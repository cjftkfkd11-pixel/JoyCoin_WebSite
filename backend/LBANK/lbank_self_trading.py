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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SafeAPIResponseHandler:
    @staticmethod
    def normalize_response(data: Any) -> Dict[str, Any]:
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
    """LBank 자가매매 시스템 - 수수료만 지불하는 올바른 자가매칭 버전"""

    BASE_URL = "https://api.lbank.com"
    
    def __init__(self, api_key: str, secret_key: str, symbol: str = "spsi_usdt"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.symbol = symbol
        self.headers = {'Content-Type': 'application/json'}
        self._running = False
        self._trade_thread = None
        self.start_time = datetime.now()
        self.total_volume_today = 0.0
        self.total_trades_today = 0
        self.total_fees_paid = 0.0
        self.current_orders = [] # 현재 활성 주문 ID 추적용

        # --- 자가매매 설정 ---
        self.min_order_size = 1000 # 최소 주문량 (SPSI 기준) - LBank 최소 거래량 확인 필요
        self.min_trade_value_usd = 2.0 # 최소 거래 가치 (USDT 기준) - LBank $2 이상
        self.max_trade_value_usd = 15.0 # 최대 거래 가치 (USDT 기준)
        self.trade_interval = 60 # 각 자가매매 사이클 간 대기 시간 (초)

        # price_offset_percentage는 이제 진정한 자가매칭에서는 직접 사용되지 않지만,
        # 기존 코드 구조를 유지하거나 다른 전략에서 활용될 수 있으므로 남겨둡니다.
        self.price_offset_percentage = 0.005 # 0.5% 가격 오프셋 (매이커 주문 시 사용될 수 있음)

        # 거래량 목표 (SPSI 기준)
        self.min_volume_per_5min = 30000 
        self.max_volume_per_5min = 60000

        print("LBankSelfTrader 초기화 완료.")

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        query_string = urllib.parse.urlencode(sorted(params.items()))
        sign_string = f"{query_string}&api_key={self.api_key}&secret_key={self.secret_key}"
        md5_hash = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        return md5_hash.upper()

    def _send_request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_URL}{path}"
        
        # Public API (e.g., market data) do not need signature
        if path.startswith("/v2/currencyPair"): # Example, check LBank API docs for public endpoints
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return SafeAPIResponseHandler.normalize_response(response.json())
            except requests.exceptions.RequestException as e:
                logger.error(f"퍼블릭 API 요청 오류 ({path}): {e}")
                return None

        # Private API (e.g., account, trade) need signature
        if params is None:
            params = {}
        
        # LBank API v2 uses timestamp in params for signed requests
        params['timestamp'] = int(time.time() * 1000)
        
        sign = self._generate_sign(params)
        
        # Add sign and api_key to params for private endpoints
        params['sign'] = sign
        params['api_key'] = self.api_key

        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=self.headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=params, headers=self.headers, timeout=10)
            else:
                logger.error(f"지원하지 않는 HTTP 메소드: {method}")
                return None
            
            response.raise_for_status()
            data = SafeAPIResponseHandler.normalize_response(response.json())
            
            if data.get('result') == 'false':
                error_msg = data.get('error_message', '알 수 없는 오류')
                error_code = data.get('error_code', 'N/A')
                logger.warning(f"LBank API 오류 (코드: {error_code}): {error_msg}")
                return None
            
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 오류 ({path}): {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 디코딩 오류 ({path}): {e}")
            logger.error(f"응답 내용: {response.text}")
            return None
        except Exception as e:
            logger.error(f"예상치 못한 오류 ({path}): {e}")
            return None

    def get_account_balance(self) -> Optional[Dict[str, float]]:
        path = "/v2/user_info.do"
        response = self._send_request('POST', path)
        if response and response.get('result') == 'true' and 'info' in response:
            free_spsi = float(SafeAPIResponseHandler.safe_get(response['info']['freeze'], 'spsi', '0')) # Freeze balance
            free_usdt = float(SafeAPIResponseHandler.safe_get(response['info']['freeze'], 'usdt', '0')) # Freeze balance
            available_spsi = float(SafeAPIResponseHandler.safe_get(response['info']['asset'], 'spsi', '0')) - free_spsi
            available_usdt = float(SafeAPIResponseHandler.safe_get(response['info']['asset'], 'usdt', '0')) - free_usdt

            # 실제 사용 가능한 잔고만 반환
            return {
                'spsi': max(0.0, available_spsi),
                'usdt': max(0.0, available_usdt)
            }
        logger.warning("잔고 조회 실패.")
        return None

    def get_reference_price(self) -> Optional[float]:
        # 심볼의 최신 가격을 가져오는 API (시장 데이터는 보통 public)
        # LBank는 /v2/fullticker.do 가 모든 심볼의 티커를 반환합니다.
        # 특정 심볼만 가져오려면 /v2/ticker.do 를 사용해야 합니다.
        path = "/v2/ticker.do"
        params = {"symbol": self.symbol}
        response = self._send_request('GET', path, params=params)
        
        if response and response.get('result') == 'true' and 'ticker' in response:
            latest_price = SafeAPIResponseHandler.safe_get(response['ticker'], 'latest', None)
            if latest_price is None: # Corrected from ===
                logger.warning(f"심볼 {self.symbol}의 최신 가격을 찾을 수 없습니다: {response}")
                return None
            try:
                return float(latest_price)
            except ValueError:
                logger.warning(f"최신 가격 값 '{latest_price}'이 유효한 숫자가 아닙니다.")
                return None
        logger.warning(f"심볼 {self.symbol}의 가격 조회 실패: {response}")
        return None

    def place_order_with_debug(self, order_type: str, amount: float, price: float) -> Optional[str]:
        path = "/v2/supplementary/trade.do" # trade.do for placing orders
        params = {
            "symbol": self.symbol,
            "type": order_type, # 'buy' or 'sell'
            "price": price,
            "amount": amount
        }
        
        try:
            response = self._send_request('POST', path, params)
            if response and response.get('result') == 'true' and 'order_id' in response:
                order_id = SafeAPIResponseHandler.safe_get(response, 'order_id')
                logger.info(f"주문 성공 ({order_type.upper()}): ID {order_id}, 수량 {amount:.0f} @ {price:.6f}")
                return str(order_id)
            else:
                error_msg = SafeAPIResponseHandler.safe_get(response, 'error_message', '알 수 없는 오류')
                logger.error(f"주문 실패 ({order_type.upper()}): {error_msg}, 응답: {response}")
                return None
        except Exception as e:
            logger.error(f"주문 API 호출 중 예외 발생: {e}")
            return None

    def get_order_status(self, order_id: str) -> Optional[str]:
        path = "/v2/supplementary/order_info.do" # order_info.do for checking order status
        params = {
            "symbol": self.symbol,
            "order_id": order_id
        }
        
        try:
            response = self._send_request('POST', path, params)
            if response and response.get('result') == 'true' and 'orders' in response:
                orders = SafeAPIResponseHandler.safe_get(response, 'orders')
                if orders and len(orders) > 0:
                    status = str(SafeAPIResponseHandler.safe_get(orders[0], 'status'))
                    # LBank status codes: '0': new, '1': partial_fill, '2': filled, '3': canceled
                    # https://github.com/lbank-exchange/lbank-api-docs/blob/master/README.md#order_info
                    return status
                else:
                    logger.warning(f"주문 ID {order_id}에 대한 주문 정보를 찾을 수 없습니다. (orders 배열 비어있음)")
                    return None
            else:
                error_msg = SafeAPIResponseHandler.safe_get(response, 'error_message', '알 수 없는 오류')
                logger.warning(f"주문 상태 조회 실패 (ID: {order_id}): {error_msg}, 응답: {response}")
                return None
        except Exception as e:
            logger.error(f"주문 상태 조회 API 호출 중 예외 발생 (ID: {order_id}): {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        path = "/v2/supplementary/cancel_order.do" # cancel_order.do for cancelling orders
        params = {
            "symbol": self.symbol,
            "order_id": order_id
        }
        try:
            response = self._send_request('POST', path, params)
            if response and response.get('result') == 'true':
                logger.info(f"주문 성공적으로 취소됨: {order_id}")
                return True
            else:
                error_msg = SafeAPIResponseHandler.safe_get(response, 'error_message', '알 수 없는 오류')
                logger.error(f"주문 취소 실패 (ID: {order_id}): {error_msg}, 응답: {response}")
                return False
        except Exception as e:
            logger.error(f"주문 취소 API 호출 중 예외 발생 (ID: {order_id}): {e}")
            return False

    def calculate_smart_trade_amount(self, current_price: float, balance: Dict[str, float]) -> float:
        # 5분 목표 거래량에 맞춰 한 번에 거래할 양을 동적으로 계산
        # 남은 시간과 남은 거래량 목표를 고려
        
        # 간단하게, 한 번의 거래에 고정된 양을 사용하거나
        # 현재 시장 가격과 설정된 USD 가치를 기준으로 계산
        
        # 목표 거래 가치를 무작위로 선택
        target_trade_value = random.uniform(self.min_trade_value_usd, self.max_trade_value_usd)
        
        # 해당 가치에 해당하는 SPSI 수량 계산
        calculated_amount = target_trade_value / current_price
        
        # LBank 최소 주문 수량 (self.min_order_size) 및 최소 거래 가치 ($2) 확인
        # (LBank는 최소 $2 거래 가치를 요구함)
        if calculated_amount < self.min_order_size:
            calculated_amount = self.min_order_size
            # 최소 수량으로 인해 가치가 2달러 미만이 되는 경우 (즉, 2달러로 min_order_size를 못 채우는 경우)
            # 여기서는 min_order_size가 항상 $2 이상의 가치를 가지는 것으로 가정함
            # 실제 사용 시에는 min_order_size가 LBank 최소값보다 커야함.
        
        # 반올림 처리 (SPSI는 정수 수량을 사용한다고 가정)
        # LBank API 문서에 따르면 SPSI는 소수점 2자리까지 허용
        # 예시: 1000.12 SPSI 가능
        return round(calculated_amount, 2) # SPSI 소수점 2자리 허용 시

    def cleanup_old_orders(self):
        # API를 통해 모든 미체결 주문을 조회하고 취소하는 로직
        path = "/v2/supplementary/orders_info.do"
        params = {"symbol": self.symbol, "status": '0'} # status '0' for new (unfilled) orders
        response = self._send_request('POST', path, params)
        
        if response and response.get('result') == 'true' and 'orders' in response:
            orders = SafeAPIResponseHandler.safe_get(response, 'orders')
            if orders:
                print(f"   {len(orders)}개의 미체결 주문을 발견했습니다. 취소 중...")
                for order in orders:
                    order_id = SafeAPIResponseHandler.safe_get(order, 'order_id')
                    if order_id:
                        self.cancel_order(order_id)
                        time.sleep(0.1) # 취소 요청 간 간격
            else:
                print("   미체결 주문이 없습니다.")
        else:
            logger.warning("미체결 주문 조회 실패.")

    def execute_self_trade_cycle(self) -> bool:
        """자가매매 사이클 실행 - 진정한 자가매칭 버전"""
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
            
            # 3. 거래량 계산
            trade_amount = self.calculate_smart_trade_amount(current_price, balance)
            
            # 4. 🔥 자가매칭을 위한 단일 거래 가격 설정 (현재 가격 사용)
            # 여기서는 매수-매도 주문이 서로 체결되도록 같은 가격에 배치
            trade_price = round(current_price, 6) # 소수점 6자리 반올림
            
            buy_value = trade_amount * trade_price
            sell_value = trade_amount * trade_price

            print(f"   📊 거래 계획:")
            print(f"      - 매칭 가격: ${trade_price:.6f}")
            print(f"      - 거래량: {trade_amount:,.0f} SPSI")
            print(f"      - 거래 가치: ${trade_amount * trade_price:.2f}")
            print(f"      - USDT 잔고: ${balance['usdt']:.2f}")
            print(f"      - SPSI 잔고: {balance['spsi']:,.0f}")
            
            # 5. 잔고 확인 (매수 및 매도 주문을 모두 감당할 수 있는지)
            required_usdt_for_buy = trade_amount * trade_price
            required_spsi_for_sell = trade_amount

            # 최소 가치 확인 ($2 이상으로 다시 확인)
            if buy_value < 2.0 or sell_value < 2.0:
                print(f"   ⚠️ 거래 가치 부족: ${buy_value:.2f}. 최소 주문 금액을 보장하도록 조정합니다.")
                min_amount_by_value = 2.0 / trade_price
                trade_amount = max(self.min_order_size, round(min_amount_by_value, 2))
                buy_value = trade_amount * trade_price
                sell_value = trade_amount * trade_price
                print(f"   🔄 조정된 거래량: {trade_amount:,.0f} SPSI (가치: ${buy_value:.2f})")

            # 최종 잔고 확인
            # 매수 주문을 위한 USDT 잔고와 매도 주문을 위한 SPSI 잔고 모두 필요.
            # 이 단계에서는 아직 매수 체결 전이므로, 매수 주문에 필요한 USDT가 있는지 확인.
            # 매도 주문에 필요한 SPSI는 이전 매수 주문이 체결될 것이므로 충분하다고 가정.
            if balance['usdt'] < required_usdt_for_buy:
                 print(f"   ❌ USDT 잔고 부족 (매수용): ${balance['usdt']:.2f} (필요: ${required_usdt_for_buy:.2f})")
                 return False
            # 만약 SPSI가 거의 없다면, 자가매매 시작 시 SPSI가 부족하여 매도 주문을 내지 못할 수 있음.
            # 하지만 자가매매는 USDT와 SPSI를 반복적으로 교환하므로, 한쪽 잔고가 0이 아닌 이상 시작 가능.

            print(f"   🔄 자가매매 주문 배치 (동일 가격 매칭):")
            print(f"      - 매수 주문: {trade_amount:,.0f} SPSI @ ${trade_price:.6f} (가치: ${buy_value:.2f})")
            print(f"      - 매도 주문: {trade_amount:,.0f} SPSI @ ${trade_price:.6f} (가치: ${sell_value:.2f})")

            # 6. 첫 번째 주문 (Maker) 배치: 매수 주문을 먼저 배치
            print(f"   📡 매수 주문 (Maker) API 호출 중...")
            buy_maker_order_id = self.place_order_with_debug('buy', trade_amount, trade_price)
            if not buy_maker_order_id:
                print("   ❌ 매수 Maker 주문 실패")
                return False
            print(f"   ✅ 매수 Maker 주문 성공: {buy_maker_order_id}")

            # 7. 첫 번째 주문이 오더북에 올라갈 때까지 잠시 대기 (필요시)
            # LBank API의 처리 속도에 따라 필요 없을 수도 있지만, 안전을 위해 추가
            # 여기서 중요한 것은 buy_maker_order_id가 오더북에 실제로 올라갔는지 확인하는 것 (상태 '0' 또는 'new')
            time.sleep(0.5) 
            
            # 8. 두 번째 주문 (Taker) 배치: 동일 가격의 매도 주문으로 즉시 체결 유도
            print(f"   📡 매도 주문 (Taker) API 호출 중...")
            sell_taker_order_id = self.place_order_with_debug('sell', trade_amount, trade_price)
            if not sell_taker_order_id:
                print("   ❌ 매도 Taker 주문 실패. 매수 Maker 주문 취소 중...")
                # 매도 주문 실패 시, 이미 배치된 매수 주문 취소
                self.cancel_order(buy_maker_order_id)
                return False
            print(f"   ✅ 매도 Taker 주문 성공: {sell_taker_order_id}")

            # 9. 주문이 체결될 때까지 대기 (확인용)
            # 사실상 Taker 주문으로 바로 체결되므로 대기가 짧거나 필요 없을 수 있지만,
            # API 응답 지연 가능성 있으므로 간단히 확인
            print(f"   ⏳ 주문 체결 확인 중...")
            max_confirmation_wait_time = 30 # 체결 확인을 위한 대기 시간 (이전 15초보다 증가)
            start_confirmation_time = time.time()
            both_filled = False

            while time.time() - start_confirmation_time < max_confirmation_wait_time:
                buy_status = self.get_order_status(buy_maker_order_id)
                sell_status = self.get_order_status(sell_taker_order_id)
                
                # '2': filled (완료), '1': partial_fill (부분 체결)
                if (buy_status == '2' or buy_status == '1') and \
                   (sell_status == '2' or sell_status == '1'):
                    print(f"   🎉 매수/매도 주문 모두 체결됨 (매수:{buy_status}, 매도:{sell_status})")
                    both_filled = True
                    break
                elif buy_status == '3' or sell_status == '3': # '3': canceled (취소됨)
                    print(f"   ❌ 주문 중 하나 취소됨. (매수:{buy_status}, 매도:{sell_status})")
                    break
                time.sleep(1)

            if not both_filled:
                print(f"   ⚠️ 모든 주문이 {max_confirmation_wait_time}초 내 체결되지 않음. 잔여 주문 취소.")
                self.cancel_order(buy_maker_order_id)
                self.cancel_order(sell_taker_order_id)
                return False

            # 10. 주문 ID 저장 및 통계 업데이트
            self.current_orders.extend([buy_maker_order_id, sell_taker_order_id])
            self.total_volume_today += trade_amount * 2  # 매수 + 매도
            self.total_trades_today += 2
            
            estimated_fee = (buy_value + sell_value) * 0.001  # LBank 0.1% maker/taker (가정)
            self.total_fees_paid += estimated_fee
            
            print(f"   ✅ 자가매매 사이클 완료!")
            print(f"   📊 예상 수수료: ${estimated_fee:.4f}")
            logger.info(f"자가매매 완료: {trade_amount:,.0f} SPSI, 수수료: ${estimated_fee:.4f}")
            
            return True
            
        except Exception as e:
            print(f"   💥 자가매매 사이클 오류: {e}")
            logger.error(f"자가매매 사이클 오류: {e}")
            # 오류 발생 시 미체결 주문 정리 (필요하다면)
            return False

    def _trading_loop(self):
        while self._running:
            success = self.execute_self_trade_cycle()
            if not success:
                logger.warning("이번 자가매매 사이클 실패. 다음 시도를 위해 대기합니다.")
            
            # 다음 사이클까지 대기
            time.sleep(self.trade_interval)

    def start_self_trading(self):
        if not self._running:
            self._running = True
            print("자가매매 시스템 시작 요청됨...")
            self._trade_thread = threading.Thread(target=self._trading_loop)
            self._trade_thread.start()
            logger.info("자가매매 시스템 시작됨.")
        else:
            print("자가매매 시스템이 이미 실행 중입니다.")

    def stop_self_trading(self):
        if self._running:
            self._running = False
            print("자가매매 시스템 중지 요청됨...")
            if self._trade_thread and self._trade_thread.is_alive():
                self._trade_thread.join(timeout=5) # 스레드가 종료될 때까지 최대 5초 대기
            logger.info("자가매매 시스템 중지됨.")
            print("자가매매 시스템이 중지되었습니다.")
        else:
            print("자가매매 시스템이 실행 중이 아닙니다.")

    def display_status(self):
        now = datetime.now()
        uptime = now - self.start_time
        
        print("\n--- 자가매매 시스템 현재 상태 ---")
        print(f"  🟢 상태: {'실행 중' if self._running else '정지됨'}")
        print(f"  ⏰ 가동 시간: {uptime.days}일 {uptime.seconds // 3600}시간 {(uptime.seconds % 3600) // 60}분")
        print(f"  📊 금일 총 거래량 (SPSI): {self.total_volume_today:,.2f}")
        print(f"  📈 금일 총 거래 횟수: {self.total_trades_today}")
        print(f"  💰 금일 예상 총 수수료 지불: ${self.total_fees_paid:.4f}")
        
        balance = self.get_account_balance()
        if balance:
            print(f"  💼 현재 잔고: USDT {balance['usdt']:.2f}, SPSI {balance['spsi']:,.0f}")
        else:
            print("  ⚠️ 잔고 정보를 가져올 수 없습니다.")
        print("-----------------------------\n")

def main():
    # LBank API 키와 시크릿 키를 여기에 입력하세요
    # 예시:
    # API_KEY = "YOUR_LBANK_API_KEY"
    # SECRET_KEY = "YOUR_LBANK_SECRET_KEY"
    API_KEY = "73658848-ac66-435f-a43d-eca72f98ecbf"  # 실제 API 키로 변경하세요
    SECRET_KEY = "18F00DC6DCD01F2E19452ED52F716D3D" # 실제 시크릿 키로 변경하세요

    if API_KEY == "YOUR_LBANK_API_KEY" or SECRET_KEY == "YOUR_LBANK_SECRET_KEY":
        print("경고: API 키와 시크릿 키를 'YOUR_LBANK_API_KEY'와 'YOUR_LBANK_SECRET_KEY' 대신 실제 값으로 변경해야 합니다!")
        # return # 실제 운영 시에는 이 부분을 활성화하여 키 입력 강제

    try:
        st = LBankSelfTrader(api_key=API_KEY, secret_key=SECRET_KEY, symbol="spsi_usdt")

        while True:
            print("\n--- LBank 자가매매 시스템 메뉴 ---")
            print("1. 상태 확인")
            print("2. 자가매매 시작")
            print("3. 자가매매 중지")
            print("4. 미체결 주문 정리 (수동)")
            print("0. 프로그램 종료")
            
            choice = input("선택: ").strip()
            
            try:
                if choice == '1':
                    st.display_status()
                
                elif choice == '2':
                    print("\n--- 자가매매 시작 ---")
                    print("💡 다음 설정으로 자가매매가 시작됩니다:")
                    print(f"- 매매 주기: {st.trade_interval}초")
                    print(f"- 5분 목표 거래량: {st.min_volume_per_5min:,.0f} ~ {st.max_volume_per_5min:,.0f} SPSI")
                    print(f"- 회당 거래 가치: ${st.min_trade_value_usd:.2f} ~ ${st.max_trade_value_usd:.2f} (USDT)")
                    print("- 잔고에 따라 유동적으로 거래량이 조절됩니다.")
                    print("- 언제든지 중지할 수 있습니다")
                    
                    confirm = input("정말 시작하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.start_self_trading()
                        print("✅ 자가매매 시스템이 시작되었습니다!")
                        print("💡 메뉴 1번으로 상태를 확인할 수 있습니다.")
                    else:
                        print("자가매매 시작 취소됨")
                    
                elif choice == '3':
                    st.stop_self_trading()
                    
                elif choice == '4':
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