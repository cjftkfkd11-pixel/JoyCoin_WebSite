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

# 간단한 로깅 설정
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

class LBankMarketMaker:
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.market_making_thread = None
        
        # 기본 설정
        self.symbol = "spsi_usdt"
        self.spread_percentage = 0.005
        self.order_layers = 5
        
        # 🔥 최소 가치 설정 (핵심 수정사항)
        self.min_order_value_usdt = 5.0
        self.max_order_value_usdt = 20.0
        self.min_trade_value_usdt = 10.0
        self.max_trade_value_usdt = 50.0
        
        self.order_refresh_interval = 60
        self.fake_trade_interval = 120
        self.price_update_interval = 300
        self.price_volatility = 0.002
        self.base_price = None
        self.current_orders = {'buy': [], 'sell': []}
        
        # 통계
        self.daily_volume = 0
        self.daily_trades = 0
        self.total_fees = 0.0
        
        self.response_handler = SafeAPIResponseHandler()
        
        print("✅ LBank 마켓 메이커 초기화 완료")
        logger.info("마켓 메이커 시스템 초기화 완료")

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

    # 🔥 핵심 수정: 가치 기반 수량 계산
    def calculate_amount_by_value(self, target_value_usdt: float, price: float) -> float:
        """가격 기준으로 적절한 주문 수량 계산"""
        try:
            if not price or price <= 0:
                return 0
            amount = target_value_usdt / price
            return round(amount, 2)
        except Exception:
            return 0

    def generate_order_amount_by_value(self, current_price: float) -> float:
        """가치 기준 호가창 주문량 생성"""
        try:
            target_value = random.uniform(self.min_order_value_usdt, self.max_order_value_usdt)
            amount = self.calculate_amount_by_value(target_value, current_price)
            
            # 최소 500 SPSI 보장
            if amount < 500:
                amount = random.uniform(500, 2000)
            
            return amount
        except Exception:
            return 500

    def generate_trade_amount_by_value(self, current_price: float) -> float:
        """가치 기준 자가매매 거래량 생성"""
        try:
            target_value = random.uniform(self.min_trade_value_usdt, self.max_trade_value_usdt)
            amount = self.calculate_amount_by_value(target_value, current_price)
            
            # 최소 1000 SPSI 보장
            if amount < 1000:
                amount = random.uniform(1000, 5000)
            
            return amount
        except Exception:
            return 1000

    # 기본 API 메서드들
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

    # 🔥 핵심 수정: 최소 가치 검증 포함 주문
    def place_order_with_validation(self, side: str, amount: float, price: float) -> Optional[str]:
        """주문 등록 전 최소 요구사항 검증"""
        try:
            order_value = amount * price
            
            # 최소 주문 가치 확인 ($1 이상)
            if order_value < 1.0:
                logger.warning(f"주문 가치 부족: ${order_value:.4f} < $1.00")
                # 최소 가치로 수량 재계산
                amount = 1.0 / price
                amount = round(amount, 2)
                order_value = amount * price
                logger.info(f"수량 조정: {amount:,.0f} SPSI (가치: ${order_value:.2f})")
            
            return self.place_order(side, amount, price)
            
        except Exception as e:
            logger.error(f"주문 검증 오류: {e}")
            return None

    def place_order(self, side: str, amount: float, price: float) -> Optional[str]:
        endpoint = "/create_order.do"
        params = {
            'symbol': self.symbol,
            'type': side,
            'amount': str(amount),
            'price': str(price)
        }
        
        order_value = amount * price
        logger.info(f"주문 시도: {side} {amount:,.2f} SPSI @ ${price:.6f} (가치: ${order_value:.4f} USDT)")
        
        response = self._make_request('POST', endpoint, params, signed=True)
        
        if not response or not response.get("success"):
            logger.error(f"주문 등록 실패: {response.get('error') if response else 'No response'}")
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
            return str(order_id) if order_id else None
            
        except Exception as e:
            logger.error(f"주문 응답 파싱 오류: {e}")
            return None

    # 자가매매 시스템
    def execute_arbitrage_trade(self) -> bool:
        """수정된 자가매매 실행 - 상세 디버깅 포함"""
        try:
            print("   🔍 기준 가격 조회 중...")
            reference_price = self.get_reference_price()
            if not reference_price:
                print("   ❌ 기준 가격 조회 실패")
                return False
            print(f"   ✅ 기준 가격: ${reference_price:.6f}")
            
            print("   🔍 잔고 조회 중...")
            balance = self.get_account_balance()
            if not balance:
                print("   ❌ 잔고 조회 실패")
                return False
            print(f"   ✅ 잔고 - USDT: ${balance['usdt']:.2f}, SPSI: {balance['spsi']:.2f}")
            
            # 가치 기준으로 거래량 생성
            trade_amount = self.generate_trade_amount_by_value(reference_price)
            
            price_variation = random.uniform(-0.0005, 0.0005)
            trade_price = reference_price * (1 + price_variation)
            trade_price = round(trade_price, 6)
            
            trade_value = trade_amount * trade_price
            
            print(f"   📊 거래 계획:")
            print(f"      - 수량: {trade_amount:,.0f} SPSI")
            print(f"      - 가격: ${trade_price:.6f}")
            print(f"      - 가치: ${trade_value:.2f}")
            
            logger.info(f"자가매매 계획: {trade_amount:,.0f} SPSI @ ${trade_price:.6f} (가치: ${trade_value:.2f})")
            
            # 최소 거래 가치 확인
            if trade_value < 1.0:
                print(f"   ⚠️ 거래 가치 부족: ${trade_value:.4f} < $1.00")
                logger.warning(f"거래 가치 부족: ${trade_value:.4f} < $1.00, 거래 건너뜀")
                return False
            
            # 잔고 확인 및 거래 방향 결정
            can_buy = balance['usdt'] >= trade_value
            can_sell = balance['spsi'] >= trade_amount
            
            print(f"   🔍 거래 가능성 체크:")
            print(f"      - 매수 가능: {can_buy} (필요 USDT: ${trade_value:.2f})")
            print(f"      - 매도 가능: {can_sell} (필요 SPSI: {trade_amount:,.0f})")
            
            if not can_buy and not can_sell:
                print("   ❌ 매수/매도 모두 불가능 (잔고 부족)")
                return False
            
            # 거래 실행
            if can_buy and (not can_sell or random.choice([True, False])):
                print("   🔄 시장가 매수 시도...")
                print(f"      - 주문 타입: buy_market")
                print(f"      - 주문 금액: ${trade_value:.2f} USDT")
                
                order_id = self.place_market_order('buy_market', trade_value)
                if order_id:
                    print(f"   ✅ 매수 주문 성공! ID: {order_id}")
                    self.daily_volume += trade_amount
                    self.daily_trades += 1
                    estimated_fee = trade_value * 0.001
                    self.total_fees += estimated_fee
                    logger.info(f"자가매매 매수 완료: {trade_amount:,.0f} SPSI")
                    return True
                else:
                    print("   ❌ 매수 주문 실패")
                    return False
                    
            elif can_sell:
                print("   🔄 시장가 매도 시도...")
                print(f"      - 주문 타입: sell_market")
                print(f"      - 주문 수량: {trade_amount:,.0f} SPSI")
                
                order_id = self.place_market_order('sell_market', trade_amount)
                if order_id:
                    print(f"   ✅ 매도 주문 성공! ID: {order_id}")
                    self.daily_volume += trade_amount
                    self.daily_trades += 1
                    estimated_fee = trade_value * 0.001
                    self.total_fees += estimated_fee
                    logger.info(f"자가매매 매도 완료: {trade_amount:,.0f} SPSI")
                    return True
                else:
                    print("   ❌ 매도 주문 실패")
                    return False
            else:
                print("   ❌ 예상치 못한 조건")
                return False
            
        except Exception as e:
            print(f"   💥 자가매매 실행 중 오류: {e}")
            logger.error(f"자가매매 실행 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    def place_market_order(self, order_type: str, amount: float) -> Optional[str]:
        """시장가 주문 - 상세 디버깅 포함"""
        print(f"      🔍 시장가 주문 API 호출:")
        print(f"         - 타입: {order_type}")
        print(f"         - 수량: {amount}")
        
        endpoint = "/create_order.do"
        params = {
            'symbol': self.symbol,
            'type': order_type,
            'amount': str(amount)
        }
        
        print(f"         - 파라미터: {params}")
        
        response = self._make_request('POST', endpoint, params, signed=True, silent=False)
        
        print(f"      🔍 API 응답:")
        print(f"         - 성공: {response.get('success') if response else False}")
        print(f"         - 에러: {response.get('error') if response else 'None'}")
        
        if response and response.get("success"):
            data = response.get("data", {})
            print(f"         - 응답 데이터: {data}")
            
            error_code = self.response_handler.safe_get(data, 'error_code', -1)
            print(f"         - 에러 코드: {error_code}")
            
            if error_code == 0:
                order_id = self.response_handler.safe_get(data, 'order_id')
                print(f"         - 주문 ID: {order_id}")
                return str(order_id) if order_id else None
            else:
                error_msg = self.response_handler.safe_get(data, 'msg', 'Unknown error')
                print(f"         - 에러 메시지: {error_msg}")
                return None
        else:
            print(f"         - 응답 실패")
            if response:
                print(f"         - 원본 응답: {response.get('raw_response')}")
            return None

    # 간단한 상태 확인
    def get_status(self):
        try:
            balance = self.get_account_balance()
            current_price = self.get_reference_price()
            
            print(f"\n{'='*50}")
            print(f"🏭 마켓 메이커 상태")
            print(f"{'='*50}")
            print(f"📊 현재 가격: ${current_price:.6f}" if current_price else "📊 현재 가격: 조회 실패")
            
            if balance:
                print(f"💰 USDT 잔고: {balance['usdt']:.2f}")
                print(f"🪙 SPSI 잔고: {balance['spsi']:.2f}")
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"🔄 실행 상태: {'활성' if self.running else '중지'}")
            print(f"📊 일일 통계: 거래량 {self.daily_volume:,.0f} SPSI, 거래 {self.daily_trades}회")
            print(f"💳 예상 수수료: ${self.total_fees:.2f}")
            
            if current_price:
                sample_order_amount = self.generate_order_amount_by_value(current_price)
                sample_order_value = sample_order_amount * current_price
                print(f"🎯 주문 계획: ~{sample_order_amount:,.0f} SPSI (가치: ${sample_order_value:.2f})")
                
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    # 테스트 함수
    def test_setup(self):
        print("🧪 설정 테스트 시작...")
        
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
        
        # 4. 가치 기반 수량 테스트
        print("4️⃣ 가치 기반 수량 테스트...")
        test_order_amount = self.generate_order_amount_by_value(reference_price)
        test_order_value = test_order_amount * reference_price
        
        test_trade_amount = self.generate_trade_amount_by_value(reference_price)
        test_trade_value = test_trade_amount * reference_price
        
        print(f"✅ 주문량: {test_order_amount:,.0f} SPSI (가치: ${test_order_value:.2f})")
        print(f"✅ 거래량: {test_trade_amount:,.0f} SPSI (가치: ${test_trade_value:.2f})")
        
        if test_order_value < 1.0:
            print(f"⚠️ 주문 가치가 최소 요구사항보다 낮습니다")
        if test_trade_value < 1.0:
            print(f"⚠️ 거래 가치가 최소 요구사항보다 낮습니다")
        
        print("✅ 모든 테스트 통과!")
        return True

def main():
    print("🏭 LBank 마켓 메이커 시스템 시작...")
    
    # API 키 설정
    API_KEY = os.getenv('LBANK_API_KEY', '73658848-ac66-435f-a43d-eca72f98ecbf')
    API_SECRET = os.getenv('LBANK_API_SECRET', '18F00DC6DCD01F2E19452ED52F716D3D')
    
    if not API_KEY or not API_SECRET:
        print("❌ API 키가 설정되지 않았습니다")
        input("Enter를 눌러 종료...")
        return
    
    try:
        print("📡 마켓 메이커 초기화 중...")
        mm = LBankMarketMaker(API_KEY, API_SECRET)
        
        while True:
            try:
                print("\n" + "="*50)
                print("🏭 LBank 마켓 메이커 - 최소값 검증 버전")
                print("="*50)
                print("1. 상태 확인")
                print("2. 설정 테스트")
                print("3. 자가매매 테스트")
                print("0. 종료")
                
                choice = input("\n선택하세요 (0-3): ").strip()
                
                if choice == '1':
                    mm.get_status()
                    
                elif choice == '2':
                    if mm.test_setup():
                        print("✅ 모든 테스트 통과!")
                    else:
                        print("❌ 테스트 실패!")
                    
                elif choice == '3':
                    print("🔄 자가매매 테스트 실행...")
                    result = mm.execute_arbitrage_trade()
                    if result:
                        print("✅ 자가매매 테스트 성공!")
                    else:
                        print("❌ 자가매매 테스트 실패!")
                    
                elif choice == '0':
                    print("👋 프로그램을 종료합니다.")
                    break
                    
                else:
                    print("❌ 잘못된 선택입니다.")
                    
            except KeyboardInterrupt:
                print("\n⏹️ 사용자 중단 요청")
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
