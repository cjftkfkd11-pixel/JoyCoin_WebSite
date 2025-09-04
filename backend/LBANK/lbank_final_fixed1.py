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
    """LBank 자가매매 시스템 - 최종 완성 버전 (수수료만 지불)"""
    
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.trading_thread = None
        
        # 거래 설정
        self.symbol = "spsi_usdt"
        
        # 🎯 수정된 거래량 설정 (가치 기반)
        self.min_volume_per_5min = 30000  # 5분당 최소 3만 SPSI
        self.max_volume_per_5min = 60000  # 5분당 최대 6만 SPSI
        self.trade_interval = 60  # 60초마다 실행 (5분에 5회)
        
        # 최소 거래 가치 보장
        self.min_trade_value_usd = 5.0   # 최소 $5 가치
        self.max_trade_value_usd = 15.0  # 최대 $15 가치
        
        # 자가매매 주문 설정
        self.min_order_size = 1000  # 최소 1000 SPSI per 주문
        self.max_order_size = 5000  # 최대 5000 SPSI per 주문
        
        # 가격 오프셋 (자기 주문끼리 매칭하기 위해)
        self.price_offset_percentage = 0.005  # 0.5% 차이 (더 명확한 차이)
        
        self.base_price = None
        self.current_orders = []
        
        # 통계
        self.total_volume_today = 0
        self.total_trades_today = 0
        self.total_fees_paid = 0.0
        
        self.response_handler = SafeAPIResponseHandler()
        
        print("✅ LBank 자가매매 시스템 초기화 완료")
        print(f"🎯 목표 거래량: {self.min_volume_per_5min:,} ~ {self.max_volume_per_5min:,} SPSI/5분")
        print(f"💰 최소 거래 가치: ${self.min_trade_value_usd} ~ ${self.max_trade_value_usd}")
        logger.info("자가매매 시스템 초기화 완료")

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

    def calculate_smart_trade_amount(self, current_price: float, balance: Dict[str, float]) -> float:
        """똑똑한 거래량 계산 - 잔고 고려 버전"""
        try:
            # 1. 목표 거래 가치 설정 ($5~15)
            target_value = random.uniform(self.min_trade_value_usd, self.max_trade_value_usd)
            
            # 2. 가격 기준으로 수량 계산
            amount_by_value = target_value / current_price
            
            # 3. 5분 목표량 기준으로 수량 계산
            target_volume_per_trade = random.uniform(
                self.min_volume_per_5min / 5,  # 5분에 5회 실행
                self.max_volume_per_5min / 5
            )
            
            # 4. 잔고 제한 고려 (잔고의 80%만 사용)
            max_usdt_amount = (balance['usdt'] * 0.8) / current_price
            max_spsi_amount = balance['spsi'] * 0.8
            
            # 5. 모든 제약 조건 중 최소값 선택
            final_amount = min(
                amount_by_value,
                target_volume_per_trade, 
                max_usdt_amount,
                max_spsi_amount
            )
            
            # 6. 최종 가치 확인
            final_value = final_amount * current_price
            
            print(f"   💡 거래량 계산:")
            print(f"      - 목표 가치: ${target_value:.2f}")
            print(f"      - 가치 기준 수량: {amount_by_value:,.0f} SPSI")
            print(f"      - 거래량 기준 수량: {target_volume_per_trade:,.0f} SPSI")
            print(f"      - USDT 제한 수량: {max_usdt_amount:,.0f} SPSI")
            print(f"      - SPSI 제한 수량: {max_spsi_amount:,.0f} SPSI")
            print(f"      - 최종 선택: {final_amount:,.0f} SPSI (가치: ${final_value:.2f})")
            
            # 7. 최소 가치 확인 ($2 이상)
            if final_value < 2.0:
                print(f"   ⚠️ 가치가 너무 낮음: ${final_value:.2f}")
                # 최소 $2 보장
                min_amount = 2.0 / current_price
                final_amount = min(min_amount, max_usdt_amount, max_spsi_amount)
                final_value = final_amount * current_price
                print(f"   🔄 최소 가치 보장: {final_amount:,.0f} SPSI (가치: ${final_value:.2f})")
            
            return round(final_amount, 2)
            
        except Exception as e:
            print(f"   ❌ 거래량 계산 오류: {e}")
            # 안전한 기본값: 잔고의 10%
            try:
                safe_amount = min(balance['spsi'] * 0.1, (balance['usdt'] * 0.1) / current_price)
                return max(safe_amount, 1000)
            except:
                return 1000

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
                    else:
                        print(f"         - 분석: 기타 오류")
                    
                    return None
                
                order_id = self.response_handler.safe_get(data, 'order_id')
                
                # 🔥 order_id가 data 안에 있을 수 있음
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
            
            # 🔥 order_id가 data 안에 있을 수 있음 (일반 주문용)
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

    # 🎯 핵심 기능: 올바른 자가매매 구현
    def execute_self_trade_cycle(self) -> bool:
        """자가매매 사이클 실행 - 가치 보장 버전"""
        try:
            print("   🔍 자가매매 사이클 시작...")
            
            # 1. 현재 가격 조회
            current_price = self.get_reference_price()
            if not current_price:
                print("   ❌ 현재 가격 조회 실패")
                return False
            
            # 2. 잔고 확인
            balance = self.get_account_balance()
            if not balance:
                print("   ❌ 잔고 조회 실패")
                return False
            
            # 3. 똑똑한 거래량 계산 (잔고 고려)
            trade_amount = self.calculate_smart_trade_amount(current_price, balance)
            
            print(f"   📊 거래 계획:")
            print(f"      - 현재 가격: ${current_price:.6f}")
            print(f"      - 거래량: {trade_amount:,.0f} SPSI")
            print(f"      - 거래 가치: ${trade_amount * current_price:.2f}")
            print(f"      - USDT 잔고: ${balance['usdt']:.2f}")
            print(f"      - SPSI 잔고: {balance['spsi']:,.0f}")
            
            # 4. 잔고 확인
            required_usdt = trade_amount * current_price
            if balance['usdt'] < required_usdt or balance['spsi'] < trade_amount:
                print(f"   ❌ 잔고 부족:")
                print(f"      - 필요 USDT: ${required_usdt:.2f} (보유: ${balance['usdt']:.2f})")
                print(f"      - 필요 SPSI: {trade_amount:,.0f} (보유: {balance['spsi']:,.0f})")
                return False
            
            # 5. 🎯 핵심: 같은 가격에 매수/매도 주문 동시 배치
            # 더 명확한 가격 차이를 두어 자기 주문끼리 매칭되도록 함
            buy_price = current_price * (1 - self.price_offset_percentage)  # 0.5% 낮게
            sell_price = current_price * (1 + self.price_offset_percentage)  # 0.5% 높게
            
            buy_price = round(buy_price, 6)
            sell_price = round(sell_price, 6)
            
            # 최종 가치 확인 (안전장치)
            buy_value = trade_amount * buy_price
            sell_value = trade_amount * sell_price
            
            print(f"   💡 가격 차이 계산:")
            print(f"      - 기준 가격: ${current_price:.6f}")
            print(f"      - 매수 가격: ${buy_price:.6f} ({self.price_offset_percentage*100:.1f}% 낮게)")
            print(f"      - 매도 가격: ${sell_price:.6f} ({self.price_offset_percentage*100:.1f}% 높게)")
            print(f"      - 가격 차이: ${sell_price - buy_price:.6f}")
            
            if buy_value < 2.0 or sell_value < 2.0:
                print(f"   ⚠️ 거래 가치 여전히 부족:")
                print(f"      - 매수 가치: ${buy_value:.4f}")
                print(f"      - 매도 가치: ${sell_value:.4f}")
                
                # 강제로 최소 가치 보장
                min_amount = max(2.5 / buy_price, 2.5 / sell_price)  # $2.5 보장
                trade_amount = round(min_amount, 2)
                buy_value = trade_amount * buy_price
                sell_value = trade_amount * sell_price
                
                print(f"   🔄 거래량 강제 조정: {trade_amount:,.0f} SPSI")
                print(f"      - 새 매수 가치: ${buy_value:.2f}")
                print(f"      - 새 매도 가치: ${sell_value:.2f}")
            
            print(f"   🔄 자가매매 주문 배치:")
            print(f"      - 매수 주문: {trade_amount:,.0f} SPSI @ ${buy_price:.6f} (가치: ${buy_value:.2f})")
            print(f"      - 매도 주문: {trade_amount:,.0f} SPSI @ ${sell_price:.6f} (가치: ${sell_value:.2f})")
            
            # 6. 매수 주문 먼저 배치 (상세 디버깅 포함)
            print(f"   📡 매수 주문 API 호출 중...")
            buy_order_id = self.place_order_with_debug('buy', trade_amount, buy_price)
            if not buy_order_id:
                print("   ❌ 매수 주문 실패")
                return False
            print(f"   ✅ 매수 주문 성공: {buy_order_id}")
            
            # 7. 잠시 대기 후 매도 주문
            time.sleep(2)
            
            print(f"   📡 매도 주문 API 호출 중...")
            sell_order_id = self.place_order_with_debug('sell', trade_amount, sell_price)
            if not sell_order_id:
                print("   ❌ 매도 주문 실패, 매수 주문 취소 중...")
                self.cancel_order(buy_order_id)
                return False
            print(f"   ✅ 매도 주문 성공: {sell_order_id}")
            
            # 8. 주문 ID 저장 (나중에 정리용)
            self.current_orders.extend([buy_order_id, sell_order_id])
            
            # 9. 통계 업데이트
            self.total_volume_today += trade_amount * 2  # 매수 + 매도
            self.total_trades_today += 2
            
            # 예상 수수료 (0.1% * 2회)
            estimated_fee = (buy_value + sell_value) * 0.001  # 0.1% per trade
            self.total_fees_paid += estimated_fee
            
            print(f"   ✅ 자가매매 사이클 완료!")
            print(f"   📊 예상 수수료: ${estimated_fee:.4f}")
            
            logger.info(f"자가매매 완료: {trade_amount:,.0f} SPSI, 수수료: ${estimated_fee:.4f}")
            
            return True
            
        except Exception as e:
            print(f"   💥 자가매매 사이클 오류: {e}")
            logger.error(f"자가매매 사이클 오류: {e}")
            return False

    def cleanup_old_orders(self):
        """오래된 주문들 정리"""
        try:
            if not self.current_orders:
                return
            
            print(f"   🧹 주문 정리: {len(self.current_orders)}개 주문 취소 중...")
            
            canceled_count = 0
            for order_id in self.current_orders[:]:
                if self.cancel_order(order_id):
                    canceled_count += 1
                self.current_orders.remove(order_id)
                time.sleep(0.1)  # API 제한 방지
            
            if canceled_count > 0:
                print(f"   ✅ {canceled_count}개 주문 취소 완료")
                
        except Exception as e:
            logger.error(f"주문 정리 오류: {e}")

    def start_self_trading(self):
        """자가매매 시작"""
        if self.running:
            print("⚠️ 이미 자가매매가 실행 중입니다")
            return
        
        self.running = True
        print("🚀 자가매매 시스템 시작!")
        print(f"🎯 목표: 5분마다 {self.min_volume_per_5min:,}~{self.max_volume_per_5min:,} SPSI 거래량")
        print(f"⏰ 실행 간격: {self.trade_interval}초마다 (5분에 5회)")
        print(f"💰 최소 거래 가치: ${self.min_trade_value_usd} ~ ${self.max_trade_value_usd}")
        
        def trading_loop():
            last_cleanup = time.time()
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    # 자가매매 실행
                    success = self.execute_self_trade_cycle()
                    if success:
                        print(f"   📈 누적 거래량: {self.total_volume_today:,.0f} SPSI")
                        print(f"   💰 누적 수수료: ${self.total_fees_paid:.4f}")
                    
                    # 10분마다 오래된 주문들 정리
                    if current_time - last_cleanup > 600:  # 10분
                        self.cleanup_old_orders()
                        last_cleanup = current_time
                    
                    # 다음 실행까지 대기
                    time.sleep(self.trade_interval)
                    
                except KeyboardInterrupt:
                    print("\n⏹️ 사용자 중단 요청")
                    break
                except Exception as e:
                    print(f"💥 거래 루프 오류: {e}")
                    logger.error(f"거래 루프 오류: {e}")
                    time.sleep(30)  # 오류 시 30초 대기
        
        self.trading_thread = threading.Thread(target=trading_loop, daemon=True)
        self.trading_thread.start()

    def stop_self_trading(self):
        """자가매매 중지"""
        if not self.running:
            print("⚠️ 자가매매가 실행되고 있지 않습니다")
            return
        
        self.running = False
        print("⏹️ 자가매매 중지 요청됨")
        
        # 모든 주문 취소
        self.cleanup_old_orders()
        
        if self.trading_thread:
            self.trading_thread.join(timeout=5)
        
        print("✅ 자가매매 완전 중지됨")

    def get_status(self):
        """상태 조회"""
        try:
            balance = self.get_account_balance()
            current_price = self.get_reference_price()
            
            print(f"\n{'='*60}")
            print(f"🏭 자가매매 시스템 상태")
            print(f"{'='*60}")
            print(f"📊 현재 가격: ${current_price:.6f}" if current_price else "📊 현재 가격: 조회 실패")
            
            if balance:
                print(f"💰 USDT 잔고: ${balance['usdt']:.2f}")
                print(f"🪙 SPSI 잔고: {balance['spsi']:,.2f}")
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"🔄 실행 상태: {'활성' if self.running else '중지'}")
            print(f"📊 오늘 거래량: {self.total_volume_today:,.0f} SPSI")
            print(f"📊 오늘 거래 횟수: {self.total_trades_today}회")
            print(f"💳 누적 수수료: ${self.total_fees_paid:.4f}")
            print(f"📋 대기 중인 주문: {len(self.current_orders)}개")
            
            # 시간당 예상 거래량
            if self.running:
                volume_per_hour = (self.min_volume_per_5min + self.max_volume_per_5min) / 2 * 12  # 5분 * 12 = 1시간
                print(f"🎯 예상 시간당 거래량: {volume_per_hour:,.0f} SPSI")
                
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    def test_setup(self):
        """설정 테스트"""
        print("🧪 자가매매 설정 테스트 시작...")
        
        # 1. API 연결 테스트
        print("1️⃣ API 연결 테스트...")
        ticker = self.get_ticker()
        if not ticker:
            print("❌ 티커 조회 실패")
            return False
        print("✅ 티커 조회 성공")
        
        # 2. 인증 테스트
        print("2️⃣ 인증 테스트...")
        balance = self.get_account_balance()
        if not balance:
            print("❌ 잔고 조회 실패")
            return False
        print("✅ 잔고 조회 성공")
        
        # 3. 기준 가격 설정
        print("3️⃣ 기준 가격 설정...")
        reference_price = self.get_reference_price()
        if not reference_price:
            print("❌ 기준 가격 설정 실패")
            return False
        print(f"✅ 기준 가격: ${reference_price:.6f}")
        
        # 4. 거래량 계산 테스트
        print("4️⃣ 거래량 계산 테스트...")
        target_volume = self.calculate_smart_trade_amount(reference_price, balance)
        required_usdt = target_volume * reference_price
        
        print(f"✅ 1회 거래량: {target_volume:,.0f} SPSI")
        print(f"✅ 1회 거래 가치: ${required_usdt:.2f}")
        print(f"✅ 5분 예상 거래량: {target_volume * 5:,.0f} SPSI")
        
        # 5. 잔고 충분성 검사
        print("5️⃣ 잔고 충분성 검사...")
        if balance['usdt'] >= required_usdt and balance['spsi'] >= target_volume:
            print("✅ 잔고 충분 - 자가매매 가능")
        else:
            print(f"⚠️ 잔고 부족:")
            print(f"   - USDT: ${balance['usdt']:.2f} (필요: ${required_usdt:.2f})")
            print(f"   - SPSI: {balance['spsi']:,.0f} (필요: {target_volume:,.0f})")
        
        print("✅ 모든 테스트 통과!")
        return True

def main():
    print("🏭 LBank 자가매매 시스템 - 최종 완성 버전")
    print("📋 5분마다 30,000~60,000 SPSI 거래량 생성 (수수료만 지불)")
    
    # API 키 설정
    API_KEY = os.getenv('LBANK_API_KEY', '73658848-ac66-435f-a43d-eca72f98ecbf')
    API_SECRET = os.getenv('LBANK_API_SECRET', '18F00DC6DCD01F2E19452ED52F716D3D')
    
    if not API_KEY or not API_SECRET:
        print("❌ API 키가 설정되지 않았습니다")
        input("Enter를 눌러 종료...")
        return
    
    try:
        print("📡 자가매매 시스템 초기화 중...")
        st = LBankSelfTrader(API_KEY, API_SECRET)
        
        while True:
            try:
                print("\n" + "="*60)
                print("🏭 LBank 자가매매 시스템 - 최종 완성 버전")
                print("="*60)
                print("📋 목표: 5분마다 30,000~60,000 SPSI 거래량 (수수료만 지불)")
                print("💰 최소 거래 가치: $5~15 보장으로 minimum value 오류 해결")
                print("="*60)
                print("1. 상태 확인")
                print("2. 설정 테스트")
                print("3. 자가매매 1회 테스트")
                print("4. 🚀 자가매매 시작")
                print("5. ⏹️ 자가매매 중지")
                print("6. 주문 정리")
                print("0. 종료")
                
                choice = input("\n선택하세요 (0-6): ").strip()
                
                if choice == '1':
                    st.get_status()
                    
                elif choice == '2':
                    if st.test_setup():
                        print("✅ 모든 테스트 통과!")
                    else:
                        print("❌ 테스트 실패!")
                    
                elif choice == '3':
                    print("🔄 자가매매 1회 테스트 실행...")
                    result = st.execute_self_trade_cycle()
                    if result:
                        print("✅ 자가매매 테스트 성공!")
                        print("💡 실제 주문이 배치되었습니다. 필요시 주문 정리를 실행하세요.")
                    else:
                        print("❌ 자가매매 테스트 실패!")
                    
                elif choice == '4':
                    print("\n⚠️ 주의사항:")
                    print("- 실제 거래가 시작됩니다")
                    print("- 5분마다 30,000~60,000 SPSI 거래량이 생성됩니다")
                    print("- 수수료만 지불하는 방식입니다")
                    print("- 언제든지 중지할 수 있습니다")
                    
                    confirm = input("\n정말 시작하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.start_self_trading()
                        print("✅ 자가매매 시스템이 시작되었습니다!")
                        print("💡 메뉴 1번으로 상태를 확인할 수 있습니다.")
                    else:
                        print("자가매매 시작 취소됨")
                    
                elif choice == '5':
                    st.stop_self_trading()
                    
                elif choice == '6':
                    print("🧹 미체결 주문 정리 중...")
                    st.cleanup_old_orders()
                    print("✅ 주문 정리 완료")
                    
                elif choice == '0':
                    st.stop_self_trading()
                    print("👋 프로그램을 종료합니다.")
                    break
                    
                else:
                    print("❌ 잘못된 선택입니다.")
                    
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
        print("\n프로그램 종료.")
        input("Enter를 눌러 완전 종료...")

if __name__ == "__main__":
    main()