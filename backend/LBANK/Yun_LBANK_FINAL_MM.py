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

# 로깅 설정 - 디버깅을 위해 DEBUG 레벨로 변경
logging.basicConfig(
    level=logging.DEBUG,  # INFO에서 DEBUG로 변경
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
                # JSON 문자열인지 시도
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
        """안전한 딕셔너리 접근 - 업데이트된 버전"""
        if isinstance(data, dict):
            return data.get(key, default)
        elif hasattr(data, 'get') and callable(getattr(data, 'get')):
            try:
                return data.get(key, default)
            except:
                return default
        else:
            # 에러 위치 추적을 위한 상세 로깅
            import traceback
            stack_info = traceback.format_stack()
            caller_info = stack_info[-3] if len(stack_info) >= 3 else "Unknown"
            logger.warning(f"⚠️ safe_get: '{key}' from {type(data)} at {caller_info.strip()}")
            return default
    
    @staticmethod
    def safe_nested_get(data: Any, *keys: str, default: Any = None) -> Any:
        """안전한 중첩 딕셔너리 접근"""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

class LBankMarketMaker:
    """
    LBank 마켓 메이커 시스템 V4 - 완전 에러 해결 버전
    """
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.market_making_thread = None
        
        # 마켓 메이킹 설정
        self.symbol = "spsi_usdt"
        
        # 호가창 설정
        self.spread_percentage = 0.005  # 0.5% 스프레드
        self.order_layers = 5  # 양쪽에 5개씩 주문
        self.min_order_amount = 50  # 최소 주문 수량 (SPSI)
        self.max_order_amount = 200  # 최대 주문 수량 (SPSI)
        
        # 거래 빈도 설정
        self.order_refresh_interval = 60  # 60초마다 주문 갱신
        self.fake_trade_interval = 120   # 2분마다 가짜 거래 (자가매매)
        self.price_update_interval = 300  # 5분마다 기준가격 업데이트
        
        # 가격 변동 설정
        self.price_volatility = 0.002  # 0.2% 가격 변동폭
        self.base_price = None
        self.current_orders = {'buy': [], 'sell': []}
        
        # API 응답 핸들러 초기화
        self.response_handler = SafeAPIResponseHandler()
        
        logger.info(f"🏭 마켓 메이커 시스템 V4 초기화 완료")
        logger.info(f"📊 거래 페어: {self.symbol}")
        logger.info(f"📈 스프레드: {self.spread_percentage*100:.1f}%")
        logger.info(f"🎯 주문 레이어: {self.order_layers}개씩 양쪽")

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
        """완전히 안전한 API 요청 처리"""
        if params is None:
            params = {}

        # 안전한 응답 구조 초기화
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

            # HTTP 요청 실행
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
            
            # HTTP 상태 코드 확인
            if response.status_code != 200:
                safe_response["error"] = f"HTTP {response.status_code}: {response.reason}"
                safe_response["raw_response"] = response.text[:500]
                if not silent:
                    logger.error(f"❌ {safe_response['error']}")
                return safe_response

            # 응답 내용이 비어있는지 확인
            if not response.text.strip():
                safe_response["data"] = {}
                safe_response["success"] = True
                return safe_response

            # Content-Type 확인
            content_type = response.headers.get('content-type', '').lower()
            
            # JSON 파싱 시도
            try:
                raw_data = response.json()
                safe_response["raw_response"] = raw_data
                
                # 응답 데이터 정규화
                normalized_data = self.response_handler.normalize_response(raw_data)
                safe_response["data"] = normalized_data
                safe_response["success"] = True
                
                return safe_response
                
            except (json.JSONDecodeError, ValueError) as json_error:
                # JSON 파싱 실패 시 처리
                if 'json' in content_type:
                    safe_response["error"] = f"JSON 파싱 오류: {json_error}"
                    if not silent:
                        logger.error(f"❌ JSON 파싱 실패: {response.text[:200]}...")
                else:
                    # JSON이 아닌 응답 (HTML 에러 페이지 등)
                    safe_response["error"] = f"예상하지 못한 응답 타입: {content_type}"
                    safe_response["data"] = {"text_content": response.text[:1000]}
                    if not silent:
                        logger.warning(f"⚠️ 비JSON 응답: {content_type}")
                
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
        except requests.exceptions.RequestException as e:
            safe_response["error"] = f"요청 오류: {e}"
            if not silent:
                logger.error(f"💥 요청 오류 ({endpoint}): {e}")
        except Exception as e:
            safe_response["error"] = f"예상치 못한 오류: {e}"
            if not silent:
                logger.error(f"💥 예상치 못한 오류 ({endpoint}): {e}")

        return safe_response

    # ===========================================
    # 기본 API 메서드들 - 완전 안전 버전
    # ===========================================
    
    def get_ticker(self) -> Optional[Dict[str, Any]]:
        """티커 정보 조회 - 완전 안전 버전"""
        endpoint = "/ticker.do"
        params = {"symbol": self.symbol}
        response = self._make_request('GET', endpoint, params, silent=True)
        
        if not response or not response.get("success"):
            logger.error(f"❌ 티커 조회 실패: {response.get('error') if response else 'No response'}")
            return None
        
        return response.get("data", {})

    def get_account_balance(self) -> Optional[Dict[str, float]]:
        """계정 잔고 조회 - 올바른 데이터 경로 사용"""
        endpoint = "/user_info.do"
        response = self._make_request('POST', endpoint, signed=True, silent=True)
        
        if not response or not response.get("success"):
            logger.error(f"❌ 잔고 조회 실패: {response.get('error') if response else 'No response'}")
            return None
        
        try:
            # 응답 구조: response.data.data가 실제 잔고 데이터
            raw_data = response.get("data", {})
            logger.info(f"🔍 응답 레벨 키들: {list(raw_data.keys())}")
            
            # 실제 데이터 추출
            actual_data = raw_data.get('data', raw_data)
            logger.info(f"🔍 실제 데이터 키들: {list(actual_data.keys()) if isinstance(actual_data, dict) else 'Not dict'}")
            
            if not isinstance(actual_data, dict):
                logger.error(f"❌ 실제 데이터가 딕셔너리가 아닙니다: {type(actual_data)}")
                return None
            
            # 각 섹션의 내용을 자세히 확인
            for key in ['free', 'asset', 'freeze', 'toBtc']:
                if key in actual_data:
                    section_data = actual_data[key]
                    logger.info(f"🔍 '{key}' 섹션 타입: {type(section_data)}")
                    
                    if isinstance(section_data, dict):
                        # USDT와 SPSI가 있는지 확인
                        for coin in ['usdt', 'USDT', 'spsi', 'SPSI']:
                            if coin in section_data:
                                coin_value = section_data[coin]
                                logger.info(f"🔍 '{key}.{coin}': {coin_value} (타입: {type(coin_value)})")
            
            # 실제 잔고 추출 로직
            usdt_balance = 0.0
            spsi_balance = 0.0
            
            # 1. free 섹션에서 찾기
            if 'free' in actual_data and isinstance(actual_data['free'], dict):
                free_data = actual_data['free']
                if 'usdt' in free_data:
                    usdt_balance = float(free_data['usdt']) if free_data['usdt'] else 0.0
                    logger.info(f"✅ free.usdt에서 USDT 발견: {usdt_balance}")
                if 'spsi' in free_data:
                    spsi_balance = float(free_data['spsi']) if free_data['spsi'] else 0.0
                    logger.info(f"✅ free.spsi에서 SPSI 발견: {spsi_balance}")
            
            # 2. asset 섹션에서 찾기
            if (usdt_balance == 0 or spsi_balance == 0) and 'asset' in actual_data and isinstance(actual_data['asset'], dict):
                asset_data = actual_data['asset']
                if usdt_balance == 0 and 'usdt' in asset_data:
                    usdt_info = asset_data['usdt']
                    if isinstance(usdt_info, dict) and 'free' in usdt_info:
                        usdt_balance = float(usdt_info['free']) if usdt_info['free'] else 0.0
                        logger.info(f"✅ asset.usdt.free에서 USDT 발견: {usdt_balance}")
                    elif isinstance(usdt_info, (str, int, float)):
                        usdt_balance = float(usdt_info) if usdt_info else 0.0
                        logger.info(f"✅ asset.usdt에서 USDT 발견: {usdt_balance}")
                
                if spsi_balance == 0 and 'spsi' in asset_data:
                    spsi_info = asset_data['spsi']
                    if isinstance(spsi_info, dict) and 'free' in spsi_info:
                        spsi_balance = float(spsi_info['free']) if spsi_info['free'] else 0.0
                        logger.info(f"✅ asset.spsi.free에서 SPSI 발견: {spsi_balance}")
                    elif isinstance(spsi_info, (str, int, float)):
                        spsi_balance = float(spsi_info) if spsi_info else 0.0
                        logger.info(f"✅ asset.spsi에서 SPSI 발견: {spsi_balance}")
            
            logger.info(f"🔍 최종 추출된 잔고 - USDT: {usdt_balance}, SPSI: {spsi_balance}")
            
            return {
                'usdt': usdt_balance,
                'spsi': spsi_balance
            }
            
        except (TypeError, ValueError, KeyError) as e:
            logger.error(f"❌ 잔고 데이터 파싱 오류: {e}")
            logger.error(f"원본 응답: {response}")
            return None

    def get_depth(self, size=10) -> Optional[Dict[str, Any]]:
        """호가창 정보 조회"""
        endpoint = "/depth.do"
        params = {"symbol": self.symbol, "size": size}
        response = self._make_request('GET', endpoint, params, silent=True)
        
        if response and response.get("success"):
            return response.get("data", {})
        return None

    def place_order(self, side: str, amount: float, price: float) -> Optional[str]:
        """주문 등록 - 완전 안전 버전"""
        endpoint = "/create_order.do"
        params = {
            'symbol': self.symbol,
            'type': side,
            'amount': str(amount),
            'price': str(price)
        }
        
        response = self._make_request('POST', endpoint, params, signed=True, silent=True)
        
        if not response or not response.get("success"):
            logger.error(f"❌ 주문 등록 실패: {response.get('error') if response else 'No response'}")
            return None
        
        try:
            data = response.get("data", {})
            
            # 에러 코드 확인
            error_code = self.response_handler.safe_get(data, 'error_code', -1)
            if error_code != 0:
                error_msg = self.response_handler.safe_get(data, 'error_message', 'Unknown error')
                logger.error(f"❌ 주문 에러 (코드: {error_code}): {error_msg}")
                return None
            
            # 주문 ID 추출
            order_id = self.response_handler.safe_get(data, 'order_id')
            return str(order_id) if order_id else None
            
        except Exception as e:
            logger.error(f"❌ 주문 응답 파싱 오류: {e}")
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
        """미체결 주문 조회 - 파라미터 수정"""
        endpoint = "/orders_info_no_deal.do"
        params = {
            'symbol': self.symbol,
            'current_page': '1',
            'page_length': '100'
        }
        
        response = self._make_request('POST', endpoint, params, signed=True, silent=True)
        
        if not response or not response.get("success"):
            logger.error(f"❌ 미체결 주문 조회 실패: {response.get('error') if response else 'No response'}")
            return []
        
        try:
            data = response.get("data", {})
            logger.info(f"🔍 미체결 주문 응답: {data}")
            
            # 에러 코드 확인
            error_code = self.response_handler.safe_get(data, 'error_code', -1)
            if error_code != 0:
                error_msg = self.response_handler.safe_get(data, 'msg', 'Unknown error')
                logger.error(f"❌ 미체결 주문 에러 (코드: {error_code}): {error_msg}")
                return []
            
            # 주문 목록 추출 - 여러 가능한 키 시도
            orders = None
            for key in ['orders', 'data', 'order_list', 'list']:
                if key in data:
                    orders = data[key]
                    logger.info(f"🔍 주문 목록 '{key}'에서 발견: {len(orders) if isinstance(orders, list) else 'Not list'}")
                    break
            
            if orders is None:
                logger.warning(f"⚠️ 주문 목록을 찾을 수 없습니다. 응답 키들: {list(data.keys())}")
                return []
            
            return orders if isinstance(orders, list) else []
            
        except Exception as e:
            logger.error(f"❌ 미체결 주문 파싱 오류: {e}")
            return []

    # ===========================================
    # 마켓 메이킹 핵심 기능
    # ===========================================
    
    def get_reference_price(self) -> Optional[float]:
        """기준 가격 결정 - LBank API 구조 완전 대응"""
        ticker = self.get_ticker()
        
        if not ticker:
            logger.error("❌ 티커 정보를 가져올 수 없습니다")
            return self.base_price
        
        try:
            # LBank API 응답 구조: data는 리스트이고, 첫 번째 요소에 심볼 정보가 있음
            ticker_data = self.response_handler.safe_get(ticker, 'data', [])
            
            logger.info(f"🔍 티커 데이터 타입: {type(ticker_data)}")
            
            # 데이터가 리스트인지 확인
            if not isinstance(ticker_data, list):
                logger.error(f"❌ 예상과 다른 데이터 타입: {type(ticker_data)}")
                return self.base_price
                
            if len(ticker_data) == 0:
                logger.error("❌ 티커 데이터 리스트가 비어있습니다")
                return self.base_price
            
            # 첫 번째 항목에서 심볼 정보 추출
            symbol_data = ticker_data[0]
            logger.info(f"🔍 심볼 데이터: {symbol_data}")
            
            # 심볼이 맞는지 확인
            symbol = self.response_handler.safe_get(symbol_data, 'symbol', '')
            if symbol != self.symbol:
                logger.warning(f"⚠️ 요청한 심볼({self.symbol})과 응답 심볼({symbol})이 다릅니다")
            
            # ticker 객체에서 가격 정보 추출
            ticker_info = self.response_handler.safe_get(symbol_data, 'ticker', {})
            
            if not isinstance(ticker_info, dict):
                logger.error(f"❌ 티커 정보가 딕셔너리가 아닙니다: {type(ticker_info)}")
                return self.base_price
            
            # latest 필드에서 현재 가격 추출
            latest_price = self.response_handler.safe_get(ticker_info, 'latest', None)
            
            if latest_price is None:
                logger.error(f"❌ 가격 정보를 찾을 수 없습니다. 티커 정보: {ticker_info}")
                return self.base_price
            
            market_price = float(latest_price)
            logger.info(f"🔍 추출된 시장 가격: ${market_price:.6f}")
            
            if market_price <= 0:
                logger.error(f"❌ 잘못된 시장 가격: {market_price}")
                return self.base_price
            
            # 기준가격이 없으면 현재 시장가로 설정
            if self.base_price is None:
                self.base_price = market_price
                logger.info(f"📍 기준 가격 설정: ${self.base_price:.6f}")
                return self.base_price
            
            # 시장가와 기준가의 차이가 크면 기준가 조정
            price_diff = abs(market_price - self.base_price) / self.base_price
            if price_diff > 0.01:  # 1% 이상 차이나면 조정
                old_price = self.base_price
                self.base_price = market_price
                logger.info(f"📍 기준 가격 업데이트: ${old_price:.6f} → ${self.base_price:.6f} (변동: {price_diff*100:.2f}%)")
            
            return self.base_price
            
        except (TypeError, ValueError, ZeroDivisionError) as e:
            logger.error(f"❌ 기준 가격 계산 오류: {e}")
            logger.error(f"🔍 원본 티커 데이터: {ticker}")
            return self.base_price

    def generate_order_prices(self, reference_price: float) -> tuple:
        """호가창에 배치할 주문 가격들 생성"""
        if not reference_price or reference_price <= 0:
            logger.error(f"❌ 잘못된 기준 가격: {reference_price}")
            return [], []
        
        buy_prices = []
        sell_prices = []
        
        try:
            # 매수 호가 (기준가 아래)
            for i in range(1, self.order_layers + 1):
                spread_multiplier = i * self.spread_percentage / self.order_layers
                buy_price = reference_price * (1 - spread_multiplier)
                buy_prices.append(round(buy_price, 6))
            
            # 매도 호가 (기준가 위)
            for i in range(1, self.order_layers + 1):
                spread_multiplier = i * self.spread_percentage / self.order_layers
                sell_price = reference_price * (1 + spread_multiplier)
                sell_prices.append(round(sell_price, 6))
            
            return buy_prices, sell_prices
            
        except Exception as e:
            logger.error(f"❌ 주문 가격 생성 오류: {e}")
            return [], []

    def generate_order_amount(self) -> float:
        """주문 수량 생성 (랜덤)"""
        try:
            return round(random.uniform(self.min_order_amount, self.max_order_amount), 2)
        except Exception as e:
            logger.error(f"❌ 주문 수량 생성 오류: {e}")
            return self.min_order_amount

    def cancel_all_orders(self):
        """모든 주문 취소"""
        canceled_count = 0
        try:
            for side in ['buy', 'sell']:
                for order_id in self.current_orders[side][:]:  # 복사본 사용
                    if self.cancel_order(order_id):
                        canceled_count += 1
                        self.current_orders[side].remove(order_id)
            
            if canceled_count > 0:
                logger.info(f"🗑️ {canceled_count}개 주문 취소 완료")
        except Exception as e:
            logger.error(f"❌ 주문 취소 오류: {e}")

    def place_market_making_orders(self) -> bool:
        """마켓 메이킹 주문 배치"""
        try:
            reference_price = self.get_reference_price()
            if not reference_price:
                logger.error("❌ 기준 가격을 가져올 수 없습니다")
                return False
            
            balance = self.get_account_balance()
            if not balance:
                logger.error("❌ 잔고 정보를 가져올 수 없습니다")
                return False
            
            # 기존 주문들 취소
            self.cancel_all_orders()
            
            # 새 주문 가격 생성
            buy_prices, sell_prices = self.generate_order_prices(reference_price)
            
            if not buy_prices or not sell_prices:
                logger.error("❌ 주문 가격 생성 실패")
                return False
            
            # 매수 주문 배치
            buy_orders_placed = 0
            required_usdt = sum(price * self.generate_order_amount() for price in buy_prices)
            
            if balance['usdt'] >= required_usdt:
                for price in buy_prices:
                    amount = self.generate_order_amount()
                    order_id = self.place_order('buy', amount, price)
                    if order_id:
                        self.current_orders['buy'].append(order_id)
                        buy_orders_placed += 1
            else:
                logger.warning(f"⚠️ USDT 잔고 부족: {balance['usdt']:.2f} < {required_usdt:.2f}")
            
            # 매도 주문 배치  
            sell_orders_placed = 0
            required_spsi = sum(self.generate_order_amount() for _ in sell_prices)
            
            if balance['spsi'] >= required_spsi:
                for price in sell_prices:
                    amount = self.generate_order_amount()
                    order_id = self.place_order('sell', amount, price)
                    if order_id:
                        self.current_orders['sell'].append(order_id)
                        sell_orders_placed += 1
            else:
                logger.warning(f"⚠️ SPSI 잔고 부족: {balance['spsi']:.2f} < {required_spsi:.2f}")
            
            logger.info(f"📋 주문 배치 완료 - 매수: {buy_orders_placed}개, 매도: {sell_orders_placed}개")
            logger.info(f"💰 기준가: ${reference_price:.6f} | USDT: {balance['usdt']:.1f} | SPSI: {balance['spsi']:.1f}")
            
            return buy_orders_placed > 0 or sell_orders_placed > 0
            
        except Exception as e:
            logger.error(f"❌ 마켓 메이킹 주문 배치 오류: {e}")
            return False

    def execute_fake_trade(self):
        """가짜 거래 실행 (거래량 증가 목적)"""
        try:
            reference_price = self.get_reference_price()
            if not reference_price:
                return
            
            balance = self.get_account_balance()
            if not balance:
                return
            
            # 작은 변동폭으로 가격 조정
            price_change = random.uniform(-self.price_volatility, self.price_volatility)
            trade_price = reference_price * (1 + price_change)
            trade_price = round(trade_price, 6)
            
            # 작은 수량으로 거래
            trade_amount = random.uniform(10, 50)
            
            # 50% 확률로 매수/매도 선택
            if random.choice([True, False]) and balance['usdt'] >= trade_amount * trade_price:
                # 시장가 매수
                order_id = self.place_market_order('buy_market', trade_amount * trade_price)
                if order_id:
                    logger.info(f"🔄 가짜 매수 거래: {trade_amount:.1f} SPSI @ ${trade_price:.6f}")
            elif balance['spsi'] >= trade_amount:
                # 시장가 매도
                order_id = self.place_market_order('sell_market', trade_amount)
                if order_id:
                    logger.info(f"🔄 가짜 매도 거래: {trade_amount:.1f} SPSI @ ${trade_price:.6f}")
        
        except Exception as e:
            logger.error(f"💥 가짜 거래 실행 오류: {e}")

    def place_market_order(self, order_type: str, amount: float) -> Optional[str]:
        """시장가 주문"""
        endpoint = "/create_order.do"
        params = {
            'symbol': self.symbol,
            'type': order_type,
            'amount': str(amount)
        }
        
        response = self._make_request('POST', endpoint, params, signed=True, silent=True)
        
        if response and response.get("success"):
            data = response.get("data", {})
            error_code = self.response_handler.safe_get(data, 'error_code', -1)
            if error_code == 0:
                return self.response_handler.safe_get(data, 'order_id')
        
        return None

    def update_base_price(self):
        """기준 가격 랜덤 업데이트"""
        try:
            if self.base_price:
                # 0.1% ~ 0.3% 범위에서 랜덤 조정
                price_change = random.uniform(-0.003, 0.003)
                self.base_price *= (1 + price_change)
                self.base_price = round(self.base_price, 6)
                logger.info(f"📈 기준 가격 조정: ${self.base_price:.6f} ({price_change*100:+.2f}%)")
        except Exception as e:
            logger.error(f"❌ 기준 가격 업데이트 오류: {e}")

    # ===========================================
    # 마켓 메이킹 메인 루프
    # ===========================================
    
    def start_market_making(self):
        """마켓 메이킹 시작"""
        if self.running:
            logger.warning("⚠️ 이미 마켓 메이킹이 실행 중입니다")
            return
        
        self.running = True
        logger.info(f"🏭 마켓 메이킹 시작!")
        logger.info(f"⚙️ 설정:")
        logger.info(f"   - 스프레드: {self.spread_percentage*100:.1f}%")
        logger.info(f"   - 주문 레이어: {self.order_layers}개")
        logger.info(f"   - 주문 갱신: {self.order_refresh_interval}초")
        logger.info(f"   - 가짜 거래: {self.fake_trade_interval}초")
        
        def market_making_loop():
            last_order_refresh = 0
            last_fake_trade = 0
            last_price_update = 0
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    # 주문 갱신
                    if current_time - last_order_refresh >= self.order_refresh_interval:
                        if self.place_market_making_orders():
                            last_order_refresh = current_time
                        else:
                            # 실패 시 30초 후 재시도
                            time.sleep(30)
                    
                    # 가짜 거래 실행
                    if current_time - last_fake_trade >= self.fake_trade_interval:
                        self.execute_fake_trade()
                        last_fake_trade = current_time
                    
                    # 기준 가격 업데이트
                    if current_time - last_price_update >= self.price_update_interval:
                        self.update_base_price()
                        last_price_update = current_time
                    
                    time.sleep(10)  # 10초마다 체크
                    
                except KeyboardInterrupt:
                    logger.info("⏹️ 사용자 중단 요청")
                    break
                except Exception as e:
                    logger.error(f"💥 마켓 메이킹 루프 오류: {e}")
                    time.sleep(30)  # 오류 시 30초 대기
        
        self.market_making_thread = threading.Thread(target=market_making_loop, daemon=True)
        self.market_making_thread.start()

    def stop_market_making(self):
        """마켓 메이킹 중지"""
        if not self.running:
            logger.warning("⚠️ 마켓 메이킹이 실행되고 있지 않습니다")
            return
        
        self.running = False
        logger.info("⏹️ 마켓 메이킹 중지 요청됨")
        
        # 모든 주문 취소
        self.cancel_all_orders()
        
        if self.market_making_thread:
            self.market_making_thread.join(timeout=5)
        
        logger.info("✅ 마켓 메이킹 완전 중지됨")

    # ===========================================
    # 모니터링 및 통계
    # ===========================================
    
    def get_market_making_status(self):
        """마켓 메이킹 상태 조회"""
        try:
            open_orders = self.get_open_orders()
            buy_orders = [o for o in open_orders if self.response_handler.safe_get(o, 'type') == 'buy']
            sell_orders = [o for o in open_orders if self.response_handler.safe_get(o, 'type') == 'sell']
            
            balance = self.get_account_balance()
            current_price = self.get_reference_price()  # 이미 수정된 메서드 사용
            
            print(f"\n{'='*60}")
            print(f"🏭 마켓 메이킹 상태 (V4)")
            print(f"{'='*60}")
            print(f"📊 현재 가격: ${current_price:.6f}" if current_price else "📊 현재 가격: 조회 실패")
            
            if balance:
                print(f"💰 USDT 잔고: {balance['usdt']:.2f}")
                print(f"🪙 SPSI 잔고: {balance['spsi']:.2f}")
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"📋 미체결 주문: 매수 {len(buy_orders)}개, 매도 {len(sell_orders)}개")
            print(f"🔄 실행 상태: {'활성' if self.running else '중지'}")
            
            if buy_orders:
                print(f"\n💚 매수 주문:")
                for order in buy_orders[:5]:  # 상위 5개만
                    price = self.response_handler.safe_get(order, 'price', 'N/A')
                    amount = self.response_handler.safe_get(order, 'amount', 'N/A')
                    print(f"   ${price} x {amount}")
            
            if sell_orders:
                print(f"\n💛 매도 주문:")
                for order in sell_orders[:5]:  # 상위 5개만
                    price = self.response_handler.safe_get(order, 'price', 'N/A')
                    amount = self.response_handler.safe_get(order, 'amount', 'N/A')
                    print(f"   ${price} x {amount}")
                    
        except Exception as e:
            logger.error(f"❌ 상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    def test_market_making_setup(self):
        """마켓 메이킹 설정 테스트 - 강화된 버전"""
        logger.info("🧪 마켓 메이킹 설정 테스트 시작 (V4)")
        
        # 1. API 연결 테스트
        logger.info("1️⃣ API 연결 테스트...")
        ticker = self.get_ticker()
        if not ticker:
            logger.error("❌ 티커 조회 실패 - API 연결 문제")
            return False
        logger.info("✅ 티커 조회 성공")
        
        # 2. 인증 테스트 (잔고 확인)
        logger.info("2️⃣ 인증 테스트...")
        balance = self.get_account_balance()
        if not balance:
            logger.error("❌ 잔고 조회 실패 - API 인증 문제")
            return False
        logger.info("✅ 잔고 조회 성공")
        
        # 3. 기준 가격 설정 테스트
        logger.info("3️⃣ 기준 가격 설정 테스트...")
        reference_price = self.get_reference_price()
        if not reference_price:
            logger.error("❌ 기준 가격 설정 실패")
            return False
        logger.info(f"✅ 기준 가격 설정 성공: ${reference_price:.6f}")
        
        # 4. 충분한 잔고 확인
        logger.info("4️⃣ 잔고 충분성 검사...")
        min_usdt_needed = self.max_order_amount * self.order_layers * reference_price * 0.1
        min_spsi_needed = self.max_order_amount * self.order_layers
        
        logger.info(f"💰 현재 잔고 - USDT: {balance['usdt']:.2f}, SPSI: {balance['spsi']:.2f}")
        logger.info(f"📋 권장 잔고 - USDT: {min_usdt_needed:.2f}, SPSI: {min_spsi_needed:.2f}")
        
        if balance['usdt'] < min_usdt_needed:
            logger.warning(f"⚠️ USDT 잔고 부족 (현재: {balance['usdt']:.2f}, 권장: {min_usdt_needed:.2f})")
        else:
            logger.info("✅ USDT 잔고 충분")
            
        if balance['spsi'] < min_spsi_needed:
            logger.warning(f"⚠️ SPSI 잔고 부족 (현재: {balance['spsi']:.2f}, 권장: {min_spsi_needed:.2f})")
        else:
            logger.info("✅ SPSI 잔고 충분")
        
        # 5. 주문 가격 생성 테스트
        logger.info("5️⃣ 주문 가격 생성 테스트...")
        buy_prices, sell_prices = self.generate_order_prices(reference_price)
        if not buy_prices or not sell_prices:
            logger.error("❌ 주문 가격 생성 실패")
            return False
        logger.info(f"✅ 주문 가격 생성 성공 (매수: {len(buy_prices)}개, 매도: {len(sell_prices)}개)")
        
        # 6. 테스트 주문 배치 (실제로는 하지 않음)
        logger.info("6️⃣ 주문 시스템 준비 확인...")
        logger.info("✅ 모든 테스트 통과 - 마켓 메이킹 준비 완료!")
        
        return True

    def debug_api_response(self, endpoint: str, params: dict = None, signed: bool = False):
        """API 응답 디버깅 헬퍼 함수 - 상세 버전"""
        logger.info(f"🔍 API 디버깅: {endpoint}")
        
        response = self._make_request('GET' if not signed else 'POST', endpoint, params, signed, silent=False)
        
        print(f"\n{'='*50}")
        print(f"🔍 API 디버깅 결과: {endpoint}")
        print(f"{'='*50}")
        print(f"성공 여부: {response.get('success') if response else False}")
        print(f"에러 메시지: {response.get('error') if response else 'No response'}")
        print(f"데이터 타입: {type(response.get('data')) if response else 'N/A'}")
        
        # 잔고 API인 경우 상세 분석
        if 'user_info' in endpoint and response and response.get('success'):
            raw_data = response.get('data', {})
            print(f"\n📊 잔고 데이터 상세 분석:")
            print(f"응답 레벨 키들: {list(raw_data.keys())}")
            
            # 실제 데이터는 data.data 안에 있을 수 있음
            actual_data = raw_data.get('data', raw_data)
            print(f"실제 데이터 키들: {list(actual_data.keys()) if isinstance(actual_data, dict) else 'Not dict'}")
            
            for section in ['free', 'asset', 'freeze', 'toBtc']:
                if section in actual_data:
                    section_data = actual_data[section]
                    print(f"\n🔍 '{section}' 섹션:")
                    print(f"  타입: {type(section_data)}")
                    
                    if isinstance(section_data, dict):
                        keys = list(section_data.keys())
                        print(f"  키들 (처음 20개): {keys[:20]}")
                        
                        # USDT, SPSI 찾기
                        for coin in ['usdt', 'USDT', 'spsi', 'SPSI']:
                            if coin in section_data:
                                coin_value = section_data[coin]
                                print(f"  💰 {coin}: {coin_value} (타입: {type(coin_value)})")
                    else:
                        content = str(section_data)
                        print(f"  내용: {content[:200]}...")
        
        print(f"\n원본 응답 (처음 500자): {str(response.get('raw_response', 'N/A'))[:500]}...")
        print(f"{'='*50}")

def main():
    """메인 실행 함수 - 에러 처리 강화"""
    # API 키 설정
    API_KEY = os.getenv('LBANK_API_KEY', '73658848-ac66-435f-a43d-eca72f98ecbf')
    API_SECRET = os.getenv('LBANK_API_SECRET', '18F00DC6DCD01F2E19452ED52F716D3D')
    
    if not API_KEY or not API_SECRET:
        logger.error("❌ API 키가 설정되지 않았습니다")
        return
    
    try:
        # 마켓 메이커 초기화
        mm = LBankMarketMaker(API_KEY, API_SECRET)
        logger.info("✅ 마켓 메이커 초기화 완료")
        
        while True:
            try:
                print("\n" + "="*60)
                print("🏭 LBank 마켓 메이커 시스템 V4 - 완전 에러 해결 버전")
                print("="*60)
                print("1. 마켓 메이킹 상태 확인")
                print("2. 설정 테스트")
                print("3. 마켓 메이킹 시작")
                print("4. 마켓 메이킹 중지") 
                print("5. 모든 주문 취소")
                print("6. 설정 조정")
                print("7. API 디버깅")
                print("0. 종료")
                
                choice = input("\n선택하세요 (0-7): ").strip()
                
                if choice == '1':
                    mm.get_market_making_status()
                    
                elif choice == '2':
                    if mm.test_market_making_setup():
                        print("✅ 모든 테스트 통과!")
                    else:
                        print("❌ 테스트 실패!")
                    
                elif choice == '3':
                    mm.start_market_making()
                    print("✅ 마켓 메이킹 시작됨. 거래량 증가를 위해 지속적으로 작동합니다.")
                    
                elif choice == '4':
                    mm.stop_market_making()
                    
                elif choice == '5':
                    mm.cancel_all_orders()
                    print("✅ 모든 주문 취소 완료")
                    
                elif choice == '6':
                    print("\n⚙️ 현재 설정:")
                    print(f"  - 스프레드: {mm.spread_percentage*100:.1f}%")
                    print(f"  - 주문 레이어: {mm.order_layers}개")
                    print(f"  - 주문 수량: {mm.min_order_amount} ~ {mm.max_order_amount}")
                    print(f"  - 주문 갱신 간격: {mm.order_refresh_interval}초")
                    print(f"  - 가짜 거래 간격: {mm.fake_trade_interval}초")
                    
                    try:
                        new_spread = input(f"새 스프레드 (현재 {mm.spread_percentage*100:.1f}%, Enter=유지): ").strip()
                        if new_spread:
                            mm.spread_percentage = float(new_spread) / 100
                        
                        new_layers = input(f"새 주문 레이어 (현재 {mm.order_layers}개, Enter=유지): ").strip()
                        if new_layers:
                            mm.order_layers = int(new_layers)
                        
                        print("✅ 설정 업데이트 완료")
                    except ValueError:
                        print("❌ 잘못된 값 입력")
                
                elif choice == '7':
                    print("\n🔍 API 디버깅 메뉴:")
                    print("1. 티커 정보 조회")
                    print("2. 잔고 조회")
                    print("3. 호가창 조회")
                    print("4. 미체결 주문 조회")
                    print("5. 대체 주문 조회 (/orders_info.do)")
                    
                    debug_choice = input("디버깅할 API (1-5): ").strip()
                    
                    if debug_choice == '1':
                        mm.debug_api_response("/ticker.do", {"symbol": mm.symbol})
                    elif debug_choice == '2':
                        mm.debug_api_response("/user_info.do", signed=True)
                    elif debug_choice == '3':
                        mm.debug_api_response("/depth.do", {"symbol": mm.symbol, "size": 10})
                    elif debug_choice == '5':
                        mm.debug_api_response("/orders_info.do", {
                            "symbol": mm.symbol,
                            "order_id": "-1"  # -1은 모든 주문
                        }, signed=True)
                    
                    if debug_choice == '1':
                        mm.debug_api_response("/ticker.do", {"symbol": mm.symbol})
                    elif debug_choice == '2':
                        mm.debug_api_response("/user_info.do", signed=True)
                    elif debug_choice == '3':
                        mm.debug_api_response("/depth.do", {"symbol": mm.symbol, "size": 10})
                    elif debug_choice == '4':
                        print("미체결 주문 조회 방법 선택:")
                        print("1. 기본 방법 (symbol + pagination)")
                        print("2. 심플 방법 (symbol만)")
                        print("3. 전체 주문 조회")
                        
                        method = input("방법 선택 (1-3): ").strip()
                        
                        if method == "1":
                            mm.debug_api_response("/orders_info_no_deal.do", {
                                "symbol": mm.symbol,
                                "current_page": "1", 
                                "page_length": "100"
                            }, signed=True)
                        elif method == "2":
                            mm.debug_api_response("/orders_info_no_deal.do", {
                                "symbol": mm.symbol
                            }, signed=True)
                        elif method == "3":
                            mm.debug_api_response("/orders_info_no_deal.do", {
                                "current_page": "1", 
                                "page_length": "100"
                            }, signed=True)
                        else:
                            print("잘못된 선택")
                        
                elif choice == '0':
                    mm.stop_market_making()
                    print("👋 프로그램을 종료합니다.")
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