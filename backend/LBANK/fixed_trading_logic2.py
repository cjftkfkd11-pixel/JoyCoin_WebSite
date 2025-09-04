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
from typing import Dict, Any, Optional, Union

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
        elif hasattr(data, 'get') and callable(getattr(data, 'get')):
            try:
                return data.get(key, default)
            except:
                return default
        else:
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
        self.min_volume_per_5min = 20000  # 5분당 최소 2만 SPSI (더 현실적)
        self.max_volume_per_5min = 40000  # 5분당 최대 4만 SPSI
        self.trade_interval = 60  # 60초마다 실행 (5분에 5회)
        
        # 최소 거래 가치 보장
        self.min_trade_value_usd = 3.0   # 최소 $3 가치 (더 안전)
        self.max_trade_value_usd = 8.0   # 최대 $8 가치
        
        # 자가매매 주문 설정
        self.min_order_size = 500   # 최소 500 SPSI per 주문 (더 작게)
        self.max_order_size = 3000  # 최대 3000 SPSI per 주문
        
        # 가격 오프셋 (더 크게 설정하여 확실한 분리)
        self.price_offset_percentage = 0.015  # 1.5% 차이 (더 안전)
        
        self.base_price = None
        self.current_orders = []
        
        # 통계
        self.total_volume_today = 0
        self.total_trades_today = 0
        self.total_fees_paid = 0.0
        
        self.response_handler = SafeAPIResponseHandler()
        
        print("✅ LBank 자가매매 시스템 초기화 완료 (잔고 오류 해결 버전)")
        print(f"🎯 목표 거래량: {self.min_volume_per_5min:,} ~ {self.max_volume_per_5min:,} SPSI/5분")
        print(f"💰 최소 거래 가치: ${self.min_trade_value_usd} ~ ${self.max_trade_value_usd}")
        print(f"🔧 가격 차이: {self.price_offset_percentage*100:.1f}% (매칭 방지)")
        logger.info("자가매매 시스템 초기화 완료 - 잔고 오류 해결 버전")

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
            print(f"   🔍 안전한 거래량 계산 시작:")
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
            if final_amount < self.min_order_size:
                if max_safe_amount >= self.min_order_size:
                    final_amount = self.min_order_size
                    final_value = final_amount * current_price
                    print(f"      - 최소 주문 크기 적용: {final_amount:,.0f} SPSI (${final_value:.2f})")
                else:
                    print(f"      - ⚠️ 잔고가 최소 주문 크기({self.min_order_size})보다 작음")
            
            # 11. 최종 안전성 재확인
            required_usdt = final_amount * current_price
            if required_usdt > balance['usdt'] or final_amount > balance['spsi']:
                print(f"      - ❌ 최종 안전성 검사 실패:")
                print(f"         필요 USDT: ${required_usdt:.2f} > 보유: ${balance['usdt']:.2f}")
                print(f"         필요 SPSI: {final_amount:,.0f} > 보유: {balance['spsi']:,.0f}")
                # 더욱 보수적으로 재계산
                safe_amount = min(
                    balance['usdt'] * 0.5 / current_price,
                    balance['spsi'] * 0.5
                )
                final_amount = max(safe_amount, 100)  # 최소 100 SPSI
                print(f"         긴급 조정: {final_amount:,.0f} SPSI")
            
            final_amount = round(final_amount, 2)
            final_value = final_amount * current_price
            
            print(f"   ✅ 최종 결정:")
            print(f"      - 거래량: {final_amount:,.0f} SPSI")
            print(f"      - 거래 가치: ${final_value:.2f}")
            print(f"      - 필요 USDT: ${final_amount * current_price:.2f}")
            print(f"      - 필요 SPSI: {final_amount:,.0f}")
            
            return final_amount
            
        except Exception as e:
            print(f"   ❌ 거래량 계산 오류: {e}")
            # 매우 안전한 기본값
            emergency_amount = min(
                500,  # 기본 500 SPSI
                balance['spsi'] * 0.1,  # 보유량의 10%
                (balance['usdt'] * 0.1) / current_price  # USDT의 10%
            )
            print(f"   🚨 긴급 기본값: {emergency_amount:,.0f} SPSI")
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
            print(f"   ⚠️ 미체결 주문 조회 오류: {e}")
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
                    print(f"   ⚠️ 개별 주문 파싱 오류: {e}")
                    continue
            
            available_usdt = max(0, balance['usdt'] - reserved_usdt)
            available_spsi = max(0, balance['spsi'] - reserved_spsi)
            
            print(f"   📋 잔고 예약 상황:")
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
            print(f"   ❌ 예약 잔고 계산 오류: {e}")
            return {
                'usdt': balance['usdt'] * 0.5,  # 안전하게 50%만 사용
                'spsi': balance['spsi'] * 0.5,
                'reserved_usdt': 0,
                'reserved_spsi': 0,
                'open_orders_count': 0
            }

    def calculate_smart_safe_amount(self, current_price: float, balance: Dict[str, float]) -> float:
        """🔥 진짜 스마트한 거래량 계산 - 미체결 주문 고려"""
        try:
            print(f"   🧠 스마트 거래량 계산:")
            
            # 1. 미체결 주문으로 예약된 잔고 계산
            available_balance = self.calculate_reserved_balance(balance)
            
            # 2. 실제 사용 가능한 잔고의 60%만 사용 (더 보수적)
            safe_usdt = available_balance['usdt'] * 0.6
            safe_spsi = available_balance['spsi'] * 0.6
            
            print(f"      - 안전 사용 USDT (60%): ${safe_usdt:.2f}")
            print(f"      - 안전 사용 SPSI (60%): {safe_spsi:,.0f}")
            
            # 3. 각각으로 가능한 최대 거래량
            max_buy_amount = safe_usdt / current_price
            max_sell_amount = safe_spsi
            
            # 4. 실제 안전 거래량 (둘 중 작은 값)
            max_safe_amount = min(max_buy_amount, max_sell_amount)
            
            print(f"      - USDT 기준 최대: {max_buy_amount:,.0f} SPSI")
            print(f"      - SPSI 기준 최대: {max_sell_amount:,.0f} SPSI")
            print(f"      - 실제 안전량: {max_safe_amount:,.0f} SPSI")
            
            # 5. 목표 거래량 계산
            target_volume = random.uniform(
                self.min_volume_per_5min / 6,  # 더 작게 (6등분)
                self.max_volume_per_5min / 6
            )
            
            # 6. 목표 가치 계산
            target_value = random.uniform(3.0, 6.0)  # $3~6로 더 보수적
            target_amount_by_value = target_value / current_price
            
            print(f"      - 목표 거래량: {target_volume:,.0f} SPSI")
            print(f"      - 목표 가치: ${target_value:.2f} → {target_amount_by_value:,.0f} SPSI")
            
            # 7. 최종 선택 (가장 작은 값)
            final_amount = min(
                max_safe_amount,
                target_volume,
                target_amount_by_value
            )
            
            print(f"      - 1차 선택: {final_amount:,.0f} SPSI")
            
            # 8. 최소값 보장 (하지만 안전 범위 내에서)
            min_required = 3.0 / current_price  # 최소 $3
            if final_amount < min_required:
                final_amount = min(min_required, max_safe_amount)
                print(f"      - 최소값 적용: {final_amount:,.0f} SPSI")
            
            # 9. 최종 가치 확인
            final_value = final_amount * current_price
            
            print(f"   ✅ 최종 스마트 결정:")
            print(f"      - 거래량: {final_amount:,.0f} SPSI")
            print(f"      - 거래 가치: ${final_value:.2f}")
            
            return round(final_amount, 2)
            
        except Exception as e:
            print(f"   ❌ 스마트 거래량 계산 오류: {e}")
            # 매우 보수적인 기본값
            return min(1000, balance['spsi'] * 0.1, (balance['usdt'] * 0.1) / current_price)

    def check_trading_readiness(self) -> Dict[str, Any]:
        """거래 준비 상태 상세 확인 - 미체결 주문 고려"""
        try:
            print("   🔍 거래 준비 상태 확인 중...")
            
            current_price = self.get_reference_price()
            balance = self.get_account_balance()
            
            if not current_price:
                return {"ready": False, "reason": "가격 조회 실패"}
            
            if not balance:
                return {"ready": False, "reason": "잔고 조회 실패"}
            
            # 🔥 새로운 스마트 거래량 계산 (미체결 주문 고려)
            safe_amount = self.calculate_smart_safe_amount(current_price, balance)
            required_usdt = safe_amount * current_price
            trade_value = safe_amount * current_price
            
            # 실제 사용 가능한 잔고 계산
            available_balance = self.calculate_reserved_balance(balance)
            
            # 상세 체크
            usdt_sufficient = available_balance['usdt'] >= required_usdt
            spsi_sufficient = available_balance['spsi'] >= safe_amount
            min_value_met = trade_value >= 2.5  # 최소값을 $2.5로 상향
            min_size_met = safe_amount >= 500   # 최소 크기도 더 작게
            
            # 미체결 주문이 너무 많으면 거래 중단
            too_many_orders = available_balance['open_orders_count'] > 10
            
            result = {
                "ready": usdt_sufficient and spsi_sufficient and min_value_met and min_size_met and not too_many_orders,
                "current_price": current_price,
                "safe_amount": safe_amount,
                "required_usdt": required_usdt,
                "available_usdt": available_balance['usdt'],
                "available_spsi": available_balance['spsi'],
                "trade_value": trade_value,
                "checks": {
                    "usdt_sufficient": usdt_sufficient,
                    "spsi_sufficient": spsi_sufficient,
                    "min_value_met": min_value_met,
                    "min_size_met": min_size_met,
                    "not_too_many_orders": not too_many_orders
                },
                "reserved_info": available_balance
            }
            
            print(f"   📊 거래 준비 상태:")
            print(f"      - 전체 준비: {'✅ 완료' if result['ready'] else '❌ 불완전'}")
            print(f"      - USDT 충분: {'✅' if usdt_sufficient else '❌'} (필요: ${required_usdt:.2f}, 사용가능: ${available_balance['usdt']:.2f})")
            print(f"      - SPSI 충분: {'✅' if spsi_sufficient else '❌'} (필요: {safe_amount:,.0f}, 사용가능: {available_balance['spsi']:,.0f})")
            print(f"      - 최소 가치: {'✅' if min_value_met else '❌'} (${trade_value:.2f} >= $2.5)")
            print(f"      - 최소 크기: {'✅' if min_size_met else '❌'} ({safe_amount:,.0f} >= 500 SPSI)")
            print(f"      - 주문 수 적정: {'✅' if not too_many_orders else '❌'} ({available_balance['open_orders_count']} <= 10)")
            
            if not result['ready']:
                if too_many_orders:
                    result['reason'] = f"미체결 주문이 너무 많음 ({available_balance['open_orders_count']}개)"
                elif not min_value_met:
                    result['reason'] = f"거래 가치 부족 (${trade_value:.2f} < $2.5)"
                elif not usdt_sufficient:
                    result['reason'] = f"사용가능 USDT 부족 (${available_balance['usdt']:.2f} < ${required_usdt:.2f})"
                elif not spsi_sufficient:
                    result['reason'] = f"사용가능 SPSI 부족 ({available_balance['spsi']:,.0f} < {safe_amount:,.0f})"
                else:
                    result['reason'] = "기타 조건 미충족"
            
            return result
            
        except Exception as e:
            print(f"   ❌ 준비 상태 확인 오류: {e}")
            return {"ready": False, "reason": f"확인 오류: {e}"}

    def place_order_with_debug(self, side: str, amount: float, price: float) -> Optional[str]:
        """주문 등록 - 상세 디버깅 버전"""
        try:
            order_value = amount * price
            print(f"      🔍 주문 상세:")
            print(f"         - 주문 타입: {side}")
            print(f"         - 수량: {amount:,.2f} SPSI")
            print(f"         - 가격: ${price:.6f}")
            print(f"         - 가치: ${order_value:.4f}")
            
            endpoint = "/create_order.do"
            params = {
                'symbol': self.symbol,
                'type': side,
                'amount': str(amount),
                'price': str(price)
            }
            
            print(f"         - API 파라미터: {params}")
            
            response = self._make_request('POST', endpoint, params, signed=True, silent=False)
            
            print(f"      🔍 API 응답:")
            print(f"         - 성공: {response.get('success') if response else False}")
            print(f"         - 에러: {response.get('error') if response else 'None'}")
            
            if not response or not response.get("success"):
                print(f"         - 실패 원인: {response.get('error') if response else 'No response'}")
                if response and response.get('raw_response'):
                    print(f"         - 원본 응답: {response.get('raw_response')}")
                return None
            
            try:
                data = response.get("data", {})
                print(f"         - 응답 데이터: {data}")
                
                error_code = self.response_handler.safe_get(data, 'error_code', -1)
                print(f"         - 에러 코드: {error_code}")
                
                if error_code != 0:
                    error_msg = self.response_handler.safe_get(data, 'msg', 
                               self.response_handler.safe_get(data, 'error_message', 'Unknown error'))
                    print(f"         - 에러 메시지: {error_msg}")
                    
                    # 에러 코드별 상세 분석
                    if error_code == 10010:
                        print(f"         - 분석: 최소 주문 요구사항 미충족")
                        print(f"         - 제안: 주문량 또는 가격 증가 필요")
                    elif error_code == 10011:
                        print(f"         - 분석: 잔고 부족")
                    elif error_code == 10013:
                        print(f"         - 분석: 주문 가격 범위 초과")
                    elif error_code == 10014:
                        print(f"         - 분석: 🔥 통화(SPSI/USDT) 잔고 부족!")
                        print(f"         - 해결책: 더 작은 거래량으로 재시도 필요")
                    else:
                        print(f"         - 분석: 기타 오류")
                    
                    return None
                
                order_id = self.response_handler.safe_get(data, 'order_id')
                
                # order_id가 data 안에 있을 수 있음
                if not order_id and 'data' in data:
                    inner_data = data.get('data', {})
                    order_id = self.response_handler.safe_get(inner_data, 'order_id')
                
                print(f"         - 주문 ID: {order_id}")
                return str(order_id) if order_id else None
                
            except Exception as e:
                print(f"         - 응답 파싱 오류: {e}")
                return None
                
        except Exception as e:
            print(f"      💥 주문 처리 오류: {e}")
            return None

    def place_order(self, side: str, amount: float, price: float) -> Optional[str]:
        """간단한 주문 등록"""
        endpoint = "/create_order.do"
        params = {
            'symbol': self.symbol,
            'type': side,
            'amount': str(amount),
            'price': str(price)
        }
        
        response = self._make_request('POST', endpoint, params, signed=True, silent=True)
        
        if not response or not response.get("success"):
            return None
        
        try:
            data = response.get("data", {})
            error_code = self.response_handler.safe_get(data, 'error_code', -1)
            
            if error_code != 0:
                error_msg = self.response_handler.safe_get(data, 'msg', 
                           self.response_handler.safe_get(data, 'error_message', 'Unknown error'))
                logger.error(f"주문 에러 (코드: {error_code}): {error_msg}")
                return None
            
            order_id = self.response_handler.safe_get(data, 'order_id')
            
            if not order_id and 'data' in data:
                inner_data = data.get('data', {})
                order_id = self.response_handler.safe_get(inner_data, 'order_id')
            
            return str(order_id) if order_id else None
            
        except Exception as e:
            logger.error(f"주문 응답 파싱 오류: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        endpoint = "/cancel_order.do"
        params = {
            'symbol': self.symbol,
            'order_id': str(order_id)
        }
        
        response = self._make_request('POST', endpoint, params, signed=True, silent=True)
        
        if not response or not response.get("success"):
            return False
        
        data = response.get("data", {})
        error_code = self.response_handler.safe_get(data, 'error_code', -1)
        return error_code == 0

    def execute_super_safe_trade_cycle(self) -> bool:
        """🔥 완전히 안전한 자가매매 사이클"""
        try:
            print("   🔍 초안전 자가매매 사이클 시작...")
            
            # 1. 거래 준비 상태 철저히 확인
            readiness = self.check_trading_readiness()
            if not readiness["ready"]:
                print(f"   ❌ 거래 불가: {readiness.get('reason', '알 수 없는 이유')}")
                return False
            
            current_price = readiness["current_price"]
            safe_amount = readiness["safe_amount"]
            
            # 2. 더블 체크: 잔고 다시 확인 + 미체결 주문 정리
            balance = self.get_account_balance()
            if not balance:
                print("   ❌ 잔고 재확인 실패")
                return False
            
            # 🔥 핵심 추가: 미체결 주문이 많으면 정리 먼저
            open_orders = self.get_open_orders()
            if len(open_orders) > 5:
                print(f"   🧹 미체결 주문 {len(open_orders)}개 발견, 정리 중...")
                self.cleanup_old_orders()
                time.sleep(2)  # 정리 후 잠시 대기
                
                # 잔고 재확인
                balance = self.get_account_balance()
                if not balance:
                    print("   ❌ 정리 후 잔고 확인 실패")
                    return False
            
            # 3. 🔥 새로운 스마트 거래량 계산 (미체결 주문 고려)
            safe_amount = self.calculate_smart_safe_amount(current_price, balance)
            required_usdt = safe_amount * current_price
            
            print(f"   📊 최종 거래 계획:")
            print(f"      - 현재 가격: ${current_price:.6f}")
            print(f"      - 스마트 거래량: {safe_amount:,.0f} SPSI")
            print(f"      - 필요 USDT: ${required_usdt:.2f}")
            print(f"      - 거래 가치: ${safe_amount * current_price:.2f}")
            
            # 4. 실제 사용가능 잔고로 최종 안전성 검사
            available_balance = self.calculate_reserved_balance(balance)
            
            if available_balance['usdt'] < required_usdt:
                print(f"   ❌ 사용가능 USDT 부족: ${required_usdt:.2f} 필요, ${available_balance['usdt']:.2f} 사용가능")
                return False
            
            if available_balance['spsi'] < safe_amount:
                print(f"   ❌ 사용가능 SPSI 부족: {safe_amount:,.0f} 필요, {available_balance['spsi']:,.0f} 사용가능")
                return False
            
            # 4. 가격 설정 (더 안전하게)
            buy_price = round(current_price * (1 - self.price_offset_percentage), 6)
            sell_price = round(current_price * (1 + self.price_offset_percentage), 6)
            
            # 5. 최종 가치 확인
            buy_value = safe_amount * buy_price
            sell_value = safe_amount * sell_price
            
            print(f"   💡 주문 가격 설정:")
            print(f"      - 기준 가격: ${current_price:.6f}")
            print(f"      - 매수 가격: ${buy_price:.6f} ({self.price_offset_percentage*100:.1f}% 낮게)")
            print(f"      - 매도 가격: ${sell_price:.6f} ({self.price_offset_percentage*100:.1f}% 높게)")
            print(f"      - 매수 가치: ${buy_value:.2f}")
            print(f"      - 매도 가치: ${sell_value:.2f}")
            
            # 6. 최소 가치 재확인
            if buy_value < 2.5 or sell_value < 2.5:  # $2.5로 상향
                print(f"   ❌ 거래 가치 부족 (매수: ${buy_value:.2f}, 매도: ${sell_value:.2f}) < $2.5")
                return False
            
            # 7. 매수 주문 먼저 실행 (상세 디버깅)
            print(f"   📡 매수 주문 실행 중...")
            buy_order_id = self.place_order_with_debug('buy', safe_amount, buy_price)
            if not buy_order_id:
                print("   ❌ 매수 주문 실패")
                return False
            print(f"   ✅ 매수 주문 성공: {buy_order_id}")
            
            # 8. 안전한 대기 시간
            print(f"   ⏳ 3초 대기 후 매도 주문...")
            time.sleep(3)
            
            # 9. 매도 주문 실행 (상세 디버깅)
            print(f"   📡 매도 주문 실행 중...")
            sell_order_id = self.place_order_with_debug('sell', safe_amount, sell_price)
            if not sell_order_id:
                print("   ❌ 매도 주문 실패, 매수 주문 취소 중...")
                cancel_success = self.cancel_order(buy_order_id)
                print(f"   {'✅' if cancel_success else '❌'} 매수 주문 취소 {'성공' if cancel_success else '실패'}")
                return False
            print(f"   ✅ 매도 주문 성공: {sell_order_id}")
            
            # 10. 주문 기록
            self.current_orders.extend([buy_order_id, sell_order_id])
            
            # 11. 통계 업데이트
            self.total_volume_today += safe_amount * 2  # 매수 + 매도
            self.total_trades_today += 2
            estimated_fee = (buy_value + sell_value) * 0.001  # 0.1% 수수료
            self.total_fees_paid += estimated_fee
            
            print(f"   ✅ 자가매매 사이클 완료!")
            print(f"   📊 거래 결과:")
            print(f"      - 매수: {safe_amount:,.0f} SPSI @ ${buy_price:.6f}")
            print(f"      - 매도: {safe_amount:,.0f} SPSI @ ${sell_price:.6f}")
            print(f"      - 예상 수수료: ${estimated_fee:.4f}")
            print(f"      - 누적 거래량: {self.total_volume_today:,.0f} SPSI")
            
            logger.info(f"안전 자가매매 완료: {safe_amount:,.0f} SPSI, 수수료: ${estimated_fee:.4f}")
            
            return True
            
        except Exception as e:
            print(f"   💥 자가매매 사이클 오류: {e}")
            logger.error(f"자가매매 사이클 오류: {e}")
            return False

    def cleanup_old_orders(self):
        """오래된 주문들 정리"""
        try:
            if not self.current_orders:
                print("   📝 정리할 주문이 없습니다")
                return
            
            print(f"   🧹 주문 정리: {len(self.current_orders)}개 주문 취소 중...")
            
            canceled_count = 0
            for order_id in self.current_orders[:]:
                try:
                    if self.cancel_order(order_id):
                        canceled_count += 1
                        print(f"   ✅ 주문 {order_id} 취소 성공")
                    else:
                        print(f"   ⚠️ 주문 {order_id} 취소 실패 (이미 체결되었을 수 있음)")
                    self.current_orders.remove(order_id)
                    time.sleep(0.2)  # API 제한 방지
                except Exception as e:
                    print(f"   ❌ 주문 {order_id} 취소 중 오류: {e}")
                    try:
                        self.current_orders.remove(order_id)
                    except:
                        pass
            
            print(f"   ✅ 주문 정리 완료: {canceled_count}개 취소됨")
                
        except Exception as e:
            logger.error(f"주문 정리 오류: {e}")
            print(f"   ❌ 주문 정리 중 오류: {e}")

    def start_self_trading(self):
        """자가매매 시작"""
        if self.running:
            print("⚠️ 이미 자가매매가 실행 중입니다")
            return
        
        # 시작 전 준비 상태 확인
        readiness = self.check_trading_readiness()
        if not readiness["ready"]:
            print(f"❌ 자가매매 시작 불가: {readiness.get('reason', '알 수 없는 이유')}")
            print("💡 잔고를 확인하거나 더 많은 자산을 추가하세요")
            return
        
        self.running = True
        print("🚀 초안전 자가매매 시스템 시작!")
        print(f"🎯 목표: 5분마다 {self.min_volume_per_5min:,}~{self.max_volume_per_5min:,} SPSI 거래량")
        print(f"⏰ 실행 간격: {self.trade_interval}초마다 (5분에 5회)")
        print(f"💰 거래 가치: ${self.min_trade_value_usd} ~ ${self.max_trade_value_usd}")
        print(f"🔧 가격 차이: {self.price_offset_percentage*100:.1f}% (매칭 방지)")
        
        def trading_loop():
            last_cleanup = time.time()
            consecutive_failures = 0
            max_failures = 3
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - 자가매매 실행")
                    
                    # 자가매매 실행
                    success = self.execute_super_safe_trade_cycle()
                    
                    if success:
                        consecutive_failures = 0
                        print(f"   📈 누적 통계:")
                        print(f"      - 오늘 거래량: {self.total_volume_today:,.0f} SPSI")
                        print(f"      - 오늘 거래 횟수: {self.total_trades_today}회")
                        print(f"      - 누적 수수료: ${self.total_fees_paid:.4f}")
                        print(f"      - 시간당 예상 거래량: {(self.min_volume_per_5min + self.max_volume_per_5min) / 2 * 12:,.0f} SPSI")
                    else:
                        consecutive_failures += 1
                        print(f"   ⚠️ 거래 실패 ({consecutive_failures}/{max_failures})")
                        
                        if consecutive_failures >= max_failures:
                            print(f"   🛑 연속 {max_failures}회 실패로 일시 정지")
                            print(f"   ⏳ 5분 후 재시도...")
                            time.sleep(300)  # 5분 대기
                            consecutive_failures = 0
                    
                    # 10분마다 오래된 주문들 정리
                    if current_time - last_cleanup > 600:  # 10분
                        print(f"\n🧹 정기 주문 정리...")
                        self.cleanup_old_orders()
                        last_cleanup = current_time
                    
                    # 다음 실행까지 대기
                    if self.running:
                        print(f"   ⏳ {self.trade_interval}초 대기...")
                        time.sleep(self.trade_interval)
                    
                except KeyboardInterrupt:
                    print("\n⏹️ 사용자 중단 요청")
                    break
                except Exception as e:
                    print(f"💥 거래 루프 오류: {e}")
                    logger.error(f"거래 루프 오류: {e}")
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_failures:
                        print(f"🛑 연속 오류로 일시 정지 (30초)")
                        time.sleep(30)
                        consecutive_failures = 0
                    else:
                        time.sleep(10)  # 짧은 대기
        
        self.trading_thread = threading.Thread(target=trading_loop, daemon=True)
        self.trading_thread.start()

    def stop_self_trading(self):
        """자가매매 중지"""
        if not self.running:
            print("⚠️ 자가매매가 실행되고 있지 않습니다")
            return
        
        self.running = False
        print("⏹️ 자가매매 중지 요청됨...")
        
        # 모든 주문 취소
        print("🧹 모든 미체결 주문 취소 중...")
        self.cleanup_old_orders()
        
        if self.trading_thread:
            print("⏳ 거래 스레드 종료 대기...")
            self.trading_thread.join(timeout=10)
        
        print("✅ 자가매매 완전 중지됨")

    def get_status(self):
        """상태 조회"""
        try:
            balance = self.get_account_balance()
            current_price = self.get_reference_price()
            
            print(f"\n{'='*60}")
            print(f"🏭 초안전 자가매매 시스템 상태")
            print(f"{'='*60}")
            print(f"📊 현재 가격: ${current_price:.6f}" if current_price else "📊 현재 가격: 조회 실패")
            
            if balance:
                print(f"💰 USDT 잔고: ${balance['usdt']:.2f}")
                print(f"🪙 SPSI 잔고: {balance['spsi']:,.2f}")
                
                # 거래 가능량 계산
                if current_price:
                    safe_amount = self.calculate_safe_trade_amount(current_price, balance)
                    print(f"🎯 1회 안전 거래량: {safe_amount:,.0f} SPSI")
                    print(f"💵 1회 거래 가치: ${safe_amount * current_price:.2f}")
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"🔄 실행 상태: {'🟢 활성' if self.running else '🔴 중지'}")
            print(f"📊 오늘 거래량: {self.total_volume_today:,.0f} SPSI")
            print(f"📊 오늘 거래 횟수: {self.total_trades_today}회")
            print(f"💳 누적 수수료: ${self.total_fees_paid:.4f}")
            print(f"📋 대기 중인 주문: {len(self.current_orders)}개")
            
            # 시간당 예상 거래량
            if self.running:
                volume_per_hour = (self.min_volume_per_5min + self.max_volume_per_5min) / 2 * 12  # 5분 * 12 = 1시간
                print(f"🎯 예상 시간당 거래량: {volume_per_hour:,.0f} SPSI")
                
            # 거래 준비 상태
            if current_price and balance:
                readiness = self.check_trading_readiness()
                print(f"🚦 거래 준비 상태: {'✅ 준비완료' if readiness['ready'] else '❌ 준비미완료'}")
                
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    def test_setup(self):
        """설정 테스트"""
        print("🧪 초안전 자가매매 설정 테스트 시작...")
        
        # 1. API 연결 테스트
        print("\n1️⃣ API 연결 테스트...")
        ticker = self.get_ticker()
        if not ticker:
            print("❌ 티커 조회 실패")
            return False
        print("✅ 티커 조회 성공")
        
        # 2. 인증 테스트
        print("\n2️⃣ 인증 테스트...")
        balance = self.get_account_balance()
        if not balance:
            print("❌ 잔고 조회 실패")
            return False
        print("✅ 잔고 조회 성공")
        
        # 3. 기준 가격 설정
        print("\n3️⃣ 기준 가격 설정...")
        reference_price = self.get_reference_price()
        if not reference_price:
            print("❌ 기준 가격 설정 실패")
            return False
        print(f"✅ 기준 가격: ${reference_price:.6f}")
        
        # 4. 거래 준비 상태 확인
        print("\n4️⃣ 거래 준비 상태 확인...")
        readiness = self.check_trading_readiness()
        
        if readiness["ready"]:
            print("✅ 거래 준비 완료!")
            print(f"   - 1회 거래량: {readiness['safe_amount']:,.0f} SPSI")
            print(f"   - 1회 거래 가치: ${readiness['trade_value']:.2f}")
            print(f"   - 5분 예상 거래량: {readiness['safe_amount'] * 5:,.0f} SPSI")
        else:
            print("❌ 거래 준비 미완료")
            print(f"   - 원인: {readiness.get('reason', '알 수 없음')}")
            if 'checks' in readiness:
                checks = readiness['checks']
                print(f"   - USDT 충분: {'✅' if checks.get('usdt_sufficient') else '❌'}")
                print(f"   - SPSI 충분: {'✅' if checks.get('spsi_sufficient') else '❌'}")
                print(f"   - 최소 가치: {'✅' if checks.get('min_value_met') else '❌'}")
                print(f"   - 최소 크기: {'✅' if checks.get('min_size_met') else '❌'}")
        
        print("\n✅ 모든 테스트 완료!")
        return readiness["ready"]

    def test_single_trade(self):
        """1회 자가매매 테스트"""
        print("🔄 1회 자가매매 테스트 실행...")
        
        # 거래 전 잔고 확인
        before_balance = self.get_account_balance()
        if before_balance:
            print(f"\n📊 거래 전 잔고:")
            print(f"   - USDT: ${before_balance['usdt']:.2f}")
            print(f"   - SPSI: {before_balance['spsi']:,.0f}")
        
        # 테스트 실행
        result = self.execute_super_safe_trade_cycle()
        
        if result:
            print("\n✅ 자가매매 테스트 성공!")
            print("💡 실제 주문이 배치되었습니다.")
            
            # 5초 후 잔고 재확인
            print("⏳ 5초 후 잔고 확인...")
            time.sleep(5)
            
            after_balance = self.get_account_balance()
            if after_balance:
                print(f"\n📊 거래 후 잔고:")
                print(f"   - USDT: ${after_balance['usdt']:.2f}")
                print(f"   - SPSI: {after_balance['spsi']:,.0f}")
                
                if before_balance:
                    usdt_diff = after_balance['usdt'] - before_balance['usdt']
                    spsi_diff = after_balance['spsi'] - before_balance['spsi']
                    print(f"\n📈 잔고 변화:")
                    print(f"   - USDT: {usdt_diff:+.2f}")
                    print(f"   - SPSI: {spsi_diff:+,.0f}")
            
            print("\n🧹 테스트 주문 정리를 원하시면 메뉴 6번을 실행하세요.")
            return True
        else:
            print("\n❌ 자가매매 테스트 실패!")
            return False

def main():
    print("🏭 LBank 초안전 자가매매 시스템 - 잔고 오류 완전 해결 버전")
    print("📋 특징: 보유 자산 범위 내에서만 안전하게 거래")
    print("🎯 목표: 5분마다 20,000~40,000 SPSI 거래량 생성")
    
    # API 키 설정
    API_KEY = os.getenv('LBANK_API_KEY', '73658848-ac66-435f-a43d-eca72f98ecbf')
    API_SECRET = os.getenv('LBANK_API_SECRET', '18F00DC6DCD01F2E19452ED52F716D3D')
    
    if not API_KEY or not API_SECRET:
        print("❌ API 키가 설정되지 않았습니다")
        input("Enter를 눌러 종료...")
        return
    
    try:
        print("📡 초안전 자가매매 시스템 초기화 중...")
        st = LBankSelfTrader(API_KEY, API_SECRET)
        
        while True:
            try:
                print("\n" + "="*60)
                print("🏭 LBank 초안전 자가매매 시스템")
                print("="*60)
                print("🔥 잔고 오류 완전 해결 - Currency is not enough 문제 해결!")
                print("✅ 보유 자산 범위 내에서만 안전하게 거래")
                print("🎯 목표: 실제 잔고 기반 안전한 거래량 생성")
                print("="*60)
                print("1. 💰 상태 확인 (잔고 + 거래 가능량)")
                print("2. 🧪 설정 테스트 (API + 거래 준비도)")
                print("3. 🔄 자가매매 1회 테스트")
                print("4. 🚀 자가매매 시작 (연속 실행)")
                print("5. ⏹️ 자가매매 중지")
                print("6. 🧹 주문 정리 (미체결 주문 취소)")
                print("8. 🔍 미체결 주문 확인 및 정리")
                print("0. 🚪 종료")
                
                choice = input("\n선택하세요 (0-8): ").strip()
                
                if choice == '1':
                    st.get_status()
                    
                elif choice == '2':
                    if st.test_setup():
                        print("\n🎉 모든 테스트 통과! 자가매매 실행 가능합니다.")
                    else:
                        print("\n⚠️ 테스트 실패! 설정을 확인하세요.")
                    
                elif choice == '3':
                    print("\n⚠️ 주의: 실제 주문이 배치됩니다!")
                    confirm = input("정말 테스트 하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.test_single_trade()
                    else:
                        print("테스트 취소됨")
                    
                elif choice == '4':
                    print("\n⚠️ 자가매매 시작 주의사항:")
                    print("- 실제 거래가 연속으로 시작됩니다")
                    print("- 보유 자산 범위 내에서만 안전하게 거래합니다")
                    print("- Currency is not enough 오류가 해결되었습니다")
                    print("- 언제든지 중지할 수 있습니다")
                    
                    confirm = input("\n정말 시작하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.start_self_trading()
                        if st.running:
                            print("✅ 초안전 자가매매 시스템이 시작되었습니다!")
                            print("💡 메뉴 1번으로 실시간 상태를 확인할 수 있습니다.")
                        else:
                            print("❌ 자가매매 시작 실패")
                    else:
                        print("자가매매 시작 취소됨")
                    
                elif choice == '5':
                    st.stop_self_trading()
                    
                elif choice == '6':
                    print("🧹 미체결 주문 정리 중...")
                    st.cleanup_old_orders()
                    
                elif choice == '7':
                    print("📊 거래 준비도 상세 분석...")
                    readiness = st.check_trading_readiness()
                    
                elif choice == '8':
                    print("🔍 미체결 주문 확인 및 정리...")
                    open_orders = st.get_open_orders()
                    
                    if not open_orders:
                        print("✅ 미체결 주문이 없습니다")
                    else:
                        print(f"📋 미체결 주문 {len(open_orders)}개 발견:")
                        for i, order in enumerate(open_orders[:5], 1):  # 최대 5개만 표시
                            try:
                                order_id = st.response_handler.safe_get(order, 'order_id', 'Unknown')
                                order_type = st.response_handler.safe_get(order, 'type', 'Unknown')
                                amount = st.response_handler.safe_get(order, 'amount', 0)
                                price = st.response_handler.safe_get(order, 'price', 0)
                                print(f"   {i}. {order_type.upper()} {amount} SPSI @ ${float(price):.6f} (ID: {order_id})")
                            except:
                                print(f"   {i}. 파싱 오류")
                        
                        if len(open_orders) > 5:
                            print(f"   ... 외 {len(open_orders) - 5}개 더")
                        
                        cancel_choice = input("\n모든 미체결 주문을 취소하시겠습니까? (y/N): ").strip().lower()
                        if cancel_choice == 'y':
                            st.cleanup_old_orders()
                        else:
                            print("미체결 주문 유지됨")
                
                elif choice == '0':
                    print("🛑 프로그램 종료 중...")
                    st.stop_self_trading()
                    print("👋 프로그램을 종료합니다.")
                    break
                    
                else:
                    print("❌ 잘못된 선택입니다. 0-8 중에서 선택하세요.")
                    
            except KeyboardInterrupt:
                print("\n⏹️ 사용자 중단 요청")
                st.stop_self_trading()
                break
            except Exception as e:
                print(f"❌ 메뉴 처리 오류: {e}")
                logger.error(f"메뉴 처리 오류: {e}")
        
    except Exception as e:
        print(f"❌ 심각한 오류: {e}")
        logger.error(f"메인 실행 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n👋 프로그램 종료.")
        input("Enter를 눌러 완전 종료...")

if __name__ == "__main__":
    main()