import requests
import hmac
import hashlib
import time
import json
import urllib.parse
import threading
import os
import random
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional, Union, List

# 안전한 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # 콘솔 출력만 사용
    ]
)
logger = logging.getLogger(__name__)

class SafeAPIResponseHandler:
    """안전한 API 응답 처리를 위한 헬퍼 클래스"""
    
    @staticmethod
    def normalize_response(data: Any) -> Dict[str, Any]:
        """모든 응답 타입을 안전한 딕셔너리로 변환"""
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            return {"items": data, "count": len(data)}
        elif isinstance(data, str):
            try:
                parsed = json.loads(data)
                return SafeAPIResponseHandler.normalize_response(parsed)
            except json.JSONDecodeError:
                return {"message": data, "type": "string_response"}
        elif data is None:
            return {"error": "null_response"}
        else:
            return {"value": data, "type": type(data).__name__}
    
    @staticmethod
    def safe_get(data: Any, key: str, default: Any = None) -> Any:
        """안전한 딕셔너리 접근"""
        if isinstance(data, dict):
            return data.get(key, default)
        return default

class LBankSelfTrader:
    """LBank 자가매매 시스템 - 잔고 오류 완전 해결 버전"""
    
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.trading_thread = None
        
        # 거래 설정
        self.symbol = "spsi_usdt"
        
        # 🎯 수정된 거래량 설정 (현실적으로 조정)
        self.min_volume_per_5min = 20000  # 5분당 최소 2만 SPSI
        self.max_volume_per_5min = 40000  # 5분당 최대 4만 SPSI
        self.trade_interval = 60  # 60초마다 실행 (5분에 5회)
        
        # 🔥 새로운 설정: 하이브리드 거래
        self.orderbook_ratio = 0.3  # 30%는 호가창 걸기용
        self.immediate_ratio = 0.7  # 70%는 즉시 체결용
        
        # 호가창 거래 설정
        self.orderbook_value_range = (1.0, 2.0)  # $1~2 가치
        self.orderbook_price_offset = 0.02  # 2% 가격 차이 (호가창용)
        
        # 즉시 체결 거래 설정  
        self.immediate_value_range = (3.0, 8.0)  # $3~8 가치
        self.immediate_price_offset = 0.001  # 0.1% 가격 차이 (즉시 체결용)

        # 💲 최소 거래 가치 (USD) 설정
        self.min_trade_value_usd = 5.0 # 예시: 5 USD로 설정, 필요에 따라 조정
        
        # 💲 최대 거래 가치 (USD) 설정
        # 단일 주문이 이 값을 초과하지 않도록 제한합니다.
        self.max_trade_value_usd = 100.0 # 예시: 100 USD로 설정, 필요에 따라 조정

        # 📊 가격 오프셋 퍼센티지 설정
        # 시장가 주문이나 지정가 주문 시 현재 시장가에서 얼마나 벗어나서 주문할지 결정하는 퍼센티지
        # 예를 들어, 0.001은 0.1% 오프셋을 의미합니다.
        self.price_offset_percentage = 0.001 # 예시: 0.1% 오프셋, 필요에 따라 조정
        
        self.base_price = None
        self.current_orders = []
        self.orderbook_orders = []  # 호가창 전용 주문
        
        # 통계
        self.total_volume_today = 0
        self.total_trades_today = 0
        self.total_fees_paid = 0.0
        self.immediate_trades_today = 0  # 즉시 체결 횟수
        self.orderbook_trades_today = 0  # 호가창 거래 횟수
        
        self.response_handler = SafeAPIResponseHandler()
        
        print("✅ LBank 하이브리드 자가매매 시스템 초기화 완료")
        print(f"🎯 목표 거래량: {self.min_volume_per_5min:,} ~ {self.max_volume_per_5min:,} SPSI/5분")
        print(f"📊 거래 방식:")
        print(f"  - 호가창 거래: {self.orderbook_ratio*100:.0f}% (${self.orderbook_value_range[0]}-{self.orderbook_value_range[1]})")
        print(f"  - 즉시 체결: {self.immediate_ratio*100:.0f}% (${self.immediate_value_range[0]}-{self.immediate_value_range[1]})")
        print(f"  - 최소 거래 가치: ${self.min_trade_value_usd:.2f} (USD)")
        print(f"  - 최대 거래 가치: ${self.max_trade_value_usd:.2f} (USD)")
        print(f"  - 일반 가격 오프셋: {self.price_offset_percentage*100:.2f}%") # ✨ 추가된 출력
        logger.info("하이브리드 자가매매 시스템 초기화 완료")
        logger.info(f"최소 거래 가치 (USD): {self.min_trade_value_usd}")
        logger.info(f"최대 거래 가치 (USD): {self.max_trade_value_usd}")
        logger.info(f"일반 가격 오프셋 (퍼센티지): {self.price_offset_percentage}") # ✨ 추가된 로그

    def _generate_signature(self, params):
        try:
            sorted_params = sorted(params.items())
            query_string = urllib.parse.urlencode(sorted_params)
            md5_hash = hashlib.md5(query_string.encode('utf-8')).hexdigest().upper()
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                md5_hash.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            return signature
        except Exception as e:
            logger.error(f"서명 생성 오류: {e}")
            return None

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                      signed: bool = False, silent: bool = False) -> Optional[Dict[str, Any]]:
        if params is None:
            params = {}

        safe_response = {
            "success": False,
            "data": {},
            "error": None,
            "raw_response": None
        }

        try:
            if signed:
                params['api_key'] = self.api_key
                params['timestamp'] = str(int(time.time() * 1000))
                params['signature_method'] = 'HmacSHA256'
                echostr = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(35))
                params['echostr'] = echostr
                
                params_for_sign = {k: str(v) for k, v in params.items()}
                sign = self._generate_signature(params_for_sign)
                
                if sign is None:
                    safe_response["error"] = "서명 생성 실패"
                    return safe_response
                
                params_for_sign['sign'] = sign
                params = params_for_sign

            url = f"{self.BASE_URL}{endpoint}"

            if method == 'GET':
                response = requests.get(url, params=params, timeout=15)
            elif method == 'POST':
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                response = requests.post(url, data=params, headers=headers, timeout=15)
            else:
                safe_response["error"] = f"지원하지 않는 HTTP 메서드: {method}"
                return safe_response
            
            if response.status_code != 200:
                safe_response["error"] = f"HTTP {response.status_code}: {response.reason}"
                safe_response["raw_response"] = response.text[:500]
                return safe_response

            if not response.text.strip():
                safe_response["data"] = {}
                safe_response["success"] = True
                return safe_response

            try:
                raw_data = response.json()
                safe_response["raw_response"] = raw_data
                normalized_data = self.response_handler.normalize_response(raw_data)
                safe_response["data"] = normalized_data
                safe_response["success"] = True
                return safe_response
                
            except (json.JSONDecodeError, ValueError):
                safe_response["error"] = "JSON 파싱 오류"
                safe_response["raw_response"] = response.text
                return safe_response

        except requests.exceptions.Timeout:
            safe_response["error"] = "요청 시간 초과"
        except requests.exceptions.ConnectionError:
            safe_response["error"] = "연결 오류"
        except Exception as e:
            safe_response["error"] = f"예상치 못한 오류: {e}"

        return safe_response

    def get_ticker(self) -> Optional[Dict[str, Any]]:
        endpoint = "/ticker.do"
        params = {"symbol": self.symbol}
        response = self._make_request('GET', endpoint, params, silent=True)
        
        if not response or not response.get("success"):
            return None
        return response.get("data", {})

    def get_account_balance(self) -> Optional[Dict[str, float]]:
        endpoint = "/user_info.do"
        response = self._make_request('POST', endpoint, signed=True, silent=True)
        
        if not response or not response.get("success"):
            return None
        
        try:
            raw_data = response.get("data", {})
            actual_data = raw_data.get('data', raw_data)
            
            if not isinstance(actual_data, dict):
                return None
            
            usdt_balance = 0.0
            spsi_balance = 0.0
            
            # free 섹션에서 찾기
            if 'free' in actual_data and isinstance(actual_data['free'], dict):
                free_data = actual_data['free']
                if 'usdt' in free_data:
                    usdt_balance = float(free_data['usdt']) if free_data['usdt'] else 0.0
                if 'spsi' in free_data:
                    spsi_balance = float(free_data['spsi']) if free_data['spsi'] else 0.0
            
            # asset 섹션에서 찾기
            if (usdt_balance == 0 or spsi_balance == 0) and 'asset' in actual_data:
                asset_data = actual_data['asset']
                if isinstance(asset_data, dict):
                    if usdt_balance == 0 and 'usdt' in asset_data:
                        usdt_info = asset_data['usdt']
                        if isinstance(usdt_info, dict) and 'free' in usdt_info:
                            usdt_balance = float(usdt_info['free']) if usdt_info['free'] else 0.0
                        elif isinstance(usdt_info, (str, int, float)):
                            usdt_balance = float(usdt_info) if usdt_info else 0.0
                    
                    if spsi_balance == 0 and 'spsi' in asset_data:
                        spsi_info = asset_data['spsi']
                        if isinstance(spsi_info, dict) and 'free' in spsi_info:
                            spsi_balance = float(spsi_info['free']) if spsi_info['free'] else 0.0
                        elif isinstance(spsi_info, (str, int, float)):
                            spsi_balance = float(spsi_info) if spsi_info else 0.0
            
            return {
                'usdt': usdt_balance,
                'spsi': spsi_balance
            }
            
        except Exception as e:
            logger.error(f"잔고 데이터 파싱 오류: {e}")
            return None

    def get_reference_price(self) -> Optional[float]:
        ticker = self.get_ticker()
        if not ticker:
            return self.base_price
        
        try:
            ticker_data = self.response_handler.safe_get(ticker, 'data', [])
            
            if not isinstance(ticker_data, list) or len(ticker_data) == 0:
                return self.base_price
            
            symbol_data = ticker_data[0]
            ticker_info = self.response_handler.safe_get(symbol_data, 'ticker', {})
            latest_price = self.response_handler.safe_get(ticker_info, 'latest', None)
            
            if latest_price is None:
                return self.base_price
            
            market_price = float(latest_price)
            
            if market_price <= 0:
                return self.base_price
            
            if self.base_price is None:
                self.base_price = market_price
                logger.info(f"기준 가격 설정: ${self.base_price:.6f}")
                return self.base_price
            
            price_diff = abs(market_price - self.base_price) / self.base_price
            if price_diff > 0.01:
                old_price = self.base_price
                self.base_price = market_price
                logger.info(f"기준 가격 업데이트: ${old_price:.6f} → ${self.base_price:.6f}")
            
            return self.base_price
            
        except Exception as e:
            logger.error(f"기준 가격 계산 오류: {e}")
            return self.base_price

    def calculate_safe_trade_amount(self, current_price: float, balance: Dict[str, float]) -> float:
        """🔥 핵심 수정: 완전히 안전한 거래량 계산"""
        try:
            print(f"    🔍 안전한 거래량 계산 시작:")
            print(f"      - 현재 가격: ${current_price:.6f}")
            print(f"      - 보유 USDT: ${balance['usdt']:.2f}")
            print(f"      - 보유 SPSI: {balance['spsi']:,.0f}")
            
            # 1. 각 자산의 사용 가능한 양 (70%만 사용 - 더 보수적)
            safe_usdt = balance['usdt'] * 0.7
            safe_spsi = balance['spsi'] * 0.7
            
            print(f"      - 안전 USDT (70%): ${safe_usdt:.2f}")
            print(f"      - 안전 SPSI (70%): {safe_spsi:,.0f}")
            
            # 2. USDT로 살 수 있는 최대 SPSI
            max_buy_amount = safe_usdt / current_price
            
            # 3. 팔 수 있는 최대 SPSI
            max_sell_amount = safe_spsi
            
            print(f"      - USDT로 매수 가능: {max_buy_amount:,.0f} SPSI")
            print(f"      - 보유 SPSI로 매도 가능: {max_sell_amount:,.0f} SPSI")
            
            # 4. 🔥 핵심: 두 값 중 작은 것이 실제 거래 가능량
            max_safe_amount = min(max_buy_amount, max_sell_amount)
            print(f"      - 실제 안전 거래량: {max_safe_amount:,.0f} SPSI")
            
            # 5. 목표 가치 기반 계산
            target_value = random.uniform(self.min_trade_value_usd, self.max_trade_value_usd)
            target_amount = target_value / current_price
            print(f"      - 목표 가치: ${target_value:.2f} → {target_amount:,.0f} SPSI")
            
            # 6. 5분 목표량 기준 계산
            target_volume_per_trade = random.uniform(
                self.min_volume_per_5min / 5,  # 5분에 5회 실행
                self.max_volume_per_5min / 5
            )
            print(f"      - 거래량 목표: {target_volume_per_trade:,.0f} SPSI")
            
            # 7. 모든 제약 조건 중 최소값 선택 (가장 중요!)
            final_amount = min(
                max_safe_amount,        # 👈 실제 보유량 제한 (가장 중요)
                target_amount,          # 목표 가치 제한
                target_volume_per_trade # 거래량 목표 제한
            )
            
            print(f"      - 1차 최종 선택: {final_amount:,.0f} SPSI")
            
            # 8. 최종 가치 확인
            final_value = final_amount * current_price
            print(f"      - 거래 가치: ${final_value:.2f}")
            
            # 9. 최소 가치 보장 (하지만 보유량을 넘지 않음)
            if final_value < 2.0:
                min_amount_for_value = 2.5 / current_price  # $2.5 보장
                final_amount = min(min_amount_for_value, max_safe_amount)
                final_value = final_amount * current_price
                print(f"      - 최소 가치 적용: {final_amount:,.0f} SPSI (${final_value:.2f})")
            
            # 10. 최소 주문 크기 확인
            # self.min_order_size가 정의되지 않았으므로, 임시로 100 SPSI를 사용합니다.
            # 실제 LBank의 최소 주문 크기에 따라 이 값을 조정해야 합니다.
            min_order_size_spsi = 100 # 임시 최소 주문 크기 설정
            if final_amount < min_order_size_spsi:
                if max_safe_amount >= min_order_size_spsi:
                    final_amount = min_order_size_spsi
                    final_value = final_amount * current_price
                    print(f"      - 최소 주문 크기 적용: {final_amount:,.0f} SPSI (${final_value:.2f})")
                else:
                    print(f"      - ⚠️ 잔고가 최소 주문 크기({min_order_size_spsi})보다 작음")
            
            # 11. 최종 안전성 재확인
            required_usdt = final_amount * current_price
            if required_usdt > balance['usdt'] or final_amount > balance['spsi']:
                print(f"      - ❌ 최종 안전성 검사 실패:")
                print(f"        필요 USDT: ${required_usdt:.2f} > 보유: ${balance['usdt']:.2f}")
                print(f"        필요 SPSI: {final_amount:,.0f} > 보유: {balance['spsi']:,.0f}")
                # 더욱 보수적으로 재계산
                safe_amount = min(
                    balance['usdt'] * 0.5 / current_price,
                    balance['spsi'] * 0.5
                )
                final_amount = max(safe_amount, 100)  # 최소 100 SPSI
                print(f"        긴급 조정: {final_amount:,.0f} SPSI")
            
            final_amount = round(final_amount, 2)
            final_value = final_amount * current_price
            
            print(f"    ✅ 최종 결정:")
            print(f"      - 거래량: {final_amount:,.0f} SPSI")
            print(f"      - 거래 가치: ${final_value:.2f}")
            print(f"      - 필요 USDT: ${final_amount * current_price:.2f}")
            print(f"      - 필요 SPSI: {final_amount:,.0f}")
            
            return final_amount
            
        except Exception as e:
            print(f"    ❌ 거래량 계산 오류: {e}")
            # 매우 안전한 기본값
            emergency_amount = min(
                500,  # 기본 500 SPSI
                balance['spsi'] * 0.1,  # 보유량의 10%
                (balance['usdt'] * 0.1) / current_price  # USDT의 10%
            )
            print(f"    🚨 긴급 기본값: {emergency_amount:,.0f} SPSI")
            return max(emergency_amount, 100)

    def get_open_orders(self) -> List[Dict]:
        """미체결 주문 조회"""
        try:
            endpoint = "/orders_info_no_deal.do"
            params = {'symbol': self.symbol}
            
            response = self._make_request('POST', endpoint, params, signed=True, silent=True)
            
            if not response or not response.get("success"):
                return []
            
            data = response.get("data", {})
            orders = self.response_handler.safe_get(data, 'orders', [])
            
            if isinstance(orders, list):
                return orders
            else:
                return []
                
        except Exception as e:
            print(f"    ⚠️ 미체결 주문 조회 오류: {e}")
            return []

    def calculate_reserved_balance(self, balance: Dict[str, float]) -> Dict[str, float]:
        """미체결 주문으로 예약된 잔고 계산"""
        try:
            open_orders = self.get_open_orders()
            
            reserved_usdt = 0.0
            reserved_spsi = 0.0
            
            for order in open_orders:
                try:
                    order_type = self.response_handler.safe_get(order, 'type', '')
                    amount = float(self.response_handler.safe_get(order, 'amount', 0))
                    price = float(self.response_handler.safe_get(order, 'price', 0))
                    
                    if order_type == 'buy':
                        reserved_usdt += amount * price
                    elif order_type == 'sell':
                        reserved_spsi += amount
                        
                except Exception as e:
                    print(f"    ⚠️ 개별 주문 파싱 오류: {e}")
                    continue
            
            available_usdt = max(0, balance['usdt'] - reserved_usdt)
            available_spsi = max(0, balance['spsi'] - reserved_spsi)
            
            print(f"    📋 잔고 예약 상황:")
            print(f"      - 총 USDT: ${balance['usdt']:.2f}")
            print(f"      - 예약 USDT: ${reserved_usdt:.2f}")
            print(f"      - 사용가능 USDT: ${available_usdt:.2f}")
            print(f"      - 총 SPSI: {balance['spsi']:,.0f}")
            print(f"      - 예약 SPSI: {reserved_spsi:,.0f}")
            print(f"      - 사용가능 SPSI: {available_spsi:,.0f}")
            print(f"      - 미체결 주문 수: {len(open_orders)}개")
            
            return {
                'usdt': available_usdt,
                'spsi': available_spsi,
                'reserved_usdt': reserved_usdt,
                'reserved_spsi': reserved_spsi,
                'open_orders_count': len(open_orders)
            }
            
        except Exception as e:
            print(f"    ❌ 예약 잔고 계산 오류: {e}")
            return {
                'usdt': balance['usdt'] * 0.5,  # 안전하게 50%만 사용
                'spsi': balance['spsi'] * 0.5,
                'reserved_usdt': 0,
                'reserved_spsi': 0,
                'open_orders_count': 0
            }

    def calculate_hybrid_trade_amounts(self, current_price: float, balance: Dict[str, float]) -> Dict[str, Any]:
        """🔥 하이브리드 거래량 계산 - 호가창 + 즉시체결"""
        try:
            print(f"    🧠 하이브리드 거래량 계산:")
            print(f"      - 현재 가격: ${current_price:.6f}")
            
            # 1. 실제 사용 가능한 잔고 계산
            available_balance = self.calculate_reserved_balance(balance)
            safe_usdt = available_balance['usdt'] * 0.6
            safe_spsi = available_balance['spsi'] * 0.6
            
            print(f"      - 안전 USDT: ${safe_usdt:.2f}")
            print(f"      - 안전 SPSI: {safe_spsi:,.0f}")
            
            # 2. 전체 거래 가능량
            max_buy_amount = safe_usdt / current_price
            max_sell_amount = safe_spsi
            max_total_amount = min(max_buy_amount, max_sell_amount)
            
            print(f"      - 전체 거래 가능량: {max_total_amount:,.0f} SPSI")
            
            # 3. 🔥 호가창 거래량 계산 (소량)
            orderbook_value = random.uniform(*self.orderbook_value_range)  # $1~2
            orderbook_amount = orderbook_value / current_price
            orderbook_amount = min(orderbook_amount, max_total_amount * 0.3)  # 최대 30%
            
            # 4. 🔥 즉시 체결 거래량 계산 (나머지)
            immediate_value = random.uniform(*self.immediate_value_range)  # $3~8
            immediate_amount = immediate_value / current_price
            remaining_capacity = max_total_amount - orderbook_amount
            immediate_amount = min(immediate_amount, remaining_capacity)
            
            # 5. 최종 조정
            total_planned = orderbook_amount + immediate_amount
            if total_planned > max_total_amount:
                ratio = max_total_amount / total_planned
                orderbook_amount *= ratio
                immediate_amount *= ratio
            
            # 6. 최소값 확인
            if orderbook_amount * current_price < 0.5:  # 최소 $0.5
                orderbook_amount = min(0.5 / current_price, max_total_amount * 0.1)
                
            if immediate_amount * current_price < 1.0:  # 최소 $1
                immediate_amount = min(1.0 / current_price, max_total_amount * 0.5)
            
            result = {
                'orderbook_amount': round(orderbook_amount, 2),
                'immediate_amount': round(immediate_amount, 2),
                'orderbook_value': orderbook_amount * current_price,
                'immediate_value': immediate_amount * current_price,
                'total_amount': orderbook_amount + immediate_amount,
                'total_value': (orderbook_amount + immediate_amount) * current_price,
                'can_trade': (orderbook_amount + immediate_amount) > 0
            }
            
            print(f"    ✅ 하이브리드 거래 계획:")
            print(f"      - 호가창 거래: {result['orderbook_amount']:,.0f} SPSI (${result['orderbook_value']:.2f})")
            print(f"      - 즉시 체결: {result['immediate_amount']:,.0f} SPSI (${result['immediate_value']:.2f})")
            print(f"      - 총 거래량: {result['total_amount']:,.0f} SPSI (${result['total_value']:.2f})")
            
            return result
            
        except Exception as e:
            print(f"    ❌ 하이브리드 거래량 계산 오류: {e}")
            return {
                'orderbook_amount': 0,
                'immediate_amount': 0,
                'orderbook_value': 0,
                'immediate_value': 0,
                'total_amount': 0,
                'total_value': 0,
                'can_trade': False
            }

    def execute_orderbook_trade(self, amount: float, current_price: float) -> bool:
        """호가창 거래 실행 (큰 가격 차이로 걸어두기)"""
        try:
            print(f"    📋 호가창 거래 실행 중...")
            
            # 호가창용 가격 설정 (큰 차이)
            buy_price = round(current_price * (1 - self.orderbook_price_offset), 6)
            sell_price = round(current_price * (1 + self.orderbook_price_offset), 6)
            
            print(f"      - 호가창 매수: {amount:,.0f} SPSI @ ${buy_price:.6f}")
            print(f"      - 호가창 매도: {amount:,.0f} SPSI @ ${sell_price:.6f}")
            print(f"      - 가격 차이: {self.orderbook_price_offset*100:.1f}% (호가창 걸기용)")
            
            # 매수 주문
            buy_order_id = self.place_order('buy', amount, buy_price)
            if not buy_order_id:
                print(f"      ❌ 호가창 매수 주문 실패")
                return False
            
            # 매도 주문  
            time.sleep(1)
            sell_order_id = self.place_order('sell', amount, sell_price)
            if not sell_order_id:
                print(f"      ❌ 호가창 매도 주문 실패, 매수 주문 취소 중...")
                self.cancel_order(buy_order_id)
                return False
            
            # 호가창 전용 주문으로 기록
            self.orderbook_orders.extend([buy_order_id, sell_order_id])
            self.orderbook_trades_today += 1
            
            print(f"      ✅ 호가창 거래 완료 (주문 ID: {buy_order_id}, {sell_order_id})")
            return True
            
        except Exception as e:
            print(f"      ❌ 호가창 거래 오류: {e}")
            return False

    def execute_immediate_trade(self, amount: float, current_price: float) -> bool:
        """즉시 체결 거래 실행 (작은 가격 차이로 빠른 매칭)"""
        try:
            print(f"    ⚡ 즉시 체결 거래 실행 중...")
            
            # 즉시 체결용 가격 설정 (작은 차이)
            buy_price = round(current_price * (1 - self.immediate_price_offset), 6)
            sell_price = round(current_price * (1 + self.immediate_price_offset), 6)
            
            print(f"      - 즉시 매수: {amount:,.0f} SPSI @ ${buy_price:.6f}")
            print(f"      - 즉시 매도: {amount:,.0f} SPSI @ ${sell_price:.6f}")
            print(f"      - 가격 차이: {self.immediate_price_offset*100:.1f}% (즉시 체결용)")
            
            # 매수 주문
            buy_order_id = self.place_order('buy', amount, buy_price)
            if not buy_order_id:
                print(f"      ❌ 즉시 매수 주문 실패")
                return False
            
            # 매도 주문
            time.sleep(1)
            sell_order_id = self.place_order('sell', amount, sell_price)
            if not sell_order_id:
                print(f"      ❌ 즉시 매도 주문 실패, 매수 주문 취소 중...")
                self.cancel_order(buy_order_id)
                return False
            
            # 일반 주문으로 기록
            self.current_orders.extend([buy_order_id, sell_order_id])
            self.immediate_trades_today += 1
            
            print(f"      ✅ 즉시 체결 거래 완료 (주문 ID: {buy_order_id}, {sell_order_id})")
            return True
            
        except Exception as e:
            print(f"      ❌ 즉시 체결 거래 오류: {e}")
            return False

    def execute_hybrid_trade_cycle(self) -> bool:
        """🔥 하이브리드 자가매매 사이클 - 호가창 + 즉시체결"""
        try:
            print("    🔄 하이브리드 자가매매 사이클 시작...")
            
            # 1. 기본 정보 수집
            current_price = self.get_reference_price()
            if not current_price:
                print("    ❌ 현재 가격 조회 실패")
                return False
            
            balance = self.get_account_balance()
            if not balance:
                print("    ❌ 잔고 조회 실패")
                return False
            
            # 2. 미체결 주문이 많으면 정리
            open_orders = self.get_open_orders()
            if len(open_orders) > 8:
                print(f"    🧹 미체결 주문 {len(open_orders)}개 발견, 정리 중...")
                self.cleanup_old_orders()
                time.sleep(2)
                
                balance = self.get_account_balance()
                if not balance:
                    print("    ❌ 정리 후 잔고 확인 실패")
                    return False
            
            # 3. 하이브리드 거래량 계산
            trade_plan = self.calculate_hybrid_trade_amounts(current_price, balance)
            
            if not trade_plan['can_trade']:
                print("    ❌ 거래 불가: 계산된 거래량이 0")
                return False
            
            success_count = 0
            
            # 4. 🔥 호가창 거래 실행 (30% - 호가창 활성화용)
            if trade_plan['orderbook_amount'] > 0:
                if self.execute_orderbook_trade(trade_plan['orderbook_amount'], current_price):
                    success_count += 1
                    print(f"    ✅ 호가창 거래 성공!")
                else:
                    print(f"    ⚠️ 호가창 거래 실패")
            
            # 5. 🔥 즉시 체결 거래 실행 (70% - 실제 거래량 생성용)
            if trade_plan['immediate_amount'] > 0:
                time.sleep(2)  # 짧은 대기
                if self.execute_immediate_trade(trade_plan['immediate_amount'], current_price):
                    success_count += 1
                    print(f"    ✅ 즉시 체결 거래 성공!")
                else:
                    print(f"    ⚠️ 즉시 체결 거래 실패")
            
            # 6. 통계 업데이트
            if success_count > 0:
                total_volume = trade_plan['total_amount'] * 2  # 매수 + 매도
                self.total_volume_today += total_volume
                self.total_trades_today += success_count * 2
                
                estimated_fee = trade_plan['total_value'] * 2 * 0.001  # 0.1% 수수료
                self.total_fees_paid += estimated_fee
                
                print(f"    📊 하이브리드 거래 결과:")
                print(f"      - 성공한 거래: {success_count}/2")
                print(f"      - 총 거래량: {total_volume:,.0f} SPSI")
                print(f"      - 총 거래 가치: ${trade_plan['total_value']*2:.2f}")
                print(f"      - 예상 수수료: ${estimated_fee:.4f}")
                print(f"      - 호가창 거래 횟수: {self.orderbook_trades_today}")
                print(f"      - 즉시 체결 횟수: {self.immediate_trades_today}")
                
            return success_count > 0

        except Exception as e:
            logger.error(f"하이브리드 거래 사이클 오류: {e}")
            return False

    def place_order(self, type: str, amount: float, price: float) -> Optional[str]:
        """주문 제출"""
        endpoint = "/create_order.do"
        params = {
            'symbol': self.symbol,
            'type': type,
            'price': f"{price:.6f}",
            'amount': f"{amount:.2f}"
        }
        
        print(f"    ➡️ 주문 제출: {type.upper()} {amount:,.2f} SPSI @ ${price:.6f}")
        response = self._make_request('POST', endpoint, params, signed=True)

        if not response or not response.get("success"):
            error_msg = self.response_handler.safe_get(response, 'error', '알 수 없는 오류')
            print(f"    ❌ 주문 제출 실패: {error_msg}")
            logger.error(f"주문 제출 실패 ({type} {amount} @ {price}): {error_msg}")
            return None
        
        order_id = self.response_handler.safe_get(response.get("data", {}), 'order_id')
        if order_id:
            print(f"    ✅ 주문 제출 성공! 주문 ID: {order_id}")
            return order_id
        else:
            print(f"    ❌ 주문 ID 없음: {response.get('raw_response')}")
            logger.error(f"주문 ID 없음: {response.get('raw_response')}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        endpoint = "/cancel_order.do"
        params = {
            'symbol': self.symbol,
            'order_id': order_id
        }
        print(f"    ↩️ 주문 취소 요청: {order_id}")
        response = self._make_request('POST', endpoint, params, signed=True)

        if not response or not response.get("success"):
            error_msg = self.response_handler.safe_get(response, 'error', '알 수 없는 오류')
            print(f"    ❌ 주문 취소 실패 ({order_id}): {error_msg}")
            logger.error(f"주문 취소 실패 ({order_id}): {error_msg}")
            return False
        
        print(f"    ✅ 주문 취소 성공: {order_id}")
        return True

    def cleanup_old_orders(self):
        """오래된 미체결 주문 정리"""
        print("    🧹 오래된 미체결 주문 정리 중...")
        open_orders = self.get_open_orders()
        
        if not open_orders:
            print("    ℹ️ 취소할 미체결 주문 없음.")
            return

        for order in open_orders:
            order_id = self.response_handler.safe_get(order, 'order_id')
            if order_id:
                self.cancel_order(order_id)
                time.sleep(0.5) # API 제한을 위해 잠시 대기
        print("    ✅ 미체결 주문 정리 완료.")

    def check_recent_trades(self) -> bool:
        """최근 체결된 거래가 있는지 확인"""
        endpoint = "/orders_info.do" # 체결된 주문도 포함
        params = {
            'symbol': self.symbol,
            'current_page': 1,
            'page_length': 10
        }
        response = self._make_request('POST', endpoint, params, signed=True, silent=True)
        
        if not response or not response.get("success"):
            return False
        
        data = response.get("data", {})
        orders = self.response_handler.safe_get(data, 'orders', [])
        
        if not orders:
            return False
        
        # 최근 5분 이내의 체결된 주문 확인
        now = datetime.now()
        for order in orders:
            status = self.response_handler.safe_get(order, 'status')
            create_time_ms = self.response_handler.safe_get(order, 'create_time')
            
            if status == '2' and create_time_ms: # '2'는 완전히 체결됨을 의미
                order_time = datetime.fromtimestamp(int(create_time_ms) / 1000)
                if (now - order_time).total_seconds() < 300: # 5분 (300초) 이내
                    return True
        return False

    def analyze_market_situation(self):
        """시장 상황을 분석하고 출력"""
        print("    📈 시장 상황 분석 중...")
        ticker = self.get_ticker()
        balance = self.get_account_balance()
        open_orders = self.get_open_orders()

        if ticker:
            ticker_data = self.response_handler.safe_get(ticker, 'data', [])
            if ticker_data and isinstance(ticker_data, list):
                symbol_data = ticker_data[0]
                ticker_info = self.response_handler.safe_get(symbol_data, 'ticker', {})
                latest_price = self.response_handler.safe_get(ticker_info, 'latest', 'N/A')
                high_24h = self.response_handler.safe_get(ticker_info, 'high', 'N/A')
                low_24h = self.response_handler.safe_get(ticker_info, 'low', 'N/A')
                vol_24h = self.response_handler.safe_get(ticker_info, 'vol', 'N/A')
                
                print(f"    📊 현재 {self.symbol.upper()} 시장:")
                print(f"      - 현재 가격: ${latest_price}")
                print(f"      - 24시간 최고: ${high_24h}")
                print(f"      - 24시간 최저: ${low_24h}")
                print(f"      - 24시간 거래량: {vol_24h} SPSI")
            else:
                print("    ⚠️ 티커 데이터 형식 오류 또는 없음.")
        else:
            print("    ❌ 티커 정보 조회 실패.")

        if balance:
            print(f"    💰 현재 잔고:")
            print(f"      - USDT: ${balance.get('usdt', 0.0):.2f}")
            print(f"      - SPSI: {balance.get('spsi', 0.0):,.0f}")
        else:
            print("    ❌ 잔고 정보 조회 실패.")
        
        if open_orders:
            print(f"    📋 미체결 주문 ({len(open_orders)}개):")
            for order in open_orders:
                order_id = self.response_handler.safe_get(order, 'order_id', 'N/A')
                type = self.response_handler.safe_get(order, 'type', 'N/A')
                amount = self.response_handler.safe_get(order, 'amount', 'N/A')
                price = self.response_handler.safe_get(order, 'price', 'N/A')
                print(f"      - ID: {order_id}, 유형: {type}, 수량: {amount}, 가격: ${price}")
        else:
            print("    ℹ️ 미체결 주문 없음.")
        
        print(f"    📈 오늘 총 거래량: {self.total_volume_today:,.0f} SPSI")
        print(f"    📈 오늘 총 거래 횟수: {self.total_trades_today}회")
        print(f"    💸 오늘 예상 수수료: ${self.total_fees_paid:.4f}")
        print(f"    ⚡ 즉시 체결 횟수: {self.immediate_trades_today}회")
        print(f"    📋 호가창 거래 횟수: {self.orderbook_trades_today}회")

    def start_self_trading(self):
        """자가매매 시작"""
        if self.running:
            print("이미 자가매매가 실행 중입니다.")
            return

        self.running = True
        self.trading_thread = threading.Thread(target=self._trading_loop)
        self.trading_thread.daemon = True
        self.trading_thread.start()
        print("🚀 자가매매 시스템이 백그라운드에서 시작되었습니다.")

    def stop_self_trading(self):
        """자가매매 중지"""
        if not self.running:
            print("자가매매가 실행 중이 아닙니다.")
            return

        self.running = False
        if self.trading_thread and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=5) # 스레드가 종료될 때까지 최대 5초 대기
            if self.trading_thread.is_alive():
                print("⚠️ 자가매매 스레드가 완전히 종료되지 않았습니다.")
            else:
                print("✅ 자가매매 스레드가 종료되었습니다.")
        print("🛑 자가매매 시스템이 중지되었습니다.")

    def _trading_loop(self):
        """거래 로직을 실행하는 내부 루프"""
        while self.running:
            try:
                print(f"\n--- 거래 사이클 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
                self.execute_hybrid_trade_cycle()
                print("--- 거래 사이클 종료 ---")
                time.sleep(self.trade_interval)
            except Exception as e:
                logger.error(f"거래 루프 오류: {e}")
                print(f"❌ 거래 루프 오류 발생: {e}. 60초 후 재시도합니다.")
                time.sleep(60) # 오류 발생 시 1분 대기 후 재시도

def main():
    # API 키와 시크릿 키를 환경 변수에서 불러오거나 직접 입력
    # 실제 사용 시에는 환경 변수를 사용하는 것이 보안상 더 안전합니다.
    api_key = os.getenv("LBANK_API_KEY", "YOUR_LBANK_API_KEY") 
    api_secret = os.getenv("LBANK_SECRET_KEY", "YOUR_LBANK_SECRET_KEY")

    if api_key == "YOUR_LBANK_API_KEY" or api_secret == "YOUR_LBANK_SECRET_KEY":
        print("⚠️ 경고: API 키 또는 시크릿 키가 설정되지 않았습니다.")
        print("    'YOUR_LBANK_API_KEY'와 'YOUR_LBANK_SECRET_KEY'를 실제 값으로 바꿔주세요.")
        print("    또는 환경 변수 LBANK_API_KEY, LBANK_SECRET_KEY를 설정하세요.")
        # 실제 운영 시에는 여기서 프로그램을 종료하는 것이 좋습니다.
        # return

    st = LBankSelfTrader(api_key, api_secret)

    print("\n============================================================")
    print("        LBank SPSI/USDT 하이브리드 자가매매 봇")
    print("============================================================")
    print("1. 🚀 자가매매 시작")
    print("2. 🛑 자가매매 중지")
    print("3. 📊 현재 잔고 및 시장 상황 확인")
    print("4. 🧹 미체결 주문 정리")
    print("5. 📈 최근 거래 상태 확인")
    print("0. 🚪 프로그램 종료")
    print("============================================================")

    while True:
        try:
            choice = input("\n메뉴를 선택하세요 (0-5): ").strip()

            if choice == '1':
                st.start_self_trading()
            
            elif choice == '2':
                st.stop_self_trading()

            elif choice == '3':
                print("📊 현재 잔고 및 시장 상황 확인 중...")
                st.analyze_market_situation()

            elif choice == '4':
                confirm = input("정말 모든 미체결 주문을 취소하시겠습니까? (y/n): ").lower()
                if confirm == 'y':
                    st.cleanup_old_orders()
                else:
                    print("미체결 주문 유지됨")
            
            elif choice == '5':
                print("📊 최근 거래 상태 확인...")
                has_trades = st.check_recent_trades()
                if has_trades:
                    print("✅ 일부 주문이 체결되었습니다!")
                else:
                    print("ℹ️ 아직 체결된 주문이 없습니다 (호가창에서 대기 중)")
            
            elif choice == '0':
                print("🛑 프로그램 종료 중...")
                st.stop_self_trading()
                print("👋 프로그램을 종료합니다.")
                break
                
            else:
                print("❌ 잘못된 선택입니다. 0-5 중에서 선택하세요.")
                
        except KeyboardInterrupt:
            print("\n⏹️ 사용자 중단 요청")
            st.stop_self_trading()
            break
        except Exception as e:
            print(f"❌ 메뉴 처리 오류: {e}")
            logger.error(f"메뉴 처리 오류: {e}")
    
    # 프로그램 종료 시 스레드가 완전히 종료될 때까지 대기
    if st.trading_thread and st.trading_thread.is_alive():
        st.trading_thread.join(timeout=5)
        if st.trading_thread.is_alive():
            print("⚠️ 백그라운드 거래 스레드가 완전히 종료되지 않았습니다.")
        else:
            print("✅ 백그라운드 거래 스레드가 안전하게 종료되었습니다.")
    print("\n👋 프로그램이 완전히 종료되었습니다.")


if __name__ == "__main__":
    main()