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
import matplotlib.pyplot as plt
import pandas as pd
from collections import deque
import numpy as np

# 안전한 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingChart:
    """거래 차트 및 모니터링 클래스"""
    
    def __init__(self):
        self.price_history = deque(maxlen=500)
        self.volume_history = deque(maxlen=500)
        self.balance_history = deque(maxlen=500)
        self.trade_history = deque(maxlen=100)
        self.buy_orders = deque(maxlen=100)
        self.sell_orders = deque(maxlen=100)
        
        # 실시간 통계
        self.total_buys = 0
        self.total_sells = 0
        self.total_buy_volume = 0
        self.total_sell_volume = 0
        
    def add_price_data(self, price: float, volume: float = 0):
        """가격 데이터 추가"""
        timestamp = datetime.now()
        self.price_history.append({
            'time': timestamp,
            'price': price,
            'volume': volume
        })
        
    def add_balance_data(self, usdt: float, spsi: float):
        """잔고 데이터 추가"""
        timestamp = datetime.now()
        self.balance_history.append({
            'time': timestamp,
            'usdt': usdt,
            'spsi': spsi
        })
        
    def add_trade_data(self, trade_type: str, amount: float, price: float, success: bool):
        """거래 데이터 추가"""
        timestamp = datetime.now()
        trade_data = {
            'time': timestamp,
            'type': trade_type,
            'amount': amount,
            'price': price,
            'value': amount * price,
            'success': success
        }
        
        self.trade_history.append(trade_data)
        
        if success:
            if trade_type == 'buy':
                self.buy_orders.append(trade_data)
                self.total_buys += 1
                self.total_buy_volume += amount
            else:
                self.sell_orders.append(trade_data)
                self.total_sells += 1
                self.total_sell_volume += amount
    
    def plot_price_chart(self, save_path: str = None):
        """가격 차트 생성"""
        if len(self.price_history) < 2:
            print("⚠️ 가격 데이터 부족 (최소 2개 필요)")
            return
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # 가격 차트
        times = [d['time'] for d in self.price_history]
        prices = [d['price'] for d in self.price_history]
        
        ax1.plot(times, prices, 'b-', linewidth=2, label='SPSI 가격')
        ax1.set_title('SPSI/USDT 가격 변화', fontsize=14)
        ax1.set_ylabel('가격 (USDT)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # 매수/매도 포인트 표시
        if self.buy_orders:
            buy_times = [d['time'] for d in self.buy_orders]
            buy_prices = [d['price'] for d in self.buy_orders]
            ax1.scatter(buy_times, buy_prices, color='green', s=50, alpha=0.7, label='매수')
            
        if self.sell_orders:
            sell_times = [d['time'] for d in self.sell_orders]
            sell_prices = [d['price'] for d in self.sell_orders]
            ax1.scatter(sell_times, sell_prices, color='red', s=50, alpha=0.7, label='매도')
        
        # 잔고 차트
        if self.balance_history:
            balance_times = [d['time'] for d in self.balance_history]
            usdt_balances = [d['usdt'] for d in self.balance_history]
            spsi_balances = [d['spsi'] for d in self.balance_history]
            
            ax2_twin = ax2.twinx()
            
            ax2.plot(balance_times, usdt_balances, 'g-', linewidth=2, label='USDT 잔고')
            ax2_twin.plot(balance_times, spsi_balances, 'r-', linewidth=2, label='SPSI 잔고')
            
            ax2.set_title('잔고 변화', fontsize=14)
            ax2.set_ylabel('USDT 잔고', fontsize=12, color='g')
            ax2_twin.set_ylabel('SPSI 잔고', fontsize=12, color='r')
            ax2.grid(True, alpha=0.3)
            
            # 범례 통합
            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax2_twin.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 차트 저장됨: {save_path}")
        
        plt.show()
        
    def get_trading_stats(self) -> Dict[str, Any]:
        """거래 통계 반환"""
        buy_success_rate = (self.total_buys / max(1, len([t for t in self.trade_history if t['type'] == 'buy']))) * 100
        sell_success_rate = (self.total_sells / max(1, len([t for t in self.trade_history if t['type'] == 'sell']))) * 100
        
        return {
            'total_trades': len(self.trade_history),
            'total_buys': self.total_buys,
            'total_sells': self.total_sells,
            'buy_volume': self.total_buy_volume,
            'sell_volume': self.total_sell_volume,
            'buy_success_rate': buy_success_rate,
            'sell_success_rate': sell_success_rate,
            'volume_balance': abs(self.total_buy_volume - self.total_sell_volume),
            'recent_trades': list(self.trade_history)[-10:] if self.trade_history else []
        }

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

class ImprovedLBankSelfTrader:
    """개선된 LBank 자가매매 시스템 - 균형 잡힌 거래 + 차트 기능"""
    
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.trading_thread = None
        
        # 거래 설정
        self.symbol = "spsi_usdt"
        
        # 🔥 개선된 거래량 설정
        self.min_volume_per_5min = 20000
        self.max_volume_per_5min = 40000
        self.trade_interval = 60
        
        # 🔥 균형 잡힌 거래 설정
        self.balance_threshold = 0.8  # 80% 균형 유지
        self.force_balance_every = 5   # 5회마다 강제 균형
        self.balance_counter = 0
        
        # 🔥 개선된 가격 설정 (더 현실적)
        self.tight_spread = 0.0005     # 0.05% - 빠른 체결용
        self.normal_spread = 0.001     # 0.1% - 일반 거래용
        self.wide_spread = 0.002       # 0.2% - 호가창용
        
        # 거래 타입별 설정
        self.quick_trade_ratio = 0.4   # 40% 빠른 체결
        self.normal_trade_ratio = 0.4  # 40% 일반 거래
        self.orderbook_ratio = 0.2     # 20% 호가창
        
        # 최소 거래 설정
        self.min_order_size = 100
        self.min_trade_value_usd = 1.0
        self.max_trade_value_usd = 15.0
        
        self.base_price = None
        self.current_orders = []
        
        # 통계 및 모니터링
        self.total_volume_today = 0
        self.total_trades_today = 0
        self.total_fees_paid = 0.0
        self.successful_buys = 0
        self.successful_sells = 0
        
        # 🔥 차트 시스템 추가
        self.chart = TradingChart()
        
        self.response_handler = SafeAPIResponseHandler()
        
        print("✅ 개선된 LBank 자가매매 시스템 초기화 완료")
        print(f"🎯 목표 거래량: {self.min_volume_per_5min:,} ~ {self.max_volume_per_5min:,} SPSI/5분")
        print(f"⚖️ 균형 거래: 매수/매도 {self.balance_threshold*100:.0f}% 균형 유지")
        print(f"📊 차트 기능: 실시간 모니터링 지원")
        logger.info("개선된 자가매매 시스템 초기화 완료")

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
            
            result = {
                'usdt': usdt_balance,
                'spsi': spsi_balance
            }
            
            # 🔥 차트에 잔고 데이터 추가
            self.chart.add_balance_data(usdt_balance, spsi_balance)
            
            return result
            
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
            
            # 🔥 차트에 가격 데이터 추가
            volume = float(self.response_handler.safe_get(ticker_info, 'vol', 0))
            self.chart.add_price_data(market_price, volume)
            
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

    def calculate_balanced_trade_amounts(self, current_price: float, balance: Dict[str, float]) -> Dict[str, Any]:
        """🔥 균형 잡힌 거래량 계산"""
        try:
            print(f"   ⚖️ 균형 거래량 계산:")
            print(f"      - 현재 가격: ${current_price:.6f}")
            print(f"      - USDT 잔고: ${balance['usdt']:.2f}")
            print(f"      - SPSI 잔고: {balance['spsi']:,.0f}")
            
            # 1. 미체결 주문 확인
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
                except:
                    continue
            
            available_usdt = max(0, balance['usdt'] - reserved_usdt)
            available_spsi = max(0, balance['spsi'] - reserved_spsi)
            
            print(f"      - 사용가능 USDT: ${available_usdt:.2f}")
            print(f"      - 사용가능 SPSI: {available_spsi:,.0f}")
            
            # 2. 현재 균형 상태 확인
            usdt_value = available_usdt
            spsi_value = available_spsi * current_price
            total_value = usdt_value + spsi_value
            
            if total_value < 5.0:  # 최소 $5 필요
                print(f"      ❌ 총 자산이 부족함: ${total_value:.2f} < $5.0")
                return {'can_trade': False, 'reason': '총 자산 부족'}
            
            usdt_ratio = usdt_value / total_value
            spsi_ratio = spsi_value / total_value
            
            print(f"      - USDT 비율: {usdt_ratio*100:.1f}%")
            print(f"      - SPSI 비율: {spsi_ratio*100:.1f}%")
            
            # 3. 🔥 균형 체크 및 거래 방향 결정
            balance_diff = abs(usdt_ratio - spsi_ratio)
            need_rebalance = balance_diff > (1 - self.balance_threshold)
            
            # 강제 균형 체크
            self.balance_counter += 1
            force_balance = (self.balance_counter % self.force_balance_every == 0)
            
            print(f"      - 균형 차이: {balance_diff*100:.1f}%")
            print(f"      - 재균형 필요: {need_rebalance}")
            print(f"      - 강제 균형: {force_balance} (카운터: {self.balance_counter})")
            
            # 4. 거래 전략 결정
            if need_rebalance or force_balance:
                # 불균형 해소 우선
                if usdt_ratio > spsi_ratio:
                    # USDT가 많음 → 매수 위주
                    buy_ratio = 0.7
                    sell_ratio = 0.3
                    print(f"      - 전략: 매수 위주 (USDT 과다)")
                else:
                    # SPSI가 많음 → 매도 위주
                    buy_ratio = 0.3
                    sell_ratio = 0.7
                    print(f"      - 전략: 매도 위주 (SPSI 과다)")
            else:
                # 균형 상태 → 동일 비율
                buy_ratio = 0.5
                sell_ratio = 0.5
                print(f"      - 전략: 균형 거래")
            
            # 5. 거래량 계산
            base_value = random.uniform(3.0, 8.0)  # $3-8 기본값
            
            # 매수 거래량
            max_buy_value = available_usdt * 0.8  # 안전 마진
            buy_value = min(base_value * buy_ratio, max_buy_value)
            buy_amount = buy_value / current_price if current_price > 0 else 0
            
            # 매도 거래량
            max_sell_value = available_spsi * current_price * 0.8  # 안전 마진
            sell_value = min(base_value * sell_ratio, max_sell_value)
            sell_amount = sell_value / current_price if current_price > 0 else 0
            
            # 6. 최소값 확인
            if buy_amount < 100:  # 최소 100 SPSI
                buy_amount = min(100, available_usdt / current_price * 0.5) if current_price > 0 else 0
                buy_value = buy_amount * current_price
                
            if sell_amount < 100:  # 최소 100 SPSI
                sell_amount = min(100, available_spsi * 0.5)
                sell_value = sell_amount * current_price
            
            result = {
                'buy_amount': round(buy_amount, 2),
                'sell_amount': round(sell_amount, 2),
                'buy_value': buy_value,
                'sell_value': sell_value,
                'buy_ratio': buy_ratio,
                'sell_ratio': sell_ratio,
                'balance_diff': balance_diff,
                'need_rebalance': need_rebalance,
                'force_balance': force_balance,
                'can_trade': (buy_amount > 0 or sell_amount > 0)
            }
            
            print(f"   ✅ 균형 거래 계획:")
            print(f"      - 매수: {result['buy_amount']:,.0f} SPSI (${result['buy_value']:.2f})")
            print(f"      - 매도: {result['sell_amount']:,.0f} SPSI (${result['sell_value']:.2f})")
            print(f"      - 비율: 매수 {buy_ratio*100:.0f}% / 매도 {sell_ratio*100:.0f}%")
            
            return result
            
        except Exception as e:
            print(f"   ❌ 균형 거래량 계산 오류: {e}")
            return {'can_trade': False, 'reason': f'계산 오류: {e}'}

    def execute_smart_trade(self, trade_plan: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """🔥 스마트 거래 실행 - 다양한 가격대 활용"""
        try:
            print(f"   🎯 스마트 거래 실행:")
            
            results = {
                'buy_success': False,
                'sell_success': False,
                'buy_order_id': None,
                'sell_order_id': None,
                'executed_trades': 0
            }
            
            # 1. 매수 주문 실행
            if trade_plan['buy_amount'] > 0:
                # 🔥 매수 가격 전략: 더 적극적으로 설정
                if trade_plan.get('need_rebalance', False) or trade_plan.get('force_balance', False):
                    # 재균형 필요시 → 빠른 체결
                    buy_price = round(current_price * (1 + self.tight_spread), 6)
                    print(f"      - 매수 (재균형): {trade_plan['buy_amount']:,.0f} SPSI @ ${buy_price:.6f}")
                else:
                    # 일반 상황 → 적당한 가격
                    buy_price = round(current_price * (1 + self.normal_spread), 6)
                    print(f"      - 매수 (일반): {trade_plan['buy_amount']:,.0f} SPSI @ ${buy_price:.6f}")
                
                buy_order_id = self.place_order('buy', trade_plan['buy_amount'], buy_price)
                if buy_order_id:
                    results['buy_success'] = True
                    results['buy_order_id'] = buy_order_id
                    results['executed_trades'] += 1
                    self.successful_buys += 1
                    
                    # 🔥 차트에 거래 데이터 추가
                    self.chart.add_trade_data('buy', trade_plan['buy_amount'], buy_price, True)
                    
                    print(f"      ✅ 매수 주문 성공 (ID: {buy_order_id})")
                else:
                    print(f"      ❌ 매수 주문 실패")
                    # 실패한 거래도 차트에 기록
                    self.chart.add_trade_data('buy', trade_plan['buy_amount'], buy_price, False)
            
            # 2. 매도 주문 실행
            if trade_plan['sell_amount'] > 0:
                time.sleep(1)  # 짧은 대기
                
                # 🔥 매도 가격 전략: 더 적극적으로 설정
                if trade_plan.get('need_rebalance', False) or trade_plan.get('force_balance', False):
                    # 재균형 필요시 → 빠른 체결
                    sell_price = round(current_price * (1 - self.tight_spread), 6)
                    print(f"      - 매도 (재균형): {trade_plan['sell_amount']:,.0f} SPSI @ ${sell_price:.6f}")
                else:
                    # 일반 상황 → 적당한 가격
                    sell_price = round(current_price * (1 - self.normal_spread), 6)
                    print(f"      - 매도 (일반): {trade_plan['sell_amount']:,.0f} SPSI @ ${sell_price:.6f}")
                
                sell_order_id = self.place_order('sell', trade_plan['sell_amount'], sell_price)
                if sell_order_id:
                    results['sell_success'] = True
                    results['sell_order_id'] = sell_order_id
                    results['executed_trades'] += 1
                    self.successful_sells += 1
                    
                    # 🔥 차트에 거래 데이터 추가
                    self.chart.add_trade_data('sell', trade_plan['sell_amount'], sell_price, True)
                    
                    print(f"      ✅ 매도 주문 성공 (ID: {sell_order_id})")
                else:
                    print(f"      ❌ 매도 주문 실패")
                    # 실패한 거래도 차트에 기록
                    self.chart.add_trade_data('sell', trade_plan['sell_amount'], sell_price, False)
            
            # 3. 결과 정리
            if results['executed_trades'] > 0:
                # 주문 ID 저장
                if results['buy_order_id']:
                    self.current_orders.append(results['buy_order_id'])
                if results['sell_order_id']:
                    self.current_orders.append(results['sell_order_id'])
                
                # 통계 업데이트
                total_volume = (trade_plan['buy_amount'] + trade_plan['sell_amount'])
                self.total_volume_today += total_volume
                self.total_trades_today += results['executed_trades']
                
                estimated_fee = (trade_plan['buy_value'] + trade_plan['sell_value']) * 0.001
                self.total_fees_paid += estimated_fee
                
                print(f"   📊 스마트 거래 결과:")
                print(f"      - 실행된 거래: {results['executed_trades']}/2")
                print(f"      - 총 거래량: {total_volume:,.0f} SPSI")
                print(f"      - 총 거래 가치: ${(trade_plan['buy_value'] + trade_plan['sell_value']):.2f}")
                print(f"      - 예상 수수료: ${estimated_fee:.4f}")
                print(f"      - 누적 매수 성공: {self.successful_buys}")
                print(f"      - 누적 매도 성공: {self.successful_sells}")
                
                return results
            else:
                print(f"   ❌ 모든 거래 실패")
                return results
                
        except Exception as e:
            print(f"   💥 스마트 거래 실행 오류: {e}")
            logger.error(f"스마트 거래 실행 오류: {e}")
            return results

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

    def execute_balanced_trade_cycle(self) -> bool:
        """🔥 균형 잡힌 자가매매 사이클"""
        try:
            print("   ⚖️ 균형 자가매매 사이클 시작...")
            
            # 1. 기본 정보 수집
            current_price = self.get_reference_price()
            if not current_price:
                print("   ❌ 현재 가격 조회 실패")
                return False
            
            balance = self.get_account_balance()
            if not balance:
                print("   ❌ 잔고 조회 실패")
                return False
            
            # 2. 미체결 주문 정리 (너무 많으면)
            open_orders = self.get_open_orders()
            if len(open_orders) > 10:
                print(f"   🧹 미체결 주문 {len(open_orders)}개 발견, 정리 중...")
                self.cleanup_old_orders()
                time.sleep(2)
                
                balance = self.get_account_balance()
                if not balance:
                    print("   ❌ 정리 후 잔고 확인 실패")
                    return False
            
            # 3. 균형 거래 계획 수립
            trade_plan = self.calculate_balanced_trade_amounts(current_price, balance)
            
            if not trade_plan.get('can_trade', False):
                print(f"   ❌ 거래 불가: {trade_plan.get('reason', '알 수 없음')}")
                return False
            
            # 4. 스마트 거래 실행
            results = self.execute_smart_trade(trade_plan, current_price)
            
            # 5. 결과 평가
            if results['executed_trades'] > 0:
                print(f"   ✅ 균형 거래 성공 ({results['executed_trades']}/2)")
                
                # 균형 상태 로그
                balance_status = "균형" if not trade_plan.get('need_rebalance', False) else "불균형"
                print(f"   📊 거래 후 예상 상태: {balance_status}")
                
                return True
            else:
                print(f"   ❌ 모든 거래 실패")
                return False
                
        except Exception as e:
            print(f"   💥 균형 거래 사이클 오류: {e}")
            logger.error(f"균형 거래 사이클 오류: {e}")
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
                    self.current_orders.remove(order_id)
                    time.sleep(0.2)
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
        balance = self.get_account_balance()
        current_price = self.get_reference_price()
        
        if not balance or not current_price:
            print("❌ 자가매매 시작 불가: 기본 정보 조회 실패")
            return
        
        # 최소 자산 확인
        total_value = balance['usdt'] + (balance['spsi'] * current_price)
        if total_value < 10:
            print(f"❌ 자가매매 시작 불가: 총 자산 부족 (${total_value:.2f} < $10)")
            return
        
        self.running = True
        print("🚀 개선된 균형 자가매매 시스템 시작!")
        print(f"⚖️ 특징: 매수/매도 균형 유지 + 실시간 차트")
        print(f"🎯 목표: 5분마다 {self.min_volume_per_5min:,}~{self.max_volume_per_5min:,} SPSI")
        print(f"⏰ 실행 간격: {self.trade_interval}초")
        
        def trading_loop():
            last_cleanup = time.time()
            consecutive_failures = 0
            max_failures = 3
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - 균형 자가매매 실행")
                    
                    # 균형 자가매매 실행
                    success = self.execute_balanced_trade_cycle()
                    
                    if success:
                        consecutive_failures = 0
                        
                        # 🔥 거래 통계 출력
                        stats = self.chart.get_trading_stats()
                        print(f"   📈 실시간 통계:")
                        print(f"      - 오늘 거래량: {self.total_volume_today:,.0f} SPSI")
                        print(f"      - 오늘 거래 횟수: {self.total_trades_today}회")
                        print(f"      - 매수 성공: {self.successful_buys}회")
                        print(f"      - 매도 성공: {self.successful_sells}회")
                        print(f"      - 매수/매도 균형: {abs(self.successful_buys - self.successful_sells)}")
                        print(f"      - 누적 수수료: ${self.total_fees_paid:.4f}")
                        
                        # 균형 상태 확인
                        if self.successful_buys > 0 and self.successful_sells > 0:
                            balance_ratio = min(self.successful_buys, self.successful_sells) / max(self.successful_buys, self.successful_sells)
                            print(f"      - 균형 비율: {balance_ratio*100:.1f}%")
                        
                    else:
                        consecutive_failures += 1
                        print(f"   ⚠️ 거래 실패 ({consecutive_failures}/{max_failures})")
                        
                        if consecutive_failures >= max_failures:
                            print(f"   🛑 연속 {max_failures}회 실패로 일시 정지")
                            print(f"   ⏳ 5분 후 재시도...")
                            time.sleep(300)
                            consecutive_failures = 0
                    
                    # 정기 정리
                    if current_time - last_cleanup > 600:  # 10분마다
                        print(f"\n🧹 정기 주문 정리...")
                        self.cleanup_old_orders()
                        last_cleanup = current_time
                    
                    # 대기
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
                        time.sleep(10)
        
        self.trading_thread = threading.Thread(target=trading_loop, daemon=True)
        self.trading_thread.start()

    def stop_self_trading(self):
        """자가매매 중지"""
        if not self.running:
            print("⚠️ 자가매매가 실행되고 있지 않습니다")
            return
        
        self.running = False
        print("⏹️ 균형 자가매매 중지 요청됨...")
        
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
            print(f"📊 개선된 균형 자가매매 시스템 상태")
            print(f"{'='*60}")
            print(f"💰 현재 가격: ${current_price:.6f}" if current_price else "💰 현재 가격: 조회 실패")
            
            if balance:
                print(f"💳 USDT 잔고: ${balance['usdt']:.2f}")
                print(f"🪙 SPSI 잔고: {balance['spsi']:,.2f}")
                
                # 균형 상태 분석
                if current_price:
                    usdt_value = balance['usdt']
                    spsi_value = balance['spsi'] * current_price
                    total_value = usdt_value + spsi_value
                    
                    if total_value > 0:
                        usdt_ratio = usdt_value / total_value
                        spsi_ratio = spsi_value / total_value
                        balance_score = min(usdt_ratio, spsi_ratio) / max(usdt_ratio, spsi_ratio)
                        
                        print(f"⚖️ 자산 균형:")
                        print(f"   - USDT: ${usdt_value:.2f} ({usdt_ratio*100:.1f}%)")
                        print(f"   - SPSI: ${spsi_value:.2f} ({spsi_ratio*100:.1f}%)")
                        print(f"   - 균형 점수: {balance_score*100:.1f}%")
                        
                        if balance_score > 0.8:
                            print(f"   - 상태: ✅ 균형 양호")
                        elif balance_score > 0.6:
                            print(f"   - 상태: ⚠️ 약간 불균형")
                        else:
                            print(f"   - 상태: ❌ 심각한 불균형")
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"🔄 실행 상태: {'🟢 활성' if self.running else '🔴 중지'}")
            
            # 🔥 거래 통계
            stats = self.chart.get_trading_stats()
            print(f"📊 거래 통계:")
            print(f"   - 오늘 총 거래량: {self.total_volume_today:,.0f} SPSI")
            print(f"   - 오늘 총 거래 횟수: {self.total_trades_today}회")
            print(f"   - 매수 성공: {self.successful_buys}회")
            print(f"   - 매도 성공: {self.successful_sells}회")
            print(f"   - 매수/매도 차이: {abs(self.successful_buys - self.successful_sells)}")
            print(f"   - 누적 수수료: ${self.total_fees_paid:.4f}")
            print(f"   - 대기 주문: {len(self.current_orders)}개")
            
            if self.successful_buys > 0 or self.successful_sells > 0:
                print(f"   - 매수 성공률: {stats['buy_success_rate']:.1f}%")
                print(f"   - 매도 성공률: {stats['sell_success_rate']:.1f}%")
                
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    def show_trading_chart(self):
        """거래 차트 표시"""
        try:
            print("📊 거래 차트 생성 중...")
            
            # 차트 생성
            chart_filename = f"trading_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.chart.plot_price_chart(chart_filename)
            
            # 통계 출력
            stats = self.chart.get_trading_stats()
            print(f"\n📈 거래 통계:")
            print(f"   - 총 거래 시도: {stats['total_trades']}회")
            print(f"   - 매수 성공: {stats['total_buys']}회")
            print(f"   - 매도 성공: {stats['total_sells']}회")
            print(f"   - 매수 거래량: {stats['buy_volume']:,.0f} SPSI")
            print(f"   - 매도 거래량: {stats['sell_volume']:,.0f} SPSI")
            print(f"   - 거래량 차이: {stats['volume_balance']:,.0f} SPSI")
            print(f"   - 매수 성공률: {stats['buy_success_rate']:.1f}%")
            print(f"   - 매도 성공률: {stats['sell_success_rate']:.1f}%")
            
            # 최근 거래 내역
            if stats['recent_trades']:
                print(f"\n🔍 최근 거래 내역:")
                for i, trade in enumerate(stats['recent_trades'][-5:], 1):
                    status = "✅" if trade['success'] else "❌"
                    print(f"   {i}. {status} {trade['type'].upper()} {trade['amount']:,.0f} SPSI @ ${trade['price']:.6f}")
            
        except Exception as e:
            print(f"❌ 차트 생성 오류: {e}")
            logger.error(f"차트 생성 오류: {e}")

    def test_single_balanced_trade(self):
        """1회 균형 거래 테스트"""
        print("🧪 1회 균형 거래 테스트 실행...")
        
        # 거래 전 상태
        before_balance = self.get_account_balance()
        current_price = self.get_reference_price()
        
        if before_balance and current_price:
            print(f"\n📊 거래 전 상태:")
            print(f"   - USDT: ${before_balance['usdt']:.2f}")
            print(f"   - SPSI: {before_balance['spsi']:,.0f}")
            print(f"   - 현재 가격: ${current_price:.6f}")
            
            # 균형 상태 분석
            usdt_value = before_balance['usdt']
            spsi_value = before_balance['spsi'] * current_price
            total_value = usdt_value + spsi_value
            
            if total_value > 0:
                usdt_ratio = usdt_value / total_value
                spsi_ratio = spsi_value / total_value
                print(f"   - 자산 균형: USDT {usdt_ratio*100:.1f}% / SPSI {spsi_ratio*100:.1f}%")
        
        # 테스트 실행
        result = self.execute_balanced_trade_cycle()
        
        if result:
            print("\n✅ 균형 거래 테스트 성공!")
            print("💡 실제 주문이 배치되었습니다.")
            
            # 결과 확인
            time.sleep(5)
            after_balance = self.get_account_balance()
            
            if after_balance and before_balance:
                print(f"\n📊 거래 후 상태:")
                print(f"   - USDT: ${after_balance['usdt']:.2f}")
                print(f"   - SPSI: {after_balance['spsi']:,.0f}")
                
                usdt_diff = after_balance['usdt'] - before_balance['usdt']
                spsi_diff = after_balance['spsi'] - before_balance['spsi']
                print(f"\n📈 잔고 변화:")
                print(f"   - USDT: {usdt_diff:+.2f}")
                print(f"   - SPSI: {spsi_diff:+,.0f}")
                
                # 새로운 균형 상태
                if current_price:
                    usdt_value = after_balance['usdt']
                    spsi_value = after_balance['spsi'] * current_price
                    total_value = usdt_value + spsi_value
                    
                    if total_value > 0:
                        usdt_ratio = usdt_value / total_value
                        spsi_ratio = spsi_value / total_value
                        balance_score = min(usdt_ratio, spsi_ratio) / max(usdt_ratio, spsi_ratio)
                        print(f"   - 새로운 균형: USDT {usdt_ratio*100:.1f}% / SPSI {spsi_ratio*100:.1f}%")
                        print(f"   - 균형 점수: {balance_score*100:.1f}%")
            
            print("\n🧹 테스트 주문 정리를 원하시면 메뉴 6번을 실행하세요.")
            return True
        else:
            print("\n❌ 균형 거래 테스트 실패!")
            return False

def main():
    print("🏭 개선된 LBank 균형 자가매매 시스템")
    print("⚖️ 특징: 매수/매도 균형 유지 + 실시간 차트")
    print("🎯 목표: 안정적인 거래량 생성 + 자산 균형 관리")
    
    # matplotlib 설정
    try:
        import matplotlib
        matplotlib.use('Agg')  # GUI 없이 차트 생성
        print("📊 차트 기능 활성화됨")
    except ImportError:
        print("⚠️ matplotlib가 설치되지 않았습니다. 차트 기능 비활성화")
    
    # API 키 설정
    API_KEY = os.getenv('LBANK_API_KEY', '73658848-ac66-435f-a43d-eca72f98ecbf')
    API_SECRET = os.getenv('LBANK_API_SECRET', '18F00DC6DCD01F2E19452ED52F716D3D')
    
    if not API_KEY or not API_SECRET:
        print("❌ API 키가 설정되지 않았습니다")
        input("Enter를 눌러 종료...")
        return
    
    try:
        print("📡 균형 자가매매 시스템 초기화 중...")
        st = ImprovedLBankSelfTrader(API_KEY, API_SECRET)
        
        while True:
            try:
                print("\n" + "="*60)
                print("🏭 개선된 LBank 균형 자가매매 시스템")
                print("="*60)
                print("⚖️ 매수/매도 균형 유지 + 실시간 모니터링")
                print("🎯 목표: 안정적인 거래량 생성 + 자산 균형 관리")
                print("📊 차트: 실시간 가격/잔고/거래 현황 시각화")
                print("="*60)
                print("1. 💰 상태 확인 (잔고 + 균형 + 통계)")
                print("2. 🧪 시스템 테스트 (API + 거래 준비도)")
                print("3. 🔄 균형 거래 1회 테스트")
                print("4. 🚀 균형 자가매매 시작")
                print("5. ⏹️ 자가매매 중지")
                print("6. 🧹 주문 정리 (미체결 주문 취소)")
                print("7. 📊 거래 차트 보기")
                print("8. 🔍 거래 통계 상세 보기")
                print("0. 🚪 종료")
                
                choice = input("\n선택하세요 (0-8): ").strip()
                
                if choice == '1':
                    st.get_status()
                    
                elif choice == '2':
                    print("\n🧪 시스템 테스트 중...")
                    
                    # 기본 테스트
                    balance = st.get_account_balance()
                    price = st.get_reference_price()
                    
                    if balance and price:
                        print("✅ API 연결 성공")
                        print(f"✅ 잔고 조회 성공: USDT ${balance['usdt']:.2f}, SPSI {balance['spsi']:,.0f}")
                        print(f"✅ 가격 조회 성공: ${price:.6f}")
                        
                        # 거래 계획 테스트
                        trade_plan = st.calculate_balanced_trade_amounts(price, balance)
                        if trade_plan.get('can_trade', False):
                            print("✅ 거래 계획 생성 성공")
                            print(f"   - 매수 계획: {trade_plan['buy_amount']:,.0f} SPSI")
                            print(f"   - 매도 계획: {trade_plan['sell_amount']:,.0f} SPSI")
                            print(f"   - 균형 상태: {'재균형 필요' if trade_plan.get('need_rebalance') else '균형 양호'}")
                        else:
                            print("❌ 거래 계획 생성 실패")
                            print(f"   - 원인: {trade_plan.get('reason', '알 수 없음')}")
                    else:
                        print("❌ 기본 정보 조회 실패")
                    
                elif choice == '3':
                    print("\n⚠️ 실제 거래가 실행됩니다!")
                    print("📊 균형 거래 테스트:")
                    print("   - 매수/매도 균형을 고려한 거래 실행")
                    print("   - 자산 균형 상태에 따라 거래 비율 조정")
                    print("   - 실시간 차트 데이터 수집")
                    
                    confirm = input("정말 테스트 하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.test_single_balanced_trade()
                    else:
                        print("테스트 취소됨")
                    
                elif choice == '4':
                    print("\n⚠️ 균형 자가매매 시작 주의사항:")
                    print("- 매수/매도 균형을 자동으로 유지합니다")
                    print("- 자산 불균형 시 자동으로 재균형 거래를 실행합니다")
                    print("- 실시간 차트 데이터를 수집합니다")
                    print("- 안전한 거래량으로 연속 거래를 실행합니다")
                    print("- 언제든지 중지할 수 있습니다")
                    
                    confirm = input("\n정말 시작하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.start_self_trading()
                        if st.running:
                            print("✅ 균형 자가매매 시스템이 시작되었습니다!")
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
                    print("📊 거래 차트 생성 중...")
                    st.show_trading_chart()
                    
                elif choice == '8':
                    print("🔍 거래 통계 상세 보기...")
                    stats = st.chart.get_trading_stats()
                    
                    print(f"\n📈 상세 거래 통계:")
                    print(f"   - 총 거래 시도: {stats['total_trades']}회")
                    print(f"   - 매수 성공: {stats['total_buys']}회")
                    print(f"   - 매도 성공: {stats['total_sells']}회")
                    print(f"   - 매수 거래량: {stats['buy_volume']:,.0f} SPSI")
                    print(f"   - 매도 거래량: {stats['sell_volume']:,.0f} SPSI")
                    print(f"   - 거래량 차이: {stats['volume_balance']:,.0f} SPSI")
                    print(f"   - 매수 성공률: {stats['buy_success_rate']:.1f}%")
                    print(f"   - 매도 성공률: {stats['sell_success_rate']:.1f}%")
                    
                    # 균형 점수 계산
                    if stats['buy_volume'] > 0 and stats['sell_volume'] > 0:
                        balance_score = min(stats['buy_volume'], stats['sell_volume']) / max(stats['buy_volume'], stats['sell_volume'])
                        print(f"   - 거래량 균형 점수: {balance_score*100:.1f}%")
                    
                    if stats['total_buys'] > 0 and stats['total_sells'] > 0:
                        count_balance = min(stats['total_buys'], stats['total_sells']) / max(stats['total_buys'], stats['total_sells'])
                        print(f"   - 거래 횟수 균형 점수: {count_balance*100:.1f}%")
                    
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
