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
        self.trade_history = deque(maxlen=200)
        self.buy_orders = deque(maxlen=200)
        self.sell_orders = deque(maxlen=200)
        
        # 실시간 통계
        self.total_buys = 0
        self.total_sells = 0
        self.total_buy_volume = 0
        self.total_sell_volume = 0
        
        # 🔥 거래 패턴 추적
        self.recent_trade_sizes = deque(maxlen=50)
        self.recent_price_impacts = deque(maxlen=50)
        
    def add_price_data(self, price: float, volume: float = 0):
        """가격 데이터 추가"""
        timestamp = datetime.now()
        self.price_history.append({
            'time': timestamp,
            'price': price,
            'volume': volume
        })
        
        # 🔥 가격 변동성 계산
        if len(self.price_history) > 1:
            prev_price = self.price_history[-2]['price']
            price_change = abs(price - prev_price) / prev_price
            self.recent_price_impacts.append(price_change)
        
    def add_balance_data(self, usdt: float, spsi: float):
        """잔고 데이터 추가"""
        timestamp = datetime.now()
        self.balance_history.append({
            'time': timestamp,
            'usdt': usdt,
            'spsi': spsi
        })
        
    def add_trade_data(self, trade_type: str, amount: float, price: float, success: bool, trade_size_type: str = "normal"):
        """거래 데이터 추가"""
        timestamp = datetime.now()
        trade_data = {
            'time': timestamp,
            'type': trade_type,
            'amount': amount,
            'price': price,
            'value': amount * price,
            'success': success,
            'size_type': trade_size_type  # 🔥 거래 크기 타입 추가
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
                
            # 🔥 거래 크기 추적
            self.recent_trade_sizes.append({
                'amount': amount,
                'value': amount * price,
                'type': trade_type,
                'size_type': trade_size_type
            })
    
    def plot_enhanced_chart(self, save_path: str = None):
        """🔥 향상된 차트 생성"""
        if len(self.price_history) < 2:
            print("⚠️ 가격 데이터 부족 (최소 2개 필요)")
            return
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 가격 차트 + 거래 포인트
        times = [d['time'] for d in self.price_history]
        prices = [d['price'] for d in self.price_history]
        
        ax1.plot(times, prices, 'b-', linewidth=2, label='SPSI 가격')
        ax1.set_title('SPSI/USDT 가격 변화 + 거래 포인트', fontsize=12)
        ax1.set_ylabel('가격 (USDT)', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 🔥 거래 크기별 색상 표시
        size_colors = {'micro': 'lightgreen', 'small': 'green', 'medium': 'blue', 'large': 'orange', 'huge': 'red'}
        
        # 매수 포인트 (크기별 색상)
        if self.buy_orders:
            for trade in self.buy_orders:
                color = size_colors.get(trade.get('size_type', 'medium'), 'green')
                size = 30 if trade.get('size_type') == 'micro' else 50 if trade.get('size_type') == 'small' else 70 if trade.get('size_type') == 'medium' else 90 if trade.get('size_type') == 'large' else 120
                ax1.scatter(trade['time'], trade['price'], color=color, s=size, alpha=0.7, marker='^')
                
        # 매도 포인트 (크기별 색상)
        if self.sell_orders:
            for trade in self.sell_orders:
                color = size_colors.get(trade.get('size_type', 'medium'), 'red')
                size = 30 if trade.get('size_type') == 'micro' else 50 if trade.get('size_type') == 'small' else 70 if trade.get('size_type') == 'medium' else 90 if trade.get('size_type') == 'large' else 120
                ax1.scatter(trade['time'], trade['price'], color=color, s=size, alpha=0.7, marker='v')
        
        # 2. 잔고 차트
        if self.balance_history:
            balance_times = [d['time'] for d in self.balance_history]
            usdt_balances = [d['usdt'] for d in self.balance_history]
            spsi_balances = [d['spsi'] for d in self.balance_history]
            
            ax2_twin = ax2.twinx()
            
            ax2.plot(balance_times, usdt_balances, 'g-', linewidth=2, label='USDT 잔고')
            ax2_twin.plot(balance_times, spsi_balances, 'r-', linewidth=2, label='SPSI 잔고')
            
            ax2.set_title('잔고 변화', fontsize=12)
            ax2.set_ylabel('USDT', fontsize=10, color='g')
            ax2_twin.set_ylabel('SPSI', fontsize=10, color='r')
            ax2.grid(True, alpha=0.3)
        
        # 3. 🔥 거래 크기 분포
        if self.recent_trade_sizes:
            trade_values = [t['value'] for t in self.recent_trade_sizes]
            trade_types = [t['size_type'] for t in self.recent_trade_sizes]
            
            size_counts = {}
            for size_type in trade_types:
                size_counts[size_type] = size_counts.get(size_type, 0) + 1
            
            colors = ['lightblue', 'lightgreen', 'blue', 'orange', 'red']
            ax3.pie(size_counts.values(), labels=size_counts.keys(), colors=colors[:len(size_counts)], autopct='%1.1f%%')
            ax3.set_title('거래 크기 분포', fontsize=12)
        
        # 4. 🔥 가격 변동성
        if self.recent_price_impacts:
            impact_times = list(range(len(self.recent_price_impacts)))
            ax4.plot(impact_times, [i*100 for i in self.recent_price_impacts], 'purple', linewidth=2)
            ax4.set_title('가격 변동성 (%)', fontsize=12)
            ax4.set_ylabel('변동률 (%)', fontsize=10)
            ax4.grid(True, alpha=0.3)
            
            # 평균 변동성 표시
            if self.recent_price_impacts:
                avg_impact = np.mean(self.recent_price_impacts) * 100
                ax4.axhline(y=avg_impact, color='red', linestyle='--', alpha=0.7, label=f'평균: {avg_impact:.3f}%')
                ax4.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 향상된 차트 저장됨: {save_path}")
        
        plt.show()
        
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """🔥 향상된 거래 통계"""
        stats = {
            'total_trades': len(self.trade_history),
            'total_buys': self.total_buys,
            'total_sells': self.total_sells,
            'buy_volume': self.total_buy_volume,
            'sell_volume': self.total_sell_volume,
            'recent_trades': list(self.trade_history)[-10:] if self.trade_history else []
        }
        
        # 🔥 거래 크기 분석
        if self.recent_trade_sizes:
            size_analysis = {}
            for trade in self.recent_trade_sizes:
                size_type = trade['size_type']
                if size_type not in size_analysis:
                    size_analysis[size_type] = {'count': 0, 'total_value': 0}
                size_analysis[size_type]['count'] += 1
                size_analysis[size_type]['total_value'] += trade['value']
            
            stats['size_analysis'] = size_analysis
        
        # 🔥 가격 변동성 분석
        if self.recent_price_impacts:
            stats['price_volatility'] = {
                'avg_impact': np.mean(self.recent_price_impacts) * 100,
                'max_impact': max(self.recent_price_impacts) * 100,
                'min_impact': min(self.recent_price_impacts) * 100,
                'volatility_score': np.std(self.recent_price_impacts) * 100
            }
        
        return stats

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

class RandomizedLBankTrader:
    """🔥 랜덤화된 LBank 자가매매 시스템 - 다양한 거래 패턴 + 가격 변동성"""
    
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.trading_thread = None
        
        # 거래 설정
        self.symbol = "spsi_usdt"
        
        # 🔥 랜덤 거래량 설정
        self.min_volume_per_5min = 20000
        self.max_volume_per_5min = 50000
        self.trade_interval_base = 60  # 기본 60초
        
        # 🔥 다양한 거래 크기 설정
        self.trade_sizes = {
            'micro': {'min': 50, 'max': 200, 'probability': 0.3},      # 30% - 미세 거래
            'small': {'min': 200, 'max': 800, 'probability': 0.3},     # 30% - 소량 거래
            'medium': {'min': 800, 'max': 2000, 'probability': 0.25},  # 25% - 중간 거래
            'large': {'min': 2000, 'max': 5000, 'probability': 0.1},   # 10% - 대량 거래
            'huge': {'min': 5000, 'max': 10000, 'probability': 0.05}   # 5% - 거대 거래
        }
        
        # 🔥 가격 변동성 증가를 위한 설정
        self.price_strategies = {
            'conservative': {'spread': 0.0005, 'probability': 0.4},    # 40% - 보수적
            'normal': {'spread': 0.001, 'probability': 0.35},          # 35% - 일반적
            'aggressive': {'spread': 0.002, 'probability': 0.15},      # 15% - 공격적
            'market': {'spread': 0.00001, 'probability': 0.1}          # 10% - 시장가 근처
        }
        
        # 🔥 특수 거래 패턴
        self.special_patterns = {
            'trend_up': {'consecutive_buys': 3, 'probability': 0.1},    # 상승 트렌드
            'trend_down': {'consecutive_sells': 3, 'probability': 0.1}, # 하락 트렌드
            'shock': {'huge_trade': True, 'probability': 0.05},         # 시장 충격
            'accumulation': {'micro_trades': 5, 'probability': 0.05}    # 물량 축적
        }
        
        # 균형 관리 설정
        self.balance_threshold = 0.7  # 70% 균형 (더 느슨하게)
        self.force_balance_every = 8   # 8회마다 강제 균형
        self.balance_counter = 0
        
        # 패턴 상태
        self.current_pattern = None
        self.pattern_counter = 0
        self.last_trade_time = 0
        
        # 기본 설정
        self.min_order_size = 50  # 최소 주문 크기 축소
        self.min_trade_value_usd = 0.5
        self.max_trade_value_usd = 50.0  # 최대 거래 가치 증가
        
        self.base_price = None
        self.current_orders = []
        
        # 통계
        self.total_volume_today = 0
        self.total_trades_today = 0
        self.total_fees_paid = 0.0
        self.successful_buys = 0
        self.successful_sells = 0
        
        # 🔥 패턴별 통계
        self.pattern_stats = {
            'micro': 0, 'small': 0, 'medium': 0, 'large': 0, 'huge': 0,
            'conservative': 0, 'normal': 0, 'aggressive': 0, 'market': 0
        }
        
        # 차트 시스템
        self.chart = TradingChart()
        self.response_handler = SafeAPIResponseHandler()
        
        print("🎯 랜덤화된 LBank 자가매매 시스템 초기화 완료")
        print(f"🎲 특징: 다양한 거래 크기 + 랜덤 패턴 + 가격 변동성")
        print(f"📊 거래 크기:")
        for size, config in self.trade_sizes.items():
            print(f"   - {size}: {config['min']}-{config['max']} SPSI ({config['probability']*100:.0f}%)")
        print(f"💫 특수 패턴: 트렌드 생성, 시장 충격, 물량 축적")
        logger.info("랜덤화된 자가매매 시스템 초기화 완료")

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
            
            # 차트에 잔고 데이터 추가
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
            
            # 차트에 가격 데이터 추가
            volume = float(self.response_handler.safe_get(ticker_info, 'vol', 0))
            self.chart.add_price_data(market_price, volume)
            
            if self.base_price is None:
                self.base_price = market_price
                logger.info(f"기준 가격 설정: ${self.base_price:.6f}")
                return self.base_price
            
            price_diff = abs(market_price - self.base_price) / self.base_price
            if price_diff > 0.005:  # 0.5% 이상 변동시 업데이트
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

    def select_random_trade_size(self) -> str:
        """🎲 랜덤 거래 크기 선택"""
        rand = random.random()
        cumulative = 0
        
        for size_type, config in self.trade_sizes.items():
            cumulative += config['probability']
            if rand <= cumulative:
                return size_type
        
        return 'medium'  # 기본값

    def select_random_price_strategy(self) -> str:
        """🎲 랜덤 가격 전략 선택"""
        rand = random.random()
        cumulative = 0
        
        for strategy, config in self.price_strategies.items():
            cumulative += config['probability']
            if rand <= cumulative:
                return strategy
        
        return 'normal'  # 기본값

    def check_special_pattern(self) -> Optional[str]:
        """🎭 특수 패턴 확인"""
        if self.current_pattern:
            # 현재 패턴 지속 중
            return self.current_pattern
        
        # 새로운 패턴 확인
        for pattern, config in self.special_patterns.items():
            if random.random() < config['probability']:
                self.current_pattern = pattern
                self.pattern_counter = 0
                print(f"   🎭 특수 패턴 시작: {pattern}")
                return pattern
        
        return None

    def generate_random_trade_amount(self, size_type: str, current_price: float, balance: Dict[str, float]) -> Dict[str, float]:
        """🎲 랜덤 거래량 생성"""
        try:
            # 1. 기본 거래량 범위
            size_config = self.trade_sizes[size_type]
            min_amount = size_config['min']
            max_amount = size_config['max']
            
            # 2. 랜덤 거래량 선택
            base_amount = random.uniform(min_amount, max_amount)
            
            # 3. 특수 패턴 적용
            pattern = self.check_special_pattern()
            if pattern == 'shock':
                # 시장 충격 - 거래량 2-3배 증가
                base_amount *= random.uniform(2.0, 3.0)
                print(f"   💥 시장 충격 패턴: 거래량 {base_amount:,.0f} SPSI")
            elif pattern == 'accumulation':
                # 물량 축적 - 거래량 절반으로 축소
                base_amount *= random.uniform(0.3, 0.5)
                print(f"   📦 물량 축적 패턴: 거래량 {base_amount:,.0f} SPSI")
            
            # 4. 잔고 제한 적용
            available_usdt = balance['usdt'] * 0.8
            available_spsi = balance['spsi'] * 0.8
            
            max_buy_amount = available_usdt / current_price if current_price > 0 else 0
            max_sell_amount = available_spsi
            
            # 5. 균형 고려
            usdt_value = balance['usdt']
            spsi_value = balance['spsi'] * current_price
            total_value = usdt_value + spsi_value
            
            if total_value > 0:
                usdt_ratio = usdt_value / total_value
                spsi_ratio = spsi_value / total_value
                
                # 6. 🔥 불균형 해소를 위한 거래량 조정
                balance_diff = abs(usdt_ratio - spsi_ratio)
                need_rebalance = balance_diff > (1 - self.balance_threshold)
                
                if need_rebalance:
                    if usdt_ratio > spsi_ratio:
                        # USDT 과다 → 매수 증가
                        buy_amount = min(base_amount * 1.5, max_buy_amount)
                        sell_amount = min(base_amount * 0.5, max_sell_amount)
                    else:
                        # SPSI 과다 → 매도 증가
                        buy_amount = min(base_amount * 0.5, max_buy_amount)
                        sell_amount = min(base_amount * 1.5, max_sell_amount)
                else:
                    # 균형 상태 → 랜덤 비율
                    buy_ratio = random.uniform(0.3, 0.7)
                    sell_ratio = 1 - buy_ratio
                    
                    buy_amount = min(base_amount * buy_ratio, max_buy_amount)
                    sell_amount = min(base_amount * sell_ratio, max_sell_amount)
            else:
                buy_amount = min(base_amount * 0.5, max_buy_amount)
                sell_amount = min(base_amount * 0.5, max_sell_amount)
            
            # 7. 최소값 보장
            if buy_amount < self.min_order_size:
                buy_amount = min(self.min_order_size, max_buy_amount)
            if sell_amount < self.min_order_size:
                sell_amount = min(self.min_order_size, max_sell_amount)
            
            return {
                'buy_amount': round(buy_amount, 2),
                'sell_amount': round(sell_amount, 2),
                'size_type': size_type,
                'pattern': pattern,
                'need_rebalance': need_rebalance if total_value > 0 else False
            }
            
        except Exception as e:
            print(f"   ❌ 랜덤 거래량 생성 오류: {e}")
            return {
                'buy_amount': 100,
                'sell_amount': 100,
                'size_type': 'small',
                'pattern': None,
                'need_rebalance': False
            }

    def execute_random_trade(self, current_price: float, balance: Dict[str, float]) -> Dict[str, Any]:
        """🎯 랜덤 거래 실행"""
        try:
            print(f"   🎲 랜덤 거래 실행:")
            
            # 1. 랜덤 거래 크기 선택
            size_type = self.select_random_trade_size()
            print(f"      - 거래 크기: {size_type}")
            
            # 2. 랜덤 가격 전략 선택
            price_strategy = self.select_random_price_strategy()
            spread = self.price_strategies[price_strategy]['spread']
            print(f"      - 가격 전략: {price_strategy} (스프레드: {spread*100:.2f}%)")
            
            # 3. 거래량 생성
            trade_amounts = self.generate_random_trade_amount(size_type, current_price, balance)
            
            # 4. 통계 업데이트
            self.pattern_stats[size_type] += 1
            self.pattern_stats[price_strategy] += 1
            
            results = {
                'buy_success': False,
                'sell_success': False,
                'buy_order_id': None,
                'sell_order_id': None,
                'executed_trades': 0,
                'size_type': size_type,
                'price_strategy': price_strategy,
                'pattern': trade_amounts.get('pattern')
            }
            
            # 5. 특수 패턴 처리
            pattern = trade_amounts.get('pattern')
            if pattern == 'trend_up':
                # 상승 트렌드 - 매수만 실행
                if trade_amounts['buy_amount'] > 0:
                    buy_price = round(current_price * (1 + spread * 0.5), 6)  # 더 적극적
                    print(f"      - 트렌드 매수: {trade_amounts['buy_amount']:,.0f} SPSI @ ${buy_price:.6f}")
                    
                    buy_order_id = self.place_order('buy', trade_amounts['buy_amount'], buy_price)
                    if buy_order_id:
                        results['buy_success'] = True
                        results['buy_order_id'] = buy_order_id
                        results['executed_trades'] += 1
                        self.successful_buys += 1
                        self.chart.add_trade_data('buy', trade_amounts['buy_amount'], buy_price, True, size_type)
                        print(f"      ✅ 트렌드 매수 성공")
                        
                        # 패턴 카운터 증가
                        self.pattern_counter += 1
                        if self.pattern_counter >= 3:
                            self.current_pattern = None
                            print(f"      🎭 상승 트렌드 패턴 완료")
                
            elif pattern == 'trend_down':
                # 하락 트렌드 - 매도만 실행
                if trade_amounts['sell_amount'] > 0:
                    sell_price = round(current_price * (1 - spread * 0.5), 6)  # 더 적극적
                    print(f"      - 트렌드 매도: {trade_amounts['sell_amount']:,.0f} SPSI @ ${sell_price:.6f}")
                    
                    sell_order_id = self.place_order('sell', trade_amounts['sell_amount'], sell_price)
                    if sell_order_id:
                        results['sell_success'] = True
                        results['sell_order_id'] = sell_order_id
                        results['executed_trades'] += 1
                        self.successful_sells += 1
                        self.chart.add_trade_data('sell', trade_amounts['sell_amount'], sell_price, True, size_type)
                        print(f"      ✅ 트렌드 매도 성공")
                        
                        # 패턴 카운터 증가
                        self.pattern_counter += 1
                        if self.pattern_counter >= 3:
                            self.current_pattern = None
                            print(f"      🎭 하락 트렌드 패턴 완료")
                            
            else:
                # 일반 거래 - 매수/매도 동시
                
                # 매수 거래
                if trade_amounts['buy_amount'] > 0:
                    if price_strategy == 'market':
                        buy_price = round(current_price * (1 + spread), 6)
                    else:
                        buy_price = round(current_price * (1 + spread * random.uniform(0.5, 1.5)), 6)
                    
                    print(f"      - 매수: {trade_amounts['buy_amount']:,.0f} SPSI @ ${buy_price:.6f}")
                    
                    buy_order_id = self.place_order('buy', trade_amounts['buy_amount'], buy_price)
                    if buy_order_id:
                        results['buy_success'] = True
                        results['buy_order_id'] = buy_order_id
                        results['executed_trades'] += 1
                        self.successful_buys += 1
                        self.chart.add_trade_data('buy', trade_amounts['buy_amount'], buy_price, True, size_type)
                        print(f"      ✅ 매수 성공")
                    else:
                        self.chart.add_trade_data('buy', trade_amounts['buy_amount'], buy_price, False, size_type)
                        print(f"      ❌ 매수 실패")
                
                # 매도 거래
                if trade_amounts['sell_amount'] > 0:
                    time.sleep(random.uniform(0.5, 2.0))  # 랜덤 대기
                    
                    if price_strategy == 'market':
                        sell_price = round(current_price * (1 - spread), 6)
                    else:
                        sell_price = round(current_price * (1 - spread * random.uniform(0.5, 1.5)), 6)
                    
                    print(f"      - 매도: {trade_amounts['sell_amount']:,.0f} SPSI @ ${sell_price:.6f}")
                    
                    sell_order_id = self.place_order('sell', trade_amounts['sell_amount'], sell_price)
                    if sell_order_id:
                        results['sell_success'] = True
                        results['sell_order_id'] = sell_order_id
                        results['executed_trades'] += 1
                        self.successful_sells += 1
                        self.chart.add_trade_data('sell', trade_amounts['sell_amount'], sell_price, True, size_type)
                        print(f"      ✅ 매도 성공")
                    else:
                        self.chart.add_trade_data('sell', trade_amounts['sell_amount'], sell_price, False, size_type)
                        print(f"      ❌ 매도 실패")
            
            # 6. 결과 정리
            if results['executed_trades'] > 0:
                # 주문 ID 저장
                if results['buy_order_id']:
                    self.current_orders.append(results['buy_order_id'])
                if results['sell_order_id']:
                    self.current_orders.append(results['sell_order_id'])
                
                # 통계 업데이트
                total_volume = (trade_amounts['buy_amount'] + trade_amounts['sell_amount'])
                self.total_volume_today += total_volume
                self.total_trades_today += results['executed_trades']
                
                estimated_fee = total_volume * current_price * 0.001
                self.total_fees_paid += estimated_fee
                
                print(f"   📊 랜덤 거래 결과:")
                print(f"      - 실행된 거래: {results['executed_trades']}")
                print(f"      - 거래 크기: {size_type}")
                print(f"      - 가격 전략: {price_strategy}")
                print(f"      - 총 거래량: {total_volume:,.0f} SPSI")
                print(f"      - 예상 수수료: ${estimated_fee:.4f}")
                if pattern:
                    print(f"      - 특수 패턴: {pattern}")
                
                return results
            else:
                print(f"   ❌ 모든 거래 실패")
                return results
                
        except Exception as e:
            print(f"   💥 랜덤 거래 실행 오류: {e}")
            logger.error(f"랜덤 거래 실행 오류: {e}")
            return {'executed_trades': 0, 'size_type': 'error', 'price_strategy': 'error'}

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

    def get_random_interval(self) -> int:
        """🎲 랜덤 거래 간격 생성"""
        # 기본 간격에 랜덤 요소 추가
        base = self.trade_interval_base
        
        # 현재 패턴에 따라 간격 조정
        if self.current_pattern == 'accumulation':
            # 물량 축적 - 더 자주 거래
            return random.randint(base // 2, base)
        elif self.current_pattern in ['trend_up', 'trend_down']:
            # 트렌드 - 빠른 연속 거래
            return random.randint(base // 3, base // 2)
        else:
            # 일반 상황 - 넓은 범위 랜덤
            return random.randint(base // 2, base * 2)

    def execute_randomized_trade_cycle(self) -> bool:
        """🎯 랜덤화된 자가매매 사이클"""
        try:
            print("   🎲 랜덤화된 자가매매 사이클 시작...")
            
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
            if len(open_orders) > 12:
                print(f"   🧹 미체결 주문 {len(open_orders)}개 발견, 정리 중...")
                self.cleanup_old_orders()
                time.sleep(2)
                
                balance = self.get_account_balance()
                if not balance:
                    print("   ❌ 정리 후 잔고 확인 실패")
                    return False
            
            # 3. 최소 자산 확인
            total_value = balance['usdt'] + (balance['spsi'] * current_price)
            if total_value < 5.0:
                print(f"   ❌ 총 자산 부족: ${total_value:.2f} < $5.0")
                return False
            
            # 4. 랜덤 거래 실행
            results = self.execute_random_trade(current_price, balance)
            
            # 5. 결과 평가
            if results['executed_trades'] > 0:
                print(f"   ✅ 랜덤 거래 성공 ({results['executed_trades']} 거래)")
                return True
            else:
                print(f"   ❌ 모든 거래 실패")
                return False
                
        except Exception as e:
            print(f"   💥 랜덤 거래 사이클 오류: {e}")
            logger.error(f"랜덤 거래 사이클 오류: {e}")
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
                    time.sleep(0.1)  # 더 빠른 정리
                except Exception as e:
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
        print("🚀 랜덤화된 자가매매 시스템 시작!")
        print(f"🎲 특징: 다양한 거래 크기 + 랜덤 패턴 + 가격 변동성")
        print(f"🎯 목표: 실제 차트 움직임 생성")
        print(f"💫 특수 패턴: 트렌드, 시장 충격, 물량 축적")
        
        def trading_loop():
            last_cleanup = time.time()
            consecutive_failures = 0
            max_failures = 3
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - 랜덤 자가매매 실행")
                    
                    # 랜덤 자가매매 실행
                    success = self.execute_randomized_trade_cycle()
                    
                    if success:
                        consecutive_failures = 0
                        
                        # 🔥 상세 통계 출력
                        print(f"   📈 실시간 통계:")
                        print(f"      - 오늘 거래량: {self.total_volume_today:,.0f} SPSI")
                        print(f"      - 오늘 거래 횟수: {self.total_trades_today}회")
                        print(f"      - 매수 성공: {self.successful_buys}회")
                        print(f"      - 매도 성공: {self.successful_sells}회")
                        print(f"      - 누적 수수료: ${self.total_fees_paid:.4f}")
                        
                        # 패턴 통계
                        print(f"   🎲 패턴 통계:")
                        print(f"      - 크기: micro({self.pattern_stats['micro']}), small({self.pattern_stats['small']}), medium({self.pattern_stats['medium']}), large({self.pattern_stats['large']}), huge({self.pattern_stats['huge']})")
                        print(f"      - 가격: conservative({self.pattern_stats['conservative']}), normal({self.pattern_stats['normal']}), aggressive({self.pattern_stats['aggressive']}), market({self.pattern_stats['market']})")
                        
                        # 현재 패턴 상태
                        if self.current_pattern:
                            print(f"      - 현재 패턴: {self.current_pattern} (카운터: {self.pattern_counter})")
                        
                        # 균형 상태
                        if self.successful_buys > 0 and self.successful_sells > 0:
                            balance_ratio = min(self.successful_buys, self.successful_sells) / max(self.successful_buys, self.successful_sells)
                            print(f"      - 균형 비율: {balance_ratio*100:.1f}%")
                        
                    else:
                        consecutive_failures += 1
                        print(f"   ⚠️ 거래 실패 ({consecutive_failures}/{max_failures})")
                        
                        if consecutive_failures >= max_failures:
                            print(f"   🛑 연속 {max_failures}회 실패로 일시 정지")
                            print(f"   ⏳ 3분 후 재시도...")
                            time.sleep(180)  # 3분 대기
                            consecutive_failures = 0
                    
                    # 정기 정리
                    if current_time - last_cleanup > 900:  # 15분마다
                        print(f"\n🧹 정기 주문 정리...")
                        self.cleanup_old_orders()
                        last_cleanup = current_time
                    
                    # 🔥 랜덤 대기
                    if self.running:
                        next_interval = self.get_random_interval()
                        print(f"   ⏳ {next_interval}초 대기...")
                        time.sleep(next_interval)
                    
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
                        time.sleep(5)  # 짧은 대기
        
        self.trading_thread = threading.Thread(target=trading_loop, daemon=True)
        self.trading_thread.start()

    def stop_self_trading(self):
        """자가매매 중지"""
        if not self.running:
            print("⚠️ 자가매매가 실행되고 있지 않습니다")
            return
        
        self.running = False
        print("⏹️ 랜덤 자가매매 중지 요청됨...")
        
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
            
            print(f"\n{'='*70}")
            print(f"🎲 랜덤화된 자가매매 시스템 상태")
            print(f"{'='*70}")
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
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"🔄 실행 상태: {'🟢 활성' if self.running else '🔴 중지'}")
            
            # 🔥 상세 거래 통계
            stats = self.chart.get_enhanced_stats()
            print(f"📊 거래 통계:")
            print(f"   - 오늘 총 거래량: {self.total_volume_today:,.0f} SPSI")
            print(f"   - 오늘 총 거래 횟수: {self.total_trades_today}회")
            print(f"   - 매수 성공: {self.successful_buys}회")
            print(f"   - 매도 성공: {self.successful_sells}회")
            print(f"   - 누적 수수료: ${self.total_fees_paid:.4f}")
            print(f"   - 대기 주문: {len(self.current_orders)}개")
            
            # 🎲 패턴 통계
            print(f"🎲 패턴 통계:")
            print(f"   - 거래 크기: micro({self.pattern_stats['micro']}), small({self.pattern_stats['small']}), medium({self.pattern_stats['medium']}), large({self.pattern_stats['large']}), huge({self.pattern_stats['huge']})")
            print(f"   - 가격 전략: conservative({self.pattern_stats['conservative']}), normal({self.pattern_stats['normal']}), aggressive({self.pattern_stats['aggressive']}), market({self.pattern_stats['market']})")
            
            # 현재 패턴 상태
            if self.current_pattern:
                print(f"💫 현재 특수 패턴: {self.current_pattern} (진행: {self.pattern_counter})")
            
            # 🔥 가격 변동성 분석
            if 'price_volatility' in stats:
                vol = stats['price_volatility']
                print(f"📈 가격 변동성:")
                print(f"   - 평균 변동: {vol['avg_impact']:.3f}%")
                print(f"   - 최대 변동: {vol['max_impact']:.3f}%")
                print(f"   - 변동성 점수: {vol['volatility_score']:.3f}%")
                
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    def show_enhanced_chart(self):
        """향상된 거래 차트 표시"""
        try:
            print("📊 향상된 거래 차트 생성 중...")
            
            # 차트 생성
            chart_filename = f"random_trading_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.chart.plot_enhanced_chart(chart_filename)
            
            # 통계 출력
            stats = self.chart.get_enhanced_stats()
            print(f"\n📈 향상된 거래 통계:")
            print(f"   - 총 거래 시도: {stats['total_trades']}회")
            print(f"   - 매수 성공: {stats['total_buys']}회")
            print(f"   - 매도 성공: {stats['total_sells']}회")
            print(f"   - 매수 거래량: {stats['buy_volume']:,.0f} SPSI")
            print(f"   - 매도 거래량: {stats['sell_volume']:,.0f} SPSI")
            
            # 거래 크기 분석
            if 'size_analysis' in stats:
                print(f"\n🎲 거래 크기 분석:")
                for size_type, data in stats['size_analysis'].items():
                    print(f"   - {size_type}: {data['count']}회 (총 ${data['total_value']:.2f})")
            
            # 가격 변동성 분석
            if 'price_volatility' in stats:
                vol = stats['price_volatility']
                print(f"\n📈 가격 변동성 분석:")
                print(f"   - 평균 변동: {vol['avg_impact']:.3f}%")
                print(f"   - 최대 변동: {vol['max_impact']:.3f}%")
                print(f"   - 변동성 점수: {vol['volatility_score']:.3f}%")
                
                # 변동성 평가
                if vol['volatility_score'] > 0.1:
                    print(f"   - 평가: 🔥 높은 변동성 (차트 활성화)")
                elif vol['volatility_score'] > 0.05:
                    print(f"   - 평가: 📊 중간 변동성")
                else:
                    print(f"   - 평가: 📈 낮은 변동성")
            
        except Exception as e:
            print(f"❌ 향상된 차트 생성 오류: {e}")
            logger.error(f"향상된 차트 생성 오류: {e}")

    def test_single_random_trade(self):
        """1회 랜덤 거래 테스트"""
        print("🎲 1회 랜덤 거래 테스트 실행...")
        
        # 거래 전 상태
        before_balance = self.get_account_balance()
        current_price = self.get_reference_price()
        
        if before_balance and current_price:
            print(f"\n📊 거래 전 상태:")
            print(f"   - USDT: ${before_balance['usdt']:.2f}")
            print(f"   - SPSI: {before_balance['spsi']:,.0f}")
            print(f"   - 현재 가격: ${current_price:.6f}")
        
        # 테스트 실행
        result = self.execute_randomized_trade_cycle()
        
        if result:
            print("\n✅ 랜덤 거래 테스트 성공!")
            print("🎯 실제 주문이 배치되었습니다.")
            print("📊 차트에 다양한 크기의 거래 데이터가 추가되었습니다.")
            
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
            
            # 패턴 정보
            print(f"\n🎲 이번 거래 패턴:")
            print(f"   - 크기 분포: {dict(self.pattern_stats)}")
            if self.current_pattern:
                print(f"   - 특수 패턴: {self.current_pattern}")
                
            print("\n🧹 테스트 주문 정리를 원하시면 메뉴 6번을 실행하세요.")
            print("📊 차트 확인을 원하시면 메뉴 7번을 실행하세요.")
            return True
        else:
            print("\n❌ 랜덤 거래 테스트 실패!")
            return False

def main():
    print("🎲 랜덤화된 LBank 자가매매 시스템")
    print("🎯 특징: 다양한 거래 크기 + 랜덤 패턴 + 실제 차트 움직임")
    print("💫 목표: 평평한 차트를 활성화하여 실제 거래 차트처럼 만들기")
    
    # matplotlib 설정
    try:
        import matplotlib
        matplotlib.use('Agg')  # GUI 없이 차트 생성
        print("📊 향상된 차트 기능 활성화됨")
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
        print("📡 랜덤화된 자가매매 시스템 초기화 중...")
        st = RandomizedLBankTrader(API_KEY, API_SECRET)
        
        while True:
            try:
                print("\n" + "="*70)
                print("🎲 랜덤화된 LBank 자가매매 시스템")
                print("="*70)
                print("🎯 다양한 거래 크기 + 랜덤 패턴 + 실제 차트 움직임")
                print("💫 특수 기능: 트렌드 생성, 시장 충격, 물량 축적")
                print("📊 결과: 평평한 차트 → 활성화된 거래 차트")
                print("="*70)
                print("1. 💰 상태 확인 (잔고 + 패턴 통계)")
                print("2. 🧪 시스템 테스트 (API + 거래 준비도)")
                print("3. 🎲 랜덤 거래 1회 테스트")
                print("4. 🚀 랜덤 자가매매 시작")
                print("5. ⏹️ 자가매매 중지")
                print("6. 🧹 주문 정리 (미체결 주문 취소)")
                print("7. 📊 향상된 거래 차트 보기")
                print("8. 🎯 거래 패턴 분석")
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
                        
                        # 랜덤 거래 시뮬레이션
                        print("\n🎲 랜덤 거래 시뮬레이션:")
                        for i in range(3):
                            size_type = st.select_random_trade_size()
                            price_strategy = st.select_random_price_strategy()
                            print(f"   {i+1}. 크기: {size_type}, 가격전략: {price_strategy}")
                        
                        # 총 자산 확인
                        total_value = balance['usdt'] + (balance['spsi'] * price)
                        print(f"\n💰 총 자산: ${total_value:.2f}")
                        
                        if total_value >= 10:
                            print("✅ 자가매매 실행 가능")
                        else:
                            print("❌ 자산 부족 (최소 $10 필요)")
                    else:
                        print("❌ 기본 정보 조회 실패")
                    
                elif choice == '3':
                    print("\n⚠️ 실제 랜덤 거래가 실행됩니다!")
                    print("🎲 랜덤 거래 테스트:")
                    print("   - 다양한 크기의 거래 (미세~거대)")
                    print("   - 랜덤 가격 전략 (보수적~공격적)")
                    print("   - 특수 패턴 가능성 (트렌드, 충격, 축적)")
                    print("   - 실시간 차트 데이터 수집")
                    
                    confirm = input("정말 테스트 하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.test_single_random_trade()
                    else:
                        print("테스트 취소됨")
                    
                elif choice == '4':
                    print("\n⚠️ 랜덤 자가매매 시작 주의사항:")
                    print("- 다양한 크기의 거래를 랜덤하게 실행합니다")
                    print("- 특수 패턴으로 트렌드와 변동성을 생성합니다")
                    print("- 차트가 평평하지 않고 실제 거래처럼 움직입니다")
                    print("- 거래 간격도 랜덤하게 조정됩니다")
                    print("- 언제든지 중지할 수 있습니다")
                    
                    confirm = input("\n정말 시작하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.start_self_trading()
                        if st.running:
                            print("✅ 랜덤 자가매매 시스템이 시작되었습니다!")
                            print("💡 메뉴 1번으로 실시간 상태를 확인할 수 있습니다.")
                            print("📊 메뉴 7번으로 실시간 차트를 확인할 수 있습니다.")
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
                    print("📊 향상된 거래 차트 생성 중...")
                    st.show_enhanced_chart()
                    
                elif choice == '8':
                    print("🎯 거래 패턴 분석...")
                    stats = st.chart.get_enhanced_stats()
                    
                    print(f"\n🎲 상세 패턴 분석:")
                    print(f"   - 총 거래 시도: {stats['total_trades']}회")
                    print(f"   - 매수 성공: {stats['total_buys']}회")
                    print(f"   - 매도 성공: {stats['total_sells']}회")
                    
                    # 거래 크기 분석
                    if 'size_analysis' in stats:
                        print(f"\n📊 거래 크기 분석:")
                        for size_type, data in stats['size_analysis'].items():
                            avg_value = data['total_value'] / data['count'] if data['count'] > 0 else 0
                            print(f"   - {size_type}: {data['count']}회 (평균 ${avg_value:.2f})")
                    
                    # 가격 변동성 분석
                    if 'price_volatility' in stats:
                        vol = stats['price_volatility']
                        print(f"\n📈 가격 변동성 분석:")
                        print(f"   - 평균 변동: {vol['avg_impact']:.3f}%")
                        print(f"   - 최대 변동: {vol['max_impact']:.3f}%")
                        print(f"   - 변동성 점수: {vol['volatility_score']:.3f}%")
                        
                        # 변동성 레벨 평가
                        if vol['volatility_score'] > 0.1:
                            print(f"   - 변동성 레벨: 🔥 매우 높음 (차트 활성화 성공)")
                        elif vol['volatility_score'] > 0.05:
                            print(f"   - 변동성 레벨: 📊 높음 (차트 움직임 양호)")
                        elif vol['volatility_score'] > 0.02:
                            print(f"   - 변동성 레벨: 📈 보통 (차트 움직임 있음)")
                        else:
                            print(f"   - 변동성 레벨: 📉 낮음 (더 많은 거래 필요)")
                    
                    # 패턴 효과 분석
                    print(f"\n💫 패턴 효과 분석:")
                    print(f"   - 크기 분포: {dict(st.pattern_stats)}")
                    if st.current_pattern:
                        print(f"   - 현재 특수 패턴: {st.current_pattern}")
                    
                    total_patterns = sum([st.pattern_stats[key] for key in ['micro', 'small', 'medium', 'large', 'huge']])
                    if total_patterns > 0:
                        print(f"   - 다양성 점수: {len([v for v in st.pattern_stats.values() if v > 0])}/9")
                
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
