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
from decimal import Decimal, ROUND_DOWN
import logging
from typing import Dict, Any, Optional, Union

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lbank_market_maker.log', encoding='utf-8'),
        logging.StreamHandler()
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

class LBankMarketMaker:
    """
    LBank 마켓 메이커 시스템 V5 - 자가매매 방식 (월 9만원 수수료)
    """
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.market_making_thread = None
        
        # 마켓 메이킹 설정
        self.symbol = "spsi_usdt"
        
        # 호가창 설정 (최소한으로)
        self.spread_percentage = 0.002  # 0.2% 스프레드
        self.order_layers = 3  # 양쪽에 3개씩만
        
        # 자가매매 거래량 설정 (월 9만원 수수료 목표)
        self.min_trade_volume = 8000   # 최소 거래량 (SPSI/시간)
        self.max_trade_volume = 15000  # 최대 거래량 (SPSI/시간)
        
        # 호가창 주문량 (최소한으로)
        self.min_order_amount = 500    # 최소 주문 수량 (SPSI)
        self.max_order_amount = 1500   # 최대 주문 수량 (SPSI)
        
        # 거래 빈도 설정
        self.order_refresh_interval = 300  # 5분마다 호가창 갱신
        self.arbitrage_interval = 60      # 1분마다 자가매매 실행
        self.price_update_interval = 600   # 10분마다 기준가격 업데이트
        
        # 가격 변동 설정
        self.price_volatility = 0.001  # 0.1% 가격 변동폭
        self.base_price = None
        self.current_orders = {'buy': [], 'sell': []}
        
        # 자가매매 통계
        self.daily_volume = 0
        self.daily_trades = 0
        self.total_fees = 0.0
        
        # API 응답 핸들러 초기화
        self.response_handler = SafeAPIResponseHandler()
        
        logger.info(f"🏭 자가매매 마켓 메이커 시스템 V5 초기화 완료")
        logger.info(f"📊 거래 페어: {self.symbol}")
        logger.info(f"📈 스프레드: {self.spread_percentage*100:.1f}%")
        logger.info(f"🎯 호가창 레이어: {self.order_layers}개씩 양쪽")
        logger.info(f"💰 호가창 주문량: {self.min_order_amount:,} ~ {self.max_order_amount:,} SPSI")
        logger.info(f"🔄 목표 거래량: {self.min_trade_volume:,} ~ {self.max_trade_volume:,} SPSI/시간")
        logger.info(f"💰 예상 월 비용: 약 9만원 (수수료만)")

    def _generate_signature(self, params):
        """서명 생성"""
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
            logger.error(f"❌ 서명 생성 오류: {e}")
            return None

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     signed: bool = False, silent: bool = False) -> Optional[Dict[str, Any]]:
        """안전한 API 요청 처리"""
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
                import random
                import string
                params['api_key'] = self.api_key
                params['timestamp'] = str(int(time.time() * 1000))
                params['signature_method'] = 'HmacSHA256'
                echostr = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(35))
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
            
            if not silent:
                logger.debug(f"📡 {method} {endpoint} - Status: {response.status_code}")
            
            if response.status_code != 200:
                safe_response["error"] = f"HTTP {response.status_code}: {response.reason}"
                safe_response["raw_response"] = response.text[:500]
                if not silent:
                    logger.error(f"❌ {safe_response['error']}")
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
                
            except (json.JSONDecodeError, ValueError) as json_error:
                safe_response["error"] = f"JSON 파싱 오류: {json_error}"
                safe_response["raw_response"] = response.text
                return safe_response

        except requests.exceptions.Timeout:
            safe_response["error"] = "요청 시간 초과"
            if not silent:
                logger.error(f"💥 타임아웃: {endpoint}")
        except requests.exceptions.ConnectionError:
            safe_response["error"] = "연결 오류"
            if not silent:
                logger.error(f"💥 연결 실패: {endpoint}")
        except Exception as e:
            safe_response["error"] = f"예상치 못한 오류: {e}"
            if not silent:
                logger.error(f"💥 예상치 못한 오류 ({endpoint}): {e}")

        return safe_response

    def get_ticker(self) -> Optional[Dict[str, Any]]:
        """티커 정보 조회"""
        endpoint = "/ticker.do"
        params = {"symbol": self.symbol}
        response = self._make_request('GET', endpoint, params, silent=True)
        
        if not response or not response.get("success"):
            return None
        
        return response.get("data", {})

    def get_account_balance(self) -> Optional[Dict[str, float]]:
        """계정 잔고 조회"""
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
            logger.error(f"❌ 잔고 데이터 파싱 오류: {e}")
            return None

    def place_order(self, side: str, amount: float, price: float) -> Optional[str]:
        """주문 등록"""
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
                return None
            
            order_id = self.response_handler.safe_get(data, 'order_id')
            return str(order_id) if order_id else None
            
        except Exception as e:
            logger.error(f"❌ 주문 응답 파싱 오류: {e}")
            return None

    def place_market_order(self, order_type: str, amount: float) -> Optional[str]:
        """시장가 주문"""
        endpoint = "/create_order.do"
        params = {
            'symbol': self.symbol,
            'type': order_type,
            'amount': str(amount)
        }
        
        response = self._make_request('POST', endpoint, params, signed=True, silent=False)
        
        # 🔍 디버깅을 위한 응답 출력
        logger.info(f"🔍 주문 응답 디버깅:")
        logger.info(f"   - 성공여부: {response.get('success') if response else False}")
        logger.info(f"   - 에러: {response.get('error') if response else 'None'}")
        logger.info(f"   - 원본응답: {response.get('raw_response') if response else 'None'}")
        
        if response and response.get("success"):
            data = response.get("data", {})
            error_code = self.response_handler.safe_get(data, 'error_code', -1)
            
            logger.info(f"   - 데이터: {data}")
            logger.info(f"   - 에러코드: {error_code}")
            
            if error_code == 0:
                # 🔥 수정: data.data.order_id 경로로 주문ID 추출
                order_data = self.response_handler.safe_get(data, 'data', {})
                order_id = self.response_handler.safe_get(order_data, 'order_id')
                
                # 만약 위에서 못 찾으면 직접 data에서 찾기
                if not order_id:
                    order_id = self.response_handler.safe_get(data, 'order_id')
                
                logger.info(f"   - 주문ID: {order_id}")
                return str(order_id) if order_id else None
        
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

    def get_open_orders(self) -> list:
        """미체결 주문 조회"""
        endpoint = "/orders_info_no_deal.do"
        params = {
            'symbol': self.symbol,
            'current_page': '1',
            'page_length': '100'
        }
        
        response = self._make_request('POST', endpoint, params, signed=True, silent=True)
        
        if not response or not response.get("success"):
            return []
        
        try:
            data = response.get("data", {})
            error_code = self.response_handler.safe_get(data, 'error_code', -1)
            if error_code != 0:
                return []
            
            orders = None
            for key in ['orders', 'data', 'order_list', 'list']:
                if key in data:
                    orders = data[key]
                    break
            
            return orders if isinstance(orders, list) else []
            
        except Exception as e:
            logger.error(f"❌ 미체결 주문 파싱 오류: {e}")
            return []

    def get_reference_price(self) -> Optional[float]:
        """기준 가격 결정"""
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
                logger.info(f"📍 기준 가격 설정: ${self.base_price:.6f}")
                return self.base_price
            
            price_diff = abs(market_price - self.base_price) / self.base_price
            if price_diff > 0.005:
                old_price = self.base_price
                self.base_price = market_price
                logger.info(f"📍 기준 가격 업데이트: ${old_price:.6f} → ${self.base_price:.6f}")
            
            return self.base_price
            
        except Exception as e:
            logger.error(f"❌ 기준 가격 계산 오류: {e}")
            return self.base_price

    def generate_arbitrage_amount(self) -> float:
        """자가매매 거래량 생성 (8000~15000 범위를 1시간에 나눠서)"""
        try:
            hourly_target = random.uniform(self.min_trade_volume, self.max_trade_volume)
            minute_amount = hourly_target / 60
            variation = random.uniform(0.7, 1.3)
            amount = minute_amount * variation
            amount = max(100, round(amount, 2))
            
            logger.debug(f"🎲 자가매매 거래량: {amount:,.0f} SPSI")
            return amount
        except Exception as e:
            logger.error(f"❌ 자가매매 거래량 생성 오류: {e}")
            return 200

    def generate_order_amount(self) -> float:
        """호가창 주문 수량 생성 (500~1500)"""
        try:
            amount = round(random.uniform(self.min_order_amount, self.max_order_amount), 2)
            return amount
        except Exception as e:
            logger.error(f"❌ 주문 수량 생성 오류: {e}")
            return self.min_order_amount

    def execute_arbitrage_trade(self) -> bool:
        """자가매매 실행 - 사고 바로 팔기"""
        try:
            reference_price = self.get_reference_price()
            if not reference_price:
                return False
            
            balance = self.get_account_balance()
            if not balance:
                return False
            
            trade_amount = self.generate_arbitrage_amount()
            
            price_variation = random.uniform(-0.0005, 0.0005)
            trade_price = reference_price * (1 + price_variation)
            trade_price = round(trade_price, 6)
            
            trade_value = trade_amount * trade_price
            
            if random.choice([True, False]):
                success = self._execute_buy_sell_cycle(trade_amount, trade_price, balance)
            else:
                success = self._execute_sell_buy_cycle(trade_amount, trade_price, balance)
            
            if success:
                self.daily_volume += trade_amount
                self.daily_trades += 2
                
                estimated_fee = trade_value * 0.002
                self.total_fees += estimated_fee
                
                logger.info(f"✅ 자가매매 완료: {trade_amount:,.0f} SPSI @ ${trade_price:.6f}")
                logger.info(f"📊 일일 누적: {self.daily_volume:,.0f} SPSI, 거래: {self.daily_trades}회, 수수료: ${self.total_fees:.2f}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 자가매매 실행 오류: {e}")
            return False
    
    def _execute_buy_sell_cycle(self, amount: float, price: float, balance: Dict) -> bool:
        """매수 -> 즉시 매도 사이클"""
        try:
            trade_value = amount * price
            
            if balance['usdt'] < trade_value:
                logger.warning(f"⚠️ USDT 부족: {balance['usdt']:.2f} < {trade_value:.2f}")
                return False
            
            buy_order_id = self.place_market_order('buy_market', trade_value)
            if not buy_order_id:
                logger.warning(f"⚠️ 매수 주문 실패")
                return False
            
            time.sleep(2)
            
            sell_order_id = self.place_market_order('sell_market', amount)
            if not sell_order_id:
                logger.warning(f"⚠️ 매도 주문 실패")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 매수->매도 사이클 오류: {e}")
            return False
    
    def _execute_sell_buy_cycle(self, amount: float, price: float, balance: Dict) -> bool:
        """매도 -> 즉시 매수 사이클"""
        try:
            if balance['spsi'] < amount:
                logger.warning(f"⚠️ SPSI 부족: {balance['spsi']:.2f} < {amount:.2f}")
                return False
            
            sell_order_id = self.place_market_order('sell_market', amount)
            if not sell_order_id:
                logger.warning(f"⚠️ 매도 주문 실패")
                return False
            
            time.sleep(2)
            
            trade_value = amount * price
            buy_order_id = self.place_market_order('buy_market', trade_value)
            if not buy_order_id:
                logger.warning(f"⚠️ 매수 주문 실패")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 매도->매수 사이클 오류: {e}")
            return False

    def generate_order_prices(self, reference_price: float) -> tuple:
        """호가창에 배치할 주문 가격들 생성"""
        if not reference_price or reference_price <= 0:
            return [], []
        
        buy_prices = []
        sell_prices = []
        
        try:
            for i in range(1, self.order_layers + 1):
                spread_multiplier = i * self.spread_percentage / self.order_layers
                buy_price = reference_price * (1 - spread_multiplier)
                sell_price = reference_price * (1 + spread_multiplier)
                buy_prices.append(round(buy_price, 6))
                sell_prices.append(round(sell_price, 6))
            
            return buy_prices, sell_prices
            
        except Exception as e:
            logger.error(f"❌ 주문 가격 생성 오류: {e}")
            return [], []

    def cancel_all_orders(self):
        """모든 주문 취소"""
        canceled_count = 0
        try:
            for side in ['buy', 'sell']:
                for order_id in self.current_orders[side][:]:
                    if self.cancel_order(order_id):
                        canceled_count += 1
                        self.current_orders[side].remove(order_id)
            
            if canceled_count > 0:
                logger.info(f"🗑️ {canceled_count}개 주문 취소 완료")
        except Exception as e:
            logger.error(f"❌ 주문 취소 오류: {e}")

    def place_minimal_orders(self) -> bool:
        """최소한의 호가창 주문 배치"""
        try:
            reference_price = self.get_reference_price()
            if not reference_price:
                return False
            
            balance = self.get_account_balance()
            if not balance:
                return False
            
            self.cancel_all_orders()
            
            buy_prices, sell_prices = self.generate_order_prices(reference_price)
            
            if not buy_prices or not sell_prices:
                return False
            
            buy_orders_placed = 0
            for i, price in enumerate(buy_prices[:2]):
                amount = self.generate_order_amount()
                order_value = price * amount
                
                if balance['usdt'] >= order_value:
                    order_id = self.place_order('buy', amount, price)
                    if order_id:
                        self.current_orders['buy'].append(order_id)
                        buy_orders_placed += 1
                        logger.debug(f"📗 최소 매수 주문: {amount:,} SPSI @ ${price:.6f}")
            
            sell_orders_placed = 0
            for i, price in enumerate(sell_prices[:2]):
                amount = self.generate_order_amount()
                
                if balance['spsi'] >= amount:
                    order_id = self.place_order('sell', amount, price)
                    if order_id:
                        self.current_orders['sell'].append(order_id)
                        sell_orders_placed += 1
                        logger.debug(f"📕 최소 매도 주문: {amount:,} SPSI @ ${price:.6f}")
            
            logger.info(f"📋 최소 호가창 주문 완료: 매수 {buy_orders_placed}개, 매도 {sell_orders_placed}개")
            return buy_orders_placed > 0 or sell_orders_placed > 0
            
        except Exception as e:
            logger.error(f"❌ 최소 주문 배치 오류: {e}")
            return False

    def start_market_making(self):
        """자가매매 마켓 메이킹 시작"""
        if self.running:
            logger.warning("⚠️ 이미 마켓 메이킹이 실행 중입니다")
            return
        
        self.running = True
        self.daily_volume = 0
        self.daily_trades = 0
        self.total_fees = 0.0
        
        logger.info(f"🏭 자가매매 마켓 메이킹 시작!")
        logger.info(f"⚙️ 설정:")
        logger.info(f"   - 목표 거래량: {self.min_trade_volume:,} ~ {self.max_trade_volume:,} SPSI/시간")
        logger.info(f"   - 자가매매 간격: {self.arbitrage_interval}초")
        logger.info(f"   - 호가창 갱신: {self.order_refresh_interval}초")
        logger.info(f"   - 예상 월 수수료: 약 9만원")
        
        def market_making_loop():
            last_order_refresh = 0
            last_arbitrage = 0
            last_price_update = 0
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    if current_time - last_arbitrage >= self.arbitrage_interval:
                        if self.execute_arbitrage_trade():
                            last_arbitrage = current_time
                        else:
                            time.sleep(30)
                    
                    if current_time - last_order_refresh >= self.order_refresh_interval:
                        self.place_minimal_orders()
                        last_order_refresh = current_time
                    
                    if current_time - last_price_update >= self.price_update_interval:
                        self.get_reference_price()
                        last_price_update = current_time
                    
                    time.sleep(10)
                    
                except KeyboardInterrupt:
                    logger.info("⏹️ 사용자 중단 요청")
                    break
                except Exception as e:
                    logger.error(f"💥 마켓 메이킹 루프 오류: {e}")
                    time.sleep(30)
        
        self.market_making_thread = threading.Thread(target=market_making_loop, daemon=True)
        self.market_making_thread.start()

    def stop_market_making(self):
        """마켓 메이킹 중지"""
        if not self.running:
            logger.warning("⚠️ 마켓 메이킹이 실행되고 있지 않습니다")
            return
        
        self.running = False
        logger.info("⏹️ 마켓 메이킹 중지 요청됨")
        
        self.cancel_all_orders()
        
        if self.market_making_thread:
            self.market_making_thread.join(timeout=5)
        
        logger.info("✅ 마켓 메이킹 완전 중지됨")
        logger.info(f"📊 최종 통계: 거래량 {self.daily_volume:,.0f} SPSI, 수수료 ${self.total_fees:.2f}")

    def get_market_making_status(self):
        """마켓 메이킹 상태 조회"""
        try:
            open_orders = self.get_open_orders()
            buy_orders = [o for o in open_orders if self.response_handler.safe_get(o, 'type') == 'buy']
            sell_orders = [o for o in open_orders if self.response_handler.safe_get(o, 'type') == 'sell']
            
            balance = self.get_account_balance()
            current_price = self.get_reference_price()
            
            print(f"\n{'='*60}")
            print(f"🏭 자가매매 마켓 메이킹 상태 (V5 - 월 9만원)")
            print(f"{'='*60}")
            print(f"📊 현재 가격: ${current_price:.6f}" if current_price else "📊 현재 가격: 조회 실패")
            
            if balance:
                print(f"💰 USDT 잔고: {balance['usdt']:,.2f}")
                print(f"🪙 SPSI 잔고: {balance['spsi']:,.2f}")
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"📋 호가창 주문: 매수 {len(buy_orders)}개, 매도 {len(sell_orders)}개")
            print(f"🔄 실행 상태: {'활성' if self.running else '중지'}")
            
            print(f"\n🎯 자가매매 통계 (오늘):")
            print(f"   - 총 거래량: {self.daily_volume:,.0f} SPSI")
            print(f"   - 총 거래횟수: {self.daily_trades}회")
            print(f"   - 예상 수수료: ${self.total_fees:.2f}")
            
            target_hourly = (self.min_trade_volume + self.max_trade_volume) / 2
            print(f"   - 목표 시간당: {target_hourly:,.0f} SPSI")
            
            if buy_orders:
                print(f"\n💚 매수 주문:")
                for order in buy_orders:
                    price = self.response_handler.safe_get(order, 'price', 'N/A')
                    amount = self.response_handler.safe_get(order, 'amount', 'N/A')
                    print(f"   ${price} x {amount}")
            
            if sell_orders:
                print(f"\n💛 매도 주문:")
                for order in sell_orders:
                    price = self.response_handler.safe_get(order, 'price', 'N/A')
                    amount = self.response_handler.safe_get(order, 'amount', 'N/A')
                    print(f"   ${price} x {amount}")
                    
        except Exception as e:
            logger.error(f"❌ 상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    def test_arbitrage_setup(self):
        """자가매매 설정 테스트"""
        logger.info("🧪 자가매매 설정 테스트 시작 (월 9만원 목표)")
        
        logger.info("1️⃣ API 연결 테스트...")
        ticker = self.get_ticker()
        if not ticker:
            logger.error("❌ 티커 조회 실패")
            return False
        logger.info("✅ 티커 조회 성공")
        
        logger.info("2️⃣ 잔고 확인...")
        balance = self.get_account_balance()
        if not balance:
            logger.error("❌ 잔고 조회 실패")
            return False
        logger.info("✅ 잔고 조회 성공")
        
        logger.info("3️⃣ 기준 가격 설정...")
        reference_price = self.get_reference_price()
        if not reference_price:
            logger.error("❌ 기준 가격 설정 실패")
            return False
        logger.info(f"✅ 기준 가격: ${reference_price:.6f}")
        
        logger.info("4️⃣ 자가매매 시뮬레이션...")
        test_amount = self.generate_arbitrage_amount()
        test_value = test_amount * reference_price
        
        logger.info(f"   - 테스트 거래량: {test_amount:,.0f} SPSI")
        logger.info(f"   - 테스트 거래금액: ${test_value:.2f}")
        logger.info(f"   - 예상 수수료: ${test_value * 0.002:.4f}")
        
        min_required_usdt = test_value * 2
        min_required_spsi = test_amount * 2
        
        logger.info(f"5️⃣ 최소 자금 확인...")
        logger.info(f"   - 권장 USDT: ${min_required_usdt:.2f} (보유: ${balance['usdt']:.2f})")
        logger.info(f"   - 권장 SPSI: {min_required_spsi:,.0f} (보유: {balance['spsi']:,.0f})")
        
        if balance['usdt'] >= min_required_usdt and balance['spsi'] >= min_required_spsi:
            logger.info("✅ 자금 충분 - 자가매매 준비 완료!")
        else:
            logger.warning("⚠️ 자금 부족 - 작은 규모로 시작하는 것을 권장합니다")
        
        logger.info("✅ 모든 테스트 완료 - 자가매매 시스템 준비됨!")
        logger.info(f"🎯 예상 일일 거래량: {(self.min_trade_volume + self.max_trade_volume) * 12:,.0f} SPSI")
        logger.info(f"💰 예상 월 수수료: 약 9만원")
        
        return True

    def debug_api_response(self, endpoint: str, params: dict = None, signed: bool = False):
        """API 응답 디버깅"""
        logger.info(f"🔍 API 디버깅: {endpoint}")
        
        response = self._make_request('GET' if not signed else 'POST', endpoint, params, signed, silent=False)
        
        print(f"\n{'='*50}")
        print(f"🔍 API 디버깅 결과: {endpoint}")
        print(f"{'='*50}")
        print(f"성공 여부: {response.get('success') if response else False}")
        print(f"에러 메시지: {response.get('error') if response else 'No response'}")
        print(f"데이터 타입: {type(response.get('data')) if response else 'N/A'}")
        print(f"원본 응답 (처음 500자): {str(response.get('raw_response', 'N/A'))[:500]}...")
        print(f"{'='*50}")

def main():
    """메인 실행 함수 - 자가매매 버전 (월 9만원)"""
    API_KEY = os.getenv('LBANK_API_KEY', '73658848-ac66-435f-a43d-eca72f98ecbf')
    API_SECRET = os.getenv('LBANK_API_SECRET', '18F00DC6DCD01F2E19452ED52F716D3D')
    
    if not API_KEY or not API_SECRET:
        logger.error("❌ API 키가 설정되지 않았습니다")
        return
    
    try:
        mm = LBankMarketMaker(API_KEY, API_SECRET)
        logger.info("✅ 자가매매 마켓 메이커 초기화 완료")
        
        while True:
            try:
                print("\n" + "="*60)
                print("🏭 LBank 자가매매 마켓 메이커 시스템 V5")
                print("💰 월 수수료 약 9만원으로 자연스러운 거래량 생성")
                print("="*60)
                print("1. 마켓 메이킹 상태 확인")
                print("2. 자가매매 설정 테스트")
                print("3. 자가매매 마켓 메이킹 시작")
                print("4. 마켓 메이킹 중지") 
                print("5. 모든 주문 취소")
                print("6. 설정 조정")
                print("7. API 디버깅")
                print("8. 단일 자가매매 테스트")
                print("0. 종료")
                
                choice = input("\n선택하세요 (0-8): ").strip()
                
                if choice == '1':
                    mm.get_market_making_status()
                    
                elif choice == '2':
                    if mm.test_arbitrage_setup():
                        print("✅ 자가매매 설정 테스트 완료!")
                        print("💰 월 9만원 수수료로 거래량 생성 준비됨!")
                    else:
                        print("❌ 테스트 실패!")
                    
                elif choice == '3':
                    mm.start_market_making()
                    print("✅ 자가매매 마켓 메이킹 시작됨!")
                    print("🔄 사고->팔고->사고->팔고 방식으로 거래량 생성")
                    print("💰 월 수수료 약 9만원만 발생합니다")
                    print("📊 시간당 8,000~15,000 SPSI 자연스러운 거래량 생성")
                    
                elif choice == '4':
                    mm.stop_market_making()
                    
                elif choice == '5':
                    mm.cancel_all_orders()
                    print("✅ 모든 주문 취소 완료")
                    
                elif choice == '6':
                    print("\n⚙️ 현재 설정:")
                    print(f"  - 목표 시간당 거래량: {mm.min_trade_volume:,} ~ {mm.max_trade_volume:,} SPSI")
                    print(f"  - 자가매매 간격: {mm.arbitrage_interval}초")
                    print(f"  - 호가창 갱신 간격: {mm.order_refresh_interval}초")
                    print(f"  - 호가창 주문량: {mm.min_order_amount:,} ~ {mm.max_order_amount:,} SPSI")
                    
                    try:
                        new_min_volume = input(f"새 최소 시간당 거래량 (현재 {mm.min_trade_volume:,}, Enter=유지): ").strip()
                        if new_min_volume:
                            mm.min_trade_volume = int(new_min_volume)
                        
                        new_max_volume = input(f"새 최대 시간당 거래량 (현재 {mm.max_trade_volume:,}, Enter=유지): ").strip()
                        if new_max_volume:
                            mm.max_trade_volume = int(new_max_volume)
                        
                        new_interval = input(f"새 자가매매 간격(초) (현재 {mm.arbitrage_interval}, Enter=유지): ").strip()
                        if new_interval:
                            mm.arbitrage_interval = int(new_interval)
                        
                        print("✅ 설정 업데이트 완료")
                        print(f"📊 새 시간당 거래량: {mm.min_trade_volume:,} ~ {mm.max_trade_volume:,} SPSI")
                    except ValueError:
                        print("❌ 잘못된 값 입력")
                
                elif choice == '7':
                    print("\n🔍 API 디버깅 메뉴:")
                    print("1. 티커 정보 조회")
                    print("2. 잔고 조회")
                    
                    debug_choice = input("디버깅할 API (1-2): ").strip()
                    
                    if debug_choice == '1':
                        mm.debug_api_response("/ticker.do", {"symbol": mm.symbol})
                    elif debug_choice == '2':
                        mm.debug_api_response("/user_info.do", signed=True)
                
                elif choice == '8':
                    print("🧪 단일 자가매매 테스트 실행...")
                    if mm.execute_arbitrage_trade():
                        print("✅ 자가매매 테스트 성공!")
                    else:
                        print("❌ 자가매매 테스트 실패!")
                        
                elif choice == '0':
                    mm.stop_market_making()
                    print("👋 자가매매 마켓 메이커를 종료합니다.")
                    break
                    
                else:
                    print("❌ 잘못된 선택입니다.")
                    
            except KeyboardInterrupt:
                logger.info("⏹️ 사용자 중단 요청")
                mm.stop_market_making()
                break
            except Exception as e:
                logger.error(f"💥 메뉴 처리 오류: {e}")
                print(f"❌ 오류가 발생했습니다: {e}")
    
    except Exception as e:
        logger.error(f"💥 메인 실행 오류: {e}")
        print(f"❌ 심각한 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()