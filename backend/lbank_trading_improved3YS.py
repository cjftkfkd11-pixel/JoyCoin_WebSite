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
        self.trade_history = deque(maxlen=300)
        self.buy_orders = deque(maxlen=300)
        self.sell_orders = deque(maxlen=300)
        
        # 실시간 통계
        self.total_buys = 0
        self.total_sells = 0
        self.total_buy_volume = 0
        self.total_sell_volume = 0
        
        # 🔥 거래 패턴 추적
        self.recent_trade_sizes = deque(maxlen=100)
        self.recent_price_impacts = deque(maxlen=100)
        self.price_momentum = deque(maxlen=30)
        self.box_range_history = deque(maxlen=50)  # 박스권 기록
        
    def add_price_data(self, price: float, volume: float = 0):
        """가격 데이터 추가"""
        timestamp = datetime.now()
        self.price_history.append({
            'time': timestamp,
            'price': price,
            'volume': volume
        })
        
        # 가격 변동성 및 모멘텀 계산
        if len(self.price_history) > 1:
            prev_price = self.price_history[-2]['price']
            price_change = (price - prev_price) / prev_price
            self.recent_price_impacts.append(abs(price_change))
            self.price_momentum.append(price_change)
        
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
            'size_type': trade_size_type
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
                
            # 거래 크기 추적
            self.recent_trade_sizes.append({
                'amount': amount,
                'value': amount * price,
                'type': trade_type,
                'size_type': trade_size_type
            })
    
    def add_box_range_data(self, upper_bound: float, lower_bound: float, current_price: float):
        """박스권 데이터 추가"""
        self.box_range_history.append({
            'time': datetime.now(),
            'upper': upper_bound,
            'lower': lower_bound,
            'current': current_price,
            'position': (current_price - lower_bound) / (upper_bound - lower_bound) if upper_bound > lower_bound else 0.5
        })
    
    def plot_box_trading_chart(self, save_path: str = None):
        """🔥 박스권 거래 차트 생성"""
        if len(self.price_history) < 2:
            print("⚠️ 가격 데이터 부족 (최소 2개 필요)")
            return
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 12))
        
        # 1. 🔥 가격 차트 + 박스권 + 거래 포인트
        times = [d['time'] for d in self.price_history]
        prices = [d['price'] for d in self.price_history]
        
        ax1.plot(times, prices, 'b-', linewidth=3, label='SPSI 가격', alpha=0.9)
        
        # 박스권 표시
        if self.box_range_history:
            box_times = [d['time'] for d in self.box_range_history]
            upper_bounds = [d['upper'] for d in self.box_range_history]
            lower_bounds = [d['lower'] for d in self.box_range_history]
            
            ax1.plot(box_times, upper_bounds, 'r--', linewidth=2, alpha=0.7, label='저항선 (상한)')
            ax1.plot(box_times, lower_bounds, 'g--', linewidth=2, alpha=0.7, label='지지선 (하한)')
            ax1.fill_between(box_times, upper_bounds, lower_bounds, alpha=0.1, color='yellow', label='박스권')
        
        # 🔥 거래 포인트 - 더 명확한 색상과 크기
        if self.buy_orders:
            for trade in self.buy_orders:
                size_type = trade.get('size_type', 'medium')
                if size_type == 'micro':
                    color, size, alpha = 'lime', 50, 0.7
                elif size_type == 'small':
                    color, size, alpha = 'green', 70, 0.8
                elif size_type == 'medium':
                    color, size, alpha = 'darkgreen', 90, 0.9
                elif size_type == 'large':
                    color, size, alpha = 'forestgreen', 130, 0.95
                else:  # huge/massive
                    color, size, alpha = 'darkgreen', 200, 1.0
                
                ax1.scatter(trade['time'], trade['price'], 
                           color=color, s=size, alpha=alpha, 
                           marker='^', edgecolors='black', linewidth=2,
                           label='매수' if trade == self.buy_orders[0] else "")
                
        if self.sell_orders:
            for trade in self.sell_orders:
                size_type = trade.get('size_type', 'medium')
                if size_type == 'micro':
                    color, size, alpha = 'orange', 50, 0.7
                elif size_type == 'small':
                    color, size, alpha = 'red', 70, 0.8
                elif size_type == 'medium':
                    color, size, alpha = 'darkred', 90, 0.9
                elif size_type == 'large':
                    color, size, alpha = 'crimson', 130, 0.95
                else:  # huge/massive
                    color, size, alpha = 'darkred', 200, 1.0
                
                ax1.scatter(trade['time'], trade['price'], 
                           color=color, s=size, alpha=alpha, 
                           marker='v', edgecolors='black', linewidth=2,
                           label='매도' if trade == self.sell_orders[0] else "")
        
        ax1.set_title('🎯 박스권 거래 시스템 (지지선/저항선)', fontsize=16, fontweight='bold')
        ax1.set_ylabel('가격 (USDT)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. 🔥 거래량 폭발 차트
        if self.recent_trade_sizes:
            recent_times = list(range(len(self.recent_trade_sizes)))
            buy_volumes = []
            sell_volumes = []
            
            for i, trade in enumerate(self.recent_trade_sizes):
                if trade['type'] == 'buy':
                    buy_volumes.append(trade['amount'])
                    sell_volumes.append(0)
                else:
                    buy_volumes.append(0)
                    sell_volumes.append(trade['amount'])
            
            # 스택 바 차트로 거래량 표시
            ax2.bar(recent_times, buy_volumes, color='green', alpha=0.8, label='매수 거래량')
            ax2.bar(recent_times, sell_volumes, bottom=buy_volumes, color='red', alpha=0.8, label='매도 거래량')
            
            ax2.set_title('🚀 실시간 거래량 폭발', fontsize=16, fontweight='bold')
            ax2.set_ylabel('거래량 (SPSI)', fontsize=12)
            ax2.set_xlabel('거래 순서', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 평균 거래량 라인
            if self.recent_trade_sizes:
                avg_volume = np.mean([t['amount'] for t in self.recent_trade_sizes])
                ax2.axhline(y=avg_volume, color='blue', linestyle='--', linewidth=2, 
                           label=f'평균: {avg_volume:,.0f} SPSI')
        
        # 3. 🔥 박스권 위치 분석
        if self.box_range_history:
            box_times_range = list(range(len(self.box_range_history)))
            positions = [d['position'] * 100 for d in self.box_range_history]  # 백분율
            
            # 박스권 내 위치 표시 (0% = 지지선, 100% = 저항선)
            colors = ['red' if p > 80 else 'orange' if p > 60 else 'green' if p < 20 else 'yellow' if p < 40 else 'blue' for p in positions]
            ax3.scatter(box_times_range, positions, c=colors, s=60, alpha=0.8)
            ax3.plot(box_times_range, positions, 'gray', alpha=0.5, linewidth=1)
            
            # 기준선들
            ax3.axhline(y=80, color='red', linestyle='--', alpha=0.7, label='저항선 근처 (80%)')
            ax3.axhline(y=50, color='blue', linestyle='-', alpha=0.7, label='박스 중간 (50%)')
            ax3.axhline(y=20, color='green', linestyle='--', alpha=0.7, label='지지선 근처 (20%)')
            
            ax3.set_title('📊 박스권 내 가격 위치', fontsize=16, fontweight='bold')
            ax3.set_ylabel('박스 내 위치 (%)', fontsize=12)
            ax3.set_xlabel('시간 순서', fontsize=12)
            ax3.set_ylim(0, 100)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # 4. 🔥 매수/매도 균형 분석
        if len(self.recent_trade_sizes) > 10:
            window_size = 10
            buy_ratios = []
            sell_ratios = []
            
            for i in range(window_size, len(self.recent_trade_sizes)):
                window = self.recent_trade_sizes[i-window_size:i]
                buy_vol = sum(t['amount'] for t in window if t['type'] == 'buy')
                sell_vol = sum(t['amount'] for t in window if t['type'] == 'sell')
                total_vol = buy_vol + sell_vol
                
                if total_vol > 0:
                    buy_ratios.append(buy_vol / total_vol * 100)
                    sell_ratios.append(sell_vol / total_vol * 100)
                else:
                    buy_ratios.append(50)
                    sell_ratios.append(50)
            
            times_balance = list(range(len(buy_ratios)))
            ax4.plot(times_balance, buy_ratios, 'green', linewidth=3, label='매수 비율', alpha=0.8)
            ax4.plot(times_balance, sell_ratios, 'red', linewidth=3, label='매도 비율', alpha=0.8)
            ax4.fill_between(times_balance, buy_ratios, alpha=0.3, color='green')
            ax4.fill_between(times_balance, sell_ratios, alpha=0.3, color='red')
            
            # 균형선
            ax4.axhline(y=50, color='black', linestyle='-', alpha=0.5, label='균형선 (50%)')
            
            ax4.set_title('⚖️ 매수/매도 균형 (이동평균)', fontsize=16, fontweight='bold')
            ax4.set_ylabel('비율 (%)', fontsize=12)
            ax4.set_xlabel('시간 순서', fontsize=12)
            ax4.set_ylim(0, 100)
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 박스권 거래 차트 저장됨: {save_path}")
        
        plt.show()
        
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """향상된 거래 통계"""
        stats = {
            'total_trades': len(self.trade_history),
            'total_buys': self.total_buys,
            'total_sells': self.total_sells,
            'buy_volume': self.total_buy_volume,
            'sell_volume': self.total_sell_volume,
            'recent_trades': list(self.trade_history)[-15:] if self.trade_history else []
        }
        
        # 거래 크기 분석
        if self.recent_trade_sizes:
            size_analysis = {}
            for trade in self.recent_trade_sizes:
                size_type = trade['size_type']
                if size_type not in size_analysis:
                    size_analysis[size_type] = {'count': 0, 'total_value': 0, 'total_volume': 0}
                size_analysis[size_type]['count'] += 1
                size_analysis[size_type]['total_value'] += trade['value']
                size_analysis[size_type]['total_volume'] += trade['amount']
            
            stats['size_analysis'] = size_analysis
        
        # 가격 변동성 분석
        if self.recent_price_impacts:
            stats['price_volatility'] = {
                'avg_impact': np.mean(self.recent_price_impacts) * 100,
                'max_impact': max(self.recent_price_impacts) * 100,
                'min_impact': min(self.recent_price_impacts) * 100,
                'volatility_score': np.std(self.recent_price_impacts) * 100
            }
        
        # 박스권 분석
        if self.box_range_history:
            recent_positions = [d['position'] for d in self.box_range_history[-20:]]
            stats['box_analysis'] = {
                'avg_position': np.mean(recent_positions) * 100,
                'position_volatility': np.std(recent_positions) * 100,
                'upper_touches': sum(1 for p in recent_positions if p > 0.8),
                'lower_touches': sum(1 for p in recent_positions if p < 0.2),
                'box_efficiency': len([p for p in recent_positions if 0.2 <= p <= 0.8]) / len(recent_positions) if recent_positions else 0
            }
        
        return stats

class SafeAPIResponseHandler:
    """안전한 API 응답 처리를 위한 헬퍼 클래스"""
    
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

class OptimalBoxTradingSystem:
    """🔥 적정용량 박스권 거래 시스템 - 박스권 유지 + 적절한 거래량"""
    
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.trading_thread = None
        
        # 거래 설정
        self.symbol = "spsi_usdt"
        
        # 🔥 적정 거래량 설정 (5분에 3만~6만)
        self.min_volume_per_5min = 30000    # 3만 SPSI
        self.max_volume_per_5min = 60000    # 6만 SPSI
        self.trade_interval_base = 30       # 30초마다 거래
        
        # 🔥 적정 크기 거래 설정 (5분에 5회 거래 기준)
        self.trade_sizes = {
            'micro': {'min': 15800, 'max': 28950, 'probability': 0.25},     # 25% - 미세
            'small': {'min': 21580, 'max': 32580, 'probability': 0.3},     # 30% - 소량
            'medium': {'min': 28560, 'max': 45500, 'probability': 0.25},  # 25% - 중간
            'large': {'min': 34250, 'max': 55800, 'probability': 0.15},  # 15% - 대량
            'huge': {'min': 42500, 'max': 63450, 'probability': 0.05}   # 5% - 거대
        }
        
        # 🔥 박스권 설정
        self.box_range_percentage = 0.02    # 박스 범위 2% (상하 1%씩)
        self.box_center_price = None        # 박스 중심 가격
        self.box_upper_bound = None         # 저항선
        self.box_lower_bound = None         # 지지선
        self.box_reset_interval = 300       # 5분마다 박스 재설정
        self.last_box_reset = time.time()
        
        # 🔥 박스권 거래 전략
        self.support_resistance_strength = 0.8    # 지지/저항 강도
        self.mean_reversion_force = 0.9           # 평균회귀 힘
        self.breakout_prevention = 0.95           # 돌파 방지 강도
        
        # 가격 전략 (박스권 특화)
        self.price_strategies = {
            'box_support': {'probability': 0.3},      # 30% - 지지선 근처
            'box_resistance': {'probability': 0.3},   # 30% - 저항선 근처
            'box_center': {'probability': 0.2},       # 20% - 박스 중앙
            'mean_revert': {'probability': 0.2}       # 20% - 평균회귀
        }
        
        # 패턴 상태
        self.current_box_position = 0.5  # 0=지지선, 1=저항선
        self.price_direction_bias = 0    # -1=하락편향, 0=중립, 1=상승편향
        self.consecutive_same_direction = 0
        self.last_trade_direction = None
        
        # 기본 설정
        self.min_order_size = 8000
        self.min_trade_value_usd = 5.0
        self.max_trade_value_usd = 100.0
        
        self.base_price = None
        self.current_orders = []
        
        # 통계
        self.total_volume_today = 0
        self.total_trades_today = 0
        self.total_fees_paid = 0.0
        self.successful_buys = 0
        self.successful_sells = 0
        self.box_maintenance_score = 0.0
        
        # 패턴별 통계
        self.pattern_stats = {
            'micro': 0, 'small': 0, 'medium': 0, 'large': 0, 'huge': 0, 'massive': 0,
            'box_support': 0, 'box_resistance': 0, 'box_center': 0, 'mean_revert': 0
        }
        
        # 차트 시스템
        self.chart = TradingChart()
        self.response_handler = SafeAPIResponseHandler()
        
        print("🎯 적정용량 박스권 거래 시스템 초기화 완료")
        print(f"📈 목표 거래량: {self.min_volume_per_5min:,} ~ {self.max_volume_per_5min:,} SPSI/5분")
        print(f"🎲 거래 크기: 2000 ~ 20,000 SPSI (5단계)")
        print(f"📦 박스권: ±{self.box_range_percentage*100:.1f}% 범위")
        print(f"⚡ 거래 간격: {self.trade_interval_base}초 기준")
        logger.info("적정용량 박스권 거래 시스템 초기화 완료")

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
            
            if 'free' in actual_data and isinstance(actual_data['free'], dict):
                free_data = actual_data['free']
                if 'usdt' in free_data:
                    usdt_balance = float(free_data['usdt']) if free_data['usdt'] else 0.0
                if 'spsi' in free_data:
                    spsi_balance = float(free_data['spsi']) if free_data['spsi'] else 0.0
            
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
                self.setup_initial_box_range(market_price)
                logger.info(f"기준 가격 및 박스권 설정: ${self.base_price:.6f}")
                return self.base_price
            
            # 박스권 데이터 추가
            if self.box_upper_bound and self.box_lower_bound:
                self.chart.add_box_range_data(self.box_upper_bound, self.box_lower_bound, market_price)
            
            # 🔥 박스권 유지를 위한 조건부 업데이트
            self.update_box_position(market_price)
            
            return market_price
            
        except Exception as e:
            logger.error(f"기준 가격 계산 오류: {e}")
            return self.base_price

    def setup_initial_box_range(self, current_price: float):
        """🔥 초기 박스권 설정"""
        self.box_center_price = current_price
        self.box_upper_bound = current_price * (1 + self.box_range_percentage / 2)
        self.box_lower_bound = current_price * (1 - self.box_range_percentage / 2)
        self.last_box_reset = time.time()
        
        print(f"   📦 박스권 설정:")
        print(f"      - 중심가: ${self.box_center_price:.6f}")
        print(f"      - 저항선: ${self.box_upper_bound:.6f}")
        print(f"      - 지지선: ${self.box_lower_bound:.6f}")
        print(f"      - 박스폭: {((self.box_upper_bound - self.box_lower_bound) / self.box_center_price * 100):.2f}%")

    def update_box_position(self, current_price: float):
        """🔥 박스권 내 위치 업데이트"""
        if not self.box_upper_bound or not self.box_lower_bound:
            return
        
        # 박스 내 위치 계산 (0=지지선, 1=저항선)
        box_range = self.box_upper_bound - self.box_lower_bound
        if box_range > 0:
            self.current_box_position = (current_price - self.box_lower_bound) / box_range
            self.current_box_position = max(0, min(1, self.current_box_position))  # 0-1 범위로 제한
        
        # 🔥 박스권 리셋 조건
        current_time = time.time()
        if current_time - self.last_box_reset > self.box_reset_interval:
            self.reset_box_range(current_price)

    def reset_box_range(self, current_price: float):
        """🔥 박스권 리셋 (주기적 또는 돌파시)"""
        print(f"   🔄 박스권 리셋:")
        print(f"      - 이전 박스: ${self.box_lower_bound:.6f} ~ ${self.box_upper_bound:.6f}")
        
        # 새로운 박스권 설정
        self.box_center_price = current_price
        self.box_upper_bound = current_price * (1 + self.box_range_percentage / 2)
        self.box_lower_bound = current_price * (1 - self.box_range_percentage / 2)
        self.last_box_reset = time.time()
        
        print(f"      - 새로운 박스: ${self.box_lower_bound:.6f} ~ ${self.box_upper_bound:.6f}")
        
        # 박스 유지 점수 리셋
        self.box_maintenance_score = 0.0

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

    def select_optimal_trade_size(self) -> str:
        """🎲 적정 거래 크기 선택"""
        rand = random.random()
        cumulative = 0
        
        for size_type, config in self.trade_sizes.items():
            cumulative += config['probability']
            if rand <= cumulative:
                return size_type
        
        return 'medium'

    def select_box_strategy(self) -> str:
        """🎯 박스권 전략 선택"""
        rand = random.random()
        cumulative = 0
        
        for strategy, config in self.price_strategies.items():
            cumulative += config['probability']
            if rand <= cumulative:
                return strategy
        
        return 'box_center'

    def calculate_box_aware_trade_direction(self, current_price: float) -> Dict[str, Any]:
        """🔥 박스권 인식 거래 방향 결정"""
        try:
            # 현재 박스 위치 분석
            if self.current_box_position > 0.8:
                # 저항선 근처 - 매도 압력 증가
                direction_bias = 'sell_heavy'
                buy_ratio = 0.2
                sell_ratio = 0.8
                print(f"      - 박스 위치: 저항선 근처 ({self.current_box_position*100:.1f}%) → 매도 압력")
            elif self.current_box_position < 0.2:
                # 지지선 근처 - 매수 압력 증가
                direction_bias = 'buy_heavy'
                buy_ratio = 0.8
                sell_ratio = 0.2
                print(f"      - 박스 위치: 지지선 근처 ({self.current_box_position*100:.1f}%) → 매수 압력")
            elif 0.4 <= self.current_box_position <= 0.6:
                # 박스 중앙 - 균형 거래
                direction_bias = 'balanced'
                buy_ratio = 0.5
                sell_ratio = 0.5
                print(f"      - 박스 위치: 중앙 ({self.current_box_position*100:.1f}%) → 균형 거래")
            else:
                # 중간 지역 - 약간의 편향
                if self.current_box_position > 0.5:
                    direction_bias = 'sell_bias'
                    buy_ratio = 0.3
                    sell_ratio = 0.7
                    print(f"      - 박스 위치: 상단 ({self.current_box_position*100:.1f}%) → 매도 편향")
                else:
                    direction_bias = 'buy_bias'
                    buy_ratio = 0.7
                    sell_ratio = 0.3
                    print(f"      - 박스 위치: 하단 ({self.current_box_position*100:.1f}%) → 매수 편향")
            
            # 🔥 연속 같은 방향 거래 방지 (박스권 유지)
            if self.consecutive_same_direction >= 3:
                if self.last_trade_direction == 'buy':
                    # 연속 매수 방지 - 매도 강제
                    direction_bias = 'force_sell'
                    buy_ratio = 0.1
                    sell_ratio = 0.9
                    print(f"      - 연속 매수 방지 → 강제 매도")
                elif self.last_trade_direction == 'sell':
                    # 연속 매도 방지 - 매수 강제
                    direction_bias = 'force_buy'
                    buy_ratio = 0.9
                    sell_ratio = 0.1
                    print(f"      - 연속 매도 방지 → 강제 매수")
            
            return {
                'direction_bias': direction_bias,
                'buy_ratio': buy_ratio,
                'sell_ratio': sell_ratio,
                'box_position': self.current_box_position
            }
            
        except Exception as e:
            print(f"   ❌ 박스권 거래 방향 계산 오류: {e}")
            return {
                'direction_bias': 'balanced',
                'buy_ratio': 0.5,
                'sell_ratio': 0.5,
                'box_position': 0.5
            }

    def generate_optimal_box_trade_amount(self, size_type: str, current_price: float, balance: Dict[str, float]) -> Dict[str, float]:
        """🔥 적정용량 박스권 거래량 생성"""
        try:
            # 1. 기본 거래량 범위 (대폭 증가)
            size_config = self.trade_sizes[size_type]
            min_amount = size_config['min']
            max_amount = size_config['max']
            
            # 2. 랜덤 거래량 + 추가 증폭
            base_amount = random.uniform(min_amount, max_amount)
            
            # 3. 🔥 박스권 위치에 따른 추가 증폭
            if self.current_box_position > 0.85 or self.current_box_position < 0.15:
                # 박스 경계 근처 - 큰 거래량으로 강한 반전 압력
                base_amount *= random.uniform(1.5, 2.5)
                print(f"      - 박스 경계 증폭: {base_amount:,.0f} SPSI")
            elif size_type in ['huge', 'massive']:
                # 초대형 거래 - 추가 증폭
                base_amount *= random.uniform(1.2, 1.8)
                print(f"      - 초대형 거래 증폭: {base_amount:,.0f} SPSI")
            
            # 4. 잔고 제한 (더 공격적으로)
            available_usdt = balance['usdt'] * 0.95  # 95% 사용
            available_spsi = balance['spsi'] * 0.95  # 95% 사용
            
            max_buy_amount = available_usdt / current_price if current_price > 0 else 0
            max_sell_amount = available_spsi
            
            # 5. 박스권 인식 거래 방향 결정
            direction_info = self.calculate_box_aware_trade_direction(current_price)
            buy_ratio = direction_info['buy_ratio']
            sell_ratio = direction_info['sell_ratio']
            
            # 6. 거래량 배분
            buy_amount = min(base_amount * buy_ratio, max_buy_amount)
            sell_amount = min(base_amount * sell_ratio, max_sell_amount)
            
            # 7. 최소값 보장 (대폭 증가)
            if buy_amount < self.min_order_size:
                buy_amount = min(self.min_order_size * 3, max_buy_amount)
            if sell_amount < self.min_order_size:
                sell_amount = min(self.min_order_size * 3, max_sell_amount)
            
            return {
                'buy_amount': round(buy_amount, 2),
                'sell_amount': round(sell_amount, 2),
                'size_type': size_type,
                'direction_bias': direction_info['direction_bias'],
                'box_position': direction_info['box_position']
            }
            
        except Exception as e:
            print(f"   ❌ 적정용량 박스권 거래량 생성 오류: {e}")
            return {
                'buy_amount': 1000,
                'sell_amount': 1000,
                'size_type': 'medium',
                'direction_bias': 'balanced',
                'box_position': 0.5
            }

    def calculate_box_smart_price(self, trade_type: str, current_price: float, strategy: str) -> float:
        """🔥 박스권 스마트 가격 계산"""
        try:
            if strategy == 'box_support':
                # 지지선 전략 - 지지선 근처에서 매수, 중앙으로 매도
                if trade_type == 'buy':
                    # 지지선보다 약간 높은 가격으로 매수 (빠른 체결)
                    target_price = self.box_lower_bound * (1 + random.uniform(0.001, 0.003))
                else:
                    # 중앙 가격으로 매도
                    target_price = self.box_center_price * (1 + random.uniform(-0.001, 0.001))
                    
            elif strategy == 'box_resistance':
                # 저항선 전략 - 저항선 근처에서 매도, 중앙으로 매수
                if trade_type == 'sell':
                    # 저항선보다 약간 낮은 가격으로 매도 (빠른 체결)
                    target_price = self.box_upper_bound * (1 - random.uniform(0.001, 0.003))
                else:
                    # 중앙 가격으로 매수
                    target_price = self.box_center_price * (1 + random.uniform(-0.001, 0.001))
                    
            elif strategy == 'mean_revert':
                # 평균회귀 전략 - 현재가가 중앙에서 멀어질수록 강한 복귀 압력
                distance_from_center = abs(current_price - self.box_center_price) / self.box_center_price
                revert_strength = distance_from_center * self.mean_reversion_force
                
                if current_price > self.box_center_price:
                    # 중앙보다 높으면 매도 압력
                    if trade_type == 'sell':
                        target_price = current_price * (1 - revert_strength * 0.005)
                    else:
                        target_price = current_price * (1 + revert_strength * 0.002)
                else:
                    # 중앙보다 낮으면 매수 압력
                    if trade_type == 'buy':
                        target_price = current_price * (1 + revert_strength * 0.005)
                    else:
                        target_price = current_price * (1 - revert_strength * 0.002)
                        
            else:  # box_center
                # 박스 중앙 전략 - 중앙 근처에서 균형 거래
                spread = random.uniform(0.001, 0.002)
                if trade_type == 'buy':
                    target_price = current_price * (1 + spread)
                else:
                    target_price = current_price * (1 - spread)
            
            # 박스 범위 내로 제한
            target_price = max(self.box_lower_bound * 0.999, min(self.box_upper_bound * 1.001, target_price))
            
            return round(target_price, 6)
            
        except Exception as e:
            print(f"   ❌ 박스권 가격 계산 오류: {e}")
            # 기본 가격 반환
            spread = 0.001
            if trade_type == 'buy':
                return round(current_price * (1 + spread), 6)
            else:
                return round(current_price * (1 - spread), 6)

    def execute_optimal_box_trade(self, current_price: float, balance: Dict[str, float]) -> Dict[str, Any]:
        """🔥 적정용량 박스권 거래 실행"""
        try:
            print(f"   📦 적정용량 박스권 거래 실행:")
            print(f"      - 현재가: ${current_price:.6f}")
            print(f"      - 박스범위: ${self.box_lower_bound:.6f} ~ ${self.box_upper_bound:.6f}")
            print(f"      - 박스위치: {self.current_box_position*100:.1f}%")
            
            # 1. 적정 거래 크기 선택
            size_type = self.select_optimal_trade_size()
            print(f"      - 거래크기: {size_type}")
            
            # 2. 박스권 전략 선택
            box_strategy = self.select_box_strategy()
            print(f"      - 박스전략: {box_strategy}")
            
            # 3. 적정용량 거래량 생성
            trade_amounts = self.generate_optimal_box_trade_amount(size_type, current_price, balance)
            
            # 4. 통계 업데이트
            self.pattern_stats[size_type] += 1
            self.pattern_stats[box_strategy] += 1
            
            results = {
                'buy_success': False,
                'sell_success': False,
                'buy_order_id': None,
                'sell_order_id': None,
                'executed_trades': 0,
                'size_type': size_type,
                'box_strategy': box_strategy,
                'direction_bias': trade_amounts.get('direction_bias')
            }
            
            # 5. 🔥 박스권 인식 거래 실행
            executed_buy = False
            executed_sell = False
            
            # 매수 거래
            if trade_amounts['buy_amount'] > 0:
                buy_price = self.calculate_box_smart_price('buy', current_price, box_strategy)
                print(f"      - 매수: {trade_amounts['buy_amount']:,.0f} SPSI @ ${buy_price:.6f}")
                
                buy_order_id = self.place_order('buy', trade_amounts['buy_amount'], buy_price)
                if buy_order_id:
                    results['buy_success'] = True
                    results['buy_order_id'] = buy_order_id
                    results['executed_trades'] += 1
                    self.successful_buys += 1
                    self.chart.add_trade_data('buy', trade_amounts['buy_amount'], buy_price, True, size_type)
                    executed_buy = True
                    print(f"      ✅ 매수 성공")
                else:
                    self.chart.add_trade_data('buy', trade_amounts['buy_amount'], buy_price, False, size_type)
                    print(f"      ❌ 매수 실패")
            
            # 매도 거래
            if trade_amounts['sell_amount'] > 0:
                time.sleep(random.uniform(0.1, 1.0))  # 짧은 대기
                
                sell_price = self.calculate_box_smart_price('sell', current_price, box_strategy)
                print(f"      - 매도: {trade_amounts['sell_amount']:,.0f} SPSI @ ${sell_price:.6f}")
                
                sell_order_id = self.place_order('sell', trade_amounts['sell_amount'], sell_price)
                if sell_order_id:
                    results['sell_success'] = True
                    results['sell_order_id'] = sell_order_id
                    results['executed_trades'] += 1
                    self.successful_sells += 1
                    self.chart.add_trade_data('sell', trade_amounts['sell_amount'], sell_price, True, size_type)
                    executed_sell = True
                    print(f"      ✅ 매도 성공")
                else:
                    self.chart.add_trade_data('sell', trade_amounts['sell_amount'], sell_price, False, size_type)
                    print(f"      ❌ 매도 실패")
            
            # 6. 🔥 연속 거래 방향 추적 (박스권 유지용)
            if executed_buy and executed_sell:
                self.last_trade_direction = 'both'
                self.consecutive_same_direction = 0
            elif executed_buy:
                if self.last_trade_direction == 'buy':
                    self.consecutive_same_direction += 1
                else:
                    self.consecutive_same_direction = 1
                self.last_trade_direction = 'buy'
            elif executed_sell:
                if self.last_trade_direction == 'sell':
                    self.consecutive_same_direction += 1
                else:
                    self.consecutive_same_direction = 1
                self.last_trade_direction = 'sell'
            
            # 7. 결과 정리
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
                
                # 박스 유지 점수 업데이트
                if trade_amounts.get('direction_bias') in ['buy_heavy', 'sell_heavy', 'force_buy', 'force_sell']:
                    self.box_maintenance_score += 2.0  # 박스 유지 기여도 높음
                else:
                    self.box_maintenance_score += 1.0
                
                print(f"   📊 적정용량 박스권 거래 결과:")
                print(f"      - 실행거래: {results['executed_trades']}")
                print(f"      - 거래크기: {size_type}")
                print(f"      - 박스전략: {box_strategy}")
                print(f"      - 거래편향: {trade_amounts.get('direction_bias')}")
                print(f"      - 총거래량: {total_volume:,.0f} SPSI")
                print(f"      - 예상수수료: ${estimated_fee:.4f}")
                print(f"      - 박스유지점수: {self.box_maintenance_score:.1f}")
                
                return results
            else:
                print(f"   ❌ 모든 거래 실패")
                return results
                
        except Exception as e:
            print(f"   💥 적정용량 박스권 거래 실행 오류: {e}")
            logger.error(f"적정용량 박스권 거래 실행 오류: {e}")
            return {'executed_trades': 0, 'size_type': 'error', 'box_strategy': 'error'}

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

    def get_dynamic_interval(self) -> int:
        """🔥 동적 거래 간격 생성"""
        base = self.trade_interval_base
        
        # 박스권 위치에 따라 간격 조정
        if self.current_box_position > 0.8 or self.current_box_position < 0.2:
            # 박스 경계 - 빠른 거래로 강한 반전 압력
            return random.randint(5, 15)
        elif 0.4 <= self.current_box_position <= 0.6:
            # 박스 중앙 - 중간 속도
            return random.randint(base, base * 2)
        else:
            # 일반 구간 - 기본 속도
            return random.randint(base // 2, base * 3)

    def execute_massive_box_cycle(self) -> bool:
        """🔥 적정용량 박스권 자가매매 사이클"""
        try:
            print("   📦 적정용량 박스권 자가매매 사이클 시작...")
            
            # 1. 기본 정보 수집
            current_price = self.get_reference_price()
            if not current_price:
                print("   ❌ 현재 가격 조회 실패")
                return False
            
            balance = self.get_account_balance()
            if not balance:
                print("   ❌ 잔고 조회 실패")
                return False
            
            # 2. 박스권 확인 및 설정
            if not self.box_upper_bound or not self.box_lower_bound:
                self.setup_initial_box_range(current_price)
            
            # 3. 미체결 주문 정리 (더 관대하게)
            open_orders = self.get_open_orders()
            if len(open_orders) > 20:  # 20개까지 허용
                print(f"   🧹 미체결 주문 {len(open_orders)}개 발견, 일부 정리...")
                self.cleanup_old_orders()
                time.sleep(1)
                
                balance = self.get_account_balance()
                if not balance:
                    print("   ❌ 정리 후 잔고 확인 실패")
                    return False
            
            # 4. 최소 자산 확인
            total_value = balance['usdt'] + (balance['spsi'] * current_price)
            if total_value < 5.0:  # $5로 하향
                print(f"   ❌ 총 자산 부족: ${total_value:.2f} < $5.0")
                return False
            
            # 5. 적정용량 박스권 거래 실행
            results = self.execute_optimal_box_trade(current_price, balance)
            
            # 6. 결과 평가
            if results['executed_trades'] > 0:
                print(f"   ✅ 적정용량 박스권 거래 성공 ({results['executed_trades']} 거래)")
                return True
            else:
                print(f"   ❌ 모든 거래 실패")
                return False
                
        except Exception as e:
            print(f"   💥 적정용량 박스권 거래 사이클 오류: {e}")
            logger.error(f"적정용량 박스권 거래 사이클 오류: {e}")
            return False

    def cleanup_old_orders(self):
        """오래된 주문들 정리"""
        try:
            if not self.current_orders:
                print("   📝 정리할 주문이 없습니다")
                return
            
            # 절반만 정리 (박스권 유지를 위해)
            orders_to_cancel = self.current_orders[:len(self.current_orders)//2]
            print(f"   🧹 주문 정리: {len(orders_to_cancel)}개 주문 취소 중...")
            
            canceled_count = 0
            for order_id in orders_to_cancel:
                try:
                    if self.cancel_order(order_id):
                        canceled_count += 1
                    self.current_orders.remove(order_id)
                    time.sleep(0.02)  # 매우 빠른 정리
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
        if total_value < 10:  # $10로 하향
            print(f"❌ 자가매매 시작 불가: 총 자산 부족 (${total_value:.2f} < $10)")
            return
        
        self.running = True
        print("🚀 적정용량 박스권 자가매매 시스템 시작!")
        print(f"📦 특징: 박스권 유지 + 적정 거래량 (200~20,000 SPSI)")
        print(f"🎯 목표: 지지선/저항선 박스권 + 적절한 거래량")
        print(f"📈 거래량: {self.min_volume_per_5min:,} ~ {self.max_volume_per_5min:,} SPSI/5분")
        print(f"📦 박스범위: ±{self.box_range_percentage*100:.1f}%")
        
        def trading_loop():
            last_cleanup = time.time()
            consecutive_failures = 0
            max_failures = 3
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - 적정용량 박스권 자가매매 실행")
                    
                    # 적정용량 박스권 자가매매 실행
                    success = self.execute_massive_box_cycle()
                    
                    if success:
                        consecutive_failures = 0
                        
                        # 🔥 상세 통계 출력
                        print(f"   📈 실시간 통계:")
                        print(f"      - 오늘 거래량: {self.total_volume_today:,.0f} SPSI")
                        print(f"      - 오늘 거래 횟수: {self.total_trades_today}회")
                        print(f"      - 매수 성공: {self.successful_buys}회")
                        print(f"      - 매도 성공: {self.successful_sells}회")
                        print(f"      - 누적 수수료: ${self.total_fees_paid:.4f}")
                        print(f"      - 박스 유지 점수: {self.box_maintenance_score:.1f}")
                        
                        # 📦 박스권 상태
                        if self.box_upper_bound and self.box_lower_bound:
                            box_width = ((self.box_upper_bound - self.box_lower_bound) / self.box_center_price * 100)
                            print(f"   📦 박스권 상태:")
                            print(f"      - 박스 중심: ${self.box_center_price:.6f}")
                            print(f"      - 박스 폭: {box_width:.2f}%")
                            print(f"      - 현재 위치: {self.current_box_position*100:.1f}%")
                            
                            if self.current_box_position > 0.8:
                                print(f"      - 상태: 🔴 저항선 근처 (매도 압력)")
                            elif self.current_box_position < 0.2:
                                print(f"      - 상태: 🟢 지지선 근처 (매수 압력)")
                            else:
                                print(f"      - 상태: 🔵 박스권 내부 (균형)")
                        
                        # 패턴 통계 (간략)
                        active_patterns = {k: v for k, v in self.pattern_stats.items() if v > 0}
                        if active_patterns:
                            print(f"   🎲 활성 패턴: {dict(list(active_patterns.items())[:5])}")  # 상위 5개만
                        
                        # 연속 거래 방향 추적
                        if self.consecutive_same_direction > 0:
                            print(f"      - 연속 {self.last_trade_direction}: {self.consecutive_same_direction}회")
                        
                        # 시간당 예상 거래량
                        avg_per_hour = (self.min_volume_per_5min + self.max_volume_per_5min) / 2 * 12
                        print(f"      - 예상 시간당: {avg_per_hour:,.0f} SPSI")
                        
                    else:
                        consecutive_failures += 1
                        print(f"   ⚠️ 거래 실패 ({consecutive_failures}/{max_failures})")
                        
                        if consecutive_failures >= max_failures:
                            print(f"   🛑 연속 {max_failures}회 실패로 일시 정지")
                            print(f"   ⏳ 1분 후 재시도...")
                            time.sleep(60)
                            consecutive_failures = 0
                    
                    # 정기 정리 (박스권 유지를 위해 덜 자주)
                    if current_time - last_cleanup > 900:  # 15분마다
                        print(f"\n🧹 정기 주문 정리...")
                        self.cleanup_old_orders()
                        last_cleanup = current_time
                    
                    # 🔥 동적 대기 (박스권 위치 기반)
                    if self.running:
                        next_interval = self.get_dynamic_interval()
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
                        time.sleep(5)
        
        self.trading_thread = threading.Thread(target=trading_loop, daemon=True)
        self.trading_thread.start()

    def stop_self_trading(self):
        """자가매매 중지"""
        if not self.running:
            print("⚠️ 자가매매가 실행되고 있지 않습니다")
            return
        
        self.running = False
        print("⏹️ 적정용량 박스권 자가매매 중지 요청됨...")
        
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
            
            print(f"\n{'='*80}")
            print(f"📦 적정용량 박스권 자가매매 시스템 상태")
            print(f"{'='*80}")
            print(f"💰 현재 가격: ${current_price:.6f}" if current_price else "💰 현재 가격: 조회 실패")
            
            # 📦 박스권 정보
            if self.box_upper_bound and self.box_lower_bound and current_price:
                print(f"📦 박스권 정보:")
                print(f"   - 저항선: ${self.box_upper_bound:.6f}")
                print(f"   - 중심가: ${self.box_center_price:.6f}")
                print(f"   - 지지선: ${self.box_lower_bound:.6f}")
                print(f"   - 박스폭: {((self.box_upper_bound - self.box_lower_bound) / self.box_center_price * 100):.2f}%")
                print(f"   - 현재위치: {self.current_box_position*100:.1f}%")
                
                # 박스 위치 시각화
                position_bar = "█" * int(self.current_box_position * 20)
                empty_bar = "░" * (20 - int(self.current_box_position * 20))
                print(f"   - 위치표시: |{position_bar}{empty_bar}| (지지선 ← → 저항선)")
                
                if self.current_box_position > 0.8:
                    print(f"   - 상태: 🔴 저항선 근처 (매도 압력 구간)")
                elif self.current_box_position < 0.2:
                    print(f"   - 상태: 🟢 지지선 근처 (매수 압력 구간)")
                elif 0.4 <= self.current_box_position <= 0.6:
                    print(f"   - 상태: 🔵 박스 중앙 (균형 구간)")
                else:
                    print(f"   - 상태: 🟡 박스 중간 (편향 구간)")
            
            if balance:
                print(f"💳 USDT 잔고: ${balance['usdt']:.2f}")
                print(f"🪙 SPSI 잔고: {balance['spsi']:,.2f}")
                
                if current_price:
                    total_value = balance['usdt'] + (balance['spsi'] * current_price)
                    print(f"💰 총 자산 가치: ${total_value:.2f}")
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"🔄 실행 상태: {'🟢 활성' if self.running else '🔴 중지'}")
            
            # 거래 통계
            stats = self.chart.get_enhanced_stats()
            print(f"📊 거래 통계:")
            print(f"   - 오늘 총 거래량: {self.total_volume_today:,.0f} SPSI")
            print(f"   - 오늘 총 거래 횟수: {self.total_trades_today}회")
            print(f"   - 매수 성공: {self.successful_buys}회")
            print(f"   - 매도 성공: {self.successful_sells}회")
            print(f"   - 누적 수수료: ${self.total_fees_paid:.4f}")
            print(f"   - 대기 주문: {len(self.current_orders)}개")
            print(f"   - 박스 유지 점수: {self.box_maintenance_score:.1f}")
            
            # 박스권 분석
            if 'box_analysis' in stats:
                box = stats['box_analysis']
                print(f"📦 박스권 분석:")
                print(f"   - 평균 위치: {box['avg_position']:.1f}%")
                print(f"   - 위치 변동성: {box['position_volatility']:.2f}%")
                print(f"   - 저항선 터치: {box['upper_touches']}회")
                print(f"   - 지지선 터치: {box['lower_touches']}회")
                print(f"   - 박스 효율성: {box['box_efficiency']*100:.1f}%")
            
            # 연속 거래 추적
            if self.consecutive_same_direction > 0:
                print(f"🔄 연속 거래: {self.last_trade_direction} {self.consecutive_same_direction}회")
            
            # 가격 변동성
            if 'price_volatility' in stats:
                vol = stats['price_volatility']
                print(f"📈 가격 변동성:")
                print(f"   - 평균 변동: {vol['avg_impact']:.3f}%")
                print(f"   - 변동성 점수: {vol['volatility_score']:.3f}%")
            
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    def show_box_trading_chart(self):
        """박스권 거래 차트 표시"""
        try:
            print("📊 박스권 거래 차트 생성 중...")
            
            # 차트 생성
            chart_filename = f"box_trading_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.chart.plot_box_trading_chart(chart_filename)
            
            # 통계 출력
            stats = self.chart.get_enhanced_stats()
            print(f"\n📦 박스권 거래 통계:")
            print(f"   - 총 거래 시도: {stats['total_trades']}회")
            print(f"   - 매수 성공: {stats['total_buys']}회 (🟢 초록색)")
            print(f"   - 매도 성공: {stats['total_sells']}회 (🔴 빨간색)")
            print(f"   - 매수 거래량: {stats['buy_volume']:,.0f} SPSI")
            print(f"   - 매도 거래량: {stats['sell_volume']:,.0f} SPSI")
            
            # 거래 크기 분석
            if 'size_analysis' in stats:
                print(f"\n🎲 거래 크기 분석:")
                total_volume = sum(data['total_volume'] for data in stats['size_analysis'].values())
                for size_type, data in stats['size_analysis'].items():
                    percentage = (data['total_volume'] / total_volume * 100) if total_volume > 0 else 0
                    avg_value = data['total_value'] / data['count'] if data['count'] > 0 else 0
                    print(f"   - {size_type}: {data['count']}회 ({percentage:.1f}%) 평균 ${avg_value:.2f}")
            
            # 박스권 효율성 분석
            if 'box_analysis' in stats:
                box = stats['box_analysis']
                print(f"\n📦 박스권 효율성 분석:")
                print(f"   - 박스 내 거래: {box['box_efficiency']*100:.1f}%")
                print(f"   - 저항선 터치: {box['upper_touches']}회")
                print(f"   - 지지선 터치: {box['lower_touches']}회")
                print(f"   - 평균 박스 위치: {box['avg_position']:.1f}%")
                
                # 박스권 효율성 평가
                if box['box_efficiency'] > 0.8:
                    print(f"   - 평가: 🟢 박스권 매우 잘 유지됨!")
                elif box['box_efficiency'] > 0.6:
                    print(f"   - 평가: 🟡 박스권 양호하게 유지됨")
                else:
                    print(f"   - 평가: 🔴 박스권 이탈 빈번")
            
            # 차트 구성 요소 설명
            print(f"\n🎨 차트 구성 요소:")
            print(f"   - 🔵 파란선: SPSI 가격 변화")
            print(f"   - 🔴 빨간 점선: 저항선 (상한)")
            print(f"   - 🟢 초록 점선: 지지선 (하한)")
            print(f"   - 🟡 노란 영역: 박스권 범위")
            print(f"   - 🟢 삼각형: 매수 주문 (크기별 진하기)")
            print(f"   - 🔴 역삼각형: 매도 주문 (크기별 진하기)")
            
        except Exception as e:
            print(f"❌ 박스권 차트 생성 오류: {e}")
            logger.error(f"박스권 차트 생성 오류: {e}")

    def test_optimal_box_trade(self):
        """1회 적정용량 박스권 거래 테스트"""
        print("📦 1회 적정용량 박스권 거래 테스트 실행...")
        
        # 거래 전 상태
        before_balance = self.get_account_balance()
        current_price = self.get_reference_price()
        
        if before_balance and current_price:
            print(f"\n📊 거래 전 상태:")
            print(f"   - USDT: ${before_balance['usdt']:.2f}")
            print(f"   - SPSI: {before_balance['spsi']:,.0f}")
            print(f"   - 현재 가격: ${current_price:.6f}")
            
            if self.box_upper_bound and self.box_lower_bound:
                print(f"   - 박스범위: ${self.box_lower_bound:.6f} ~ ${self.box_upper_bound:.6f}")
                print(f"   - 박스위치: {self.current_box_position*100:.1f}%")
        
        # 테스트 실행
        result = self.execute_massive_box_cycle()
        
        if result:
            print("\n✅ 적정용량 박스권 거래 테스트 성공!")
            print("🎯 실제 적정용량 주문이 박스권 전략으로 배치되었습니다.")
            print("📊 차트에 박스권 데이터가 추가되었습니다.")
            
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
            
            # 박스권 상태
            if self.box_upper_bound and self.box_lower_bound:
                current_price_new = self.get_reference_price()
                if current_price_new:
                    print(f"\n📦 박스권 상태:")
                    print(f"   - 새로운 위치: {self.current_box_position*100:.1f}%")
                    print(f"   - 박스 유지 점수: {self.box_maintenance_score:.1f}")
                    
                    if self.current_box_position > 0.8:
                        print(f"   - 🔴 저항선 근처: 다음 거래는 매도 압력 예상")
                    elif self.current_box_position < 0.2:
                        print(f"   - 🟢 지지선 근처: 다음 거래는 매수 압력 예상")
                    else:
                        print(f"   - 🔵 박스권 내부: 균형 거래 유지")
            
            print("\n🧹 테스트 주문 정리를 원하시면 메뉴 6번을 실행하세요.")
            print("📊 박스권 차트 확인을 원하시면 메뉴 7번을 실행하세요.")
            return True
        else:
            print("\n❌ 적정용량 박스권 거래 테스트 실패!")
            return False

def main():
    print("📦 적정용량 박스권 LBank 자가매매 시스템")
    print("🎯 특징: 박스권 유지 + 적정 거래량 + 지지/저항선")
    print("💥 목표: 일정 구간 박스권 + 3만~6만 SPSI 거래량")
    
    # matplotlib 설정
    try:
        import matplotlib
        matplotlib.use('Agg')
        print("📊 박스권 차트 기능 활성화됨")
    except ImportError:
        print("⚠️ matplotlib가 설치되지 않았습니다. 차트 기능 비활성화")
    
    # API 키 설정
    API_KEY = os.getenv('LBANK_API_KEY', 'bf850194-8df1-43e0-8254-a32e9ce87005')
    API_SECRET = os.getenv('LBANK_API_SECRET', 'D3602ED02A781CD551C6F123862348C7')
    
    if not API_KEY or not API_SECRET:
        print("❌ API 키가 설정되지 않았습니다")
        input("Enter를 눌러 종료...")
        return
    
    try:
        print("📡 적정용량 박스권 자가매매 시스템 초기화 중...")
        st = OptimalBoxTradingSystem(API_KEY, API_SECRET)
        
        while True:
            try:
                print("\n" + "="*80)
                print("📦 적정용량 박스권 LBank 자가매매 시스템")
                print("="*80)
                print("🎯 특징: 박스권 유지(±2%) + 적정 거래량(200~20,000)")
                print("📊 결과: 지지/저항선 박스권 + 5분당 3만~6만 SPSI")
                print("🔄 전략: 위치 기반 매수/매도 압력 + 평균회귀")
                print("="*80)
                print("1. 💰 상태 확인 (박스권 + 거래량)")
                print("2. 🧪 시스템 테스트 (API + 박스권 설정)")
                print("3. 📦 박스권 거래 1회 테스트")
                print("4. 🚀 적정용량 박스권 자가매매 시작")
                print("5. ⏹️ 자가매매 중지")
                print("6. 🧹 주문 정리 (미체결 주문 취소)")
                print("7. 📊 박스권 거래 차트 보기")
                print("8. 🎯 박스권 효율성 분석")
                print("0. 🚪 종료")
                
                choice = input("\n선택하세요 (0-8): ").strip()
                
                if choice == '1':
                    st.get_status()
                    
                elif choice == '2':
                    print("\n🧪 시스템 테스트 중...")
                    
                    balance = st.get_account_balance()
                    price = st.get_reference_price()
                    
                    if balance and price:
                        print("✅ API 연결 성공")
                        print(f"✅ 잔고 조회 성공: USDT ${balance['usdt']:.2f}, SPSI {balance['spsi']:,.0f}")
                        print(f"✅ 가격 조회 성공: ${price:.6f}")
                        
                        # 박스권 설정 테스트
                        if not st.box_upper_bound:
                            st.setup_initial_box_range(price)
                        
                        print(f"\n📦 박스권 설정:")
                        print(f"   - 저항선: ${st.box_upper_bound:.6f}")
                        print(f"   - 중심가: ${st.box_center_price:.6f}")
                        print(f"   - 지지선: ${st.box_lower_bound:.6f}")
                        print(f"   - 현재위치: {st.current_box_position*100:.1f}%")
                        
                        # 거래 크기 시뮬레이션
                        print(f"\n💥 적정용량 거래 시뮬레이션:")
                        for i in range(3):
                            size_type = st.select_optimal_trade_size()
                            box_strategy = st.select_box_strategy()
                            size_config = st.trade_sizes[size_type]
                            estimated_amount = random.uniform(size_config['min'], size_config['max'])
                            print(f"   {i+1}. 크기: {size_type} ({estimated_amount:,.0f} SPSI), 전략: {box_strategy}")
                        
                        # 총 자산 확인
                        total_value = balance['usdt'] + (balance['spsi'] * price)
                        print(f"\n💰 총 자산: ${total_value:.2f}")
                        
                        if total_value >= 10:
                            print("✅ 적정용량 박스권 자가매매 실행 가능")
                        else:
                            print("❌ 자산 부족 (최소 $10 필요)")
                    else:
                        print("❌ 기본 정보 조회 실패")
                    
                elif choice == '3':
                    print("\n⚠️ 실제 적정용량 박스권 거래가 실행됩니다!")
                    print("📦 박스권 거래 테스트:")
                    print("   - 적정용량 거래량 (200~20,000 SPSI)")
                    print("   - 박스권 전략 (지지/저항 기반)")
                    print("   - 위치 기반 매수/매도 압력")
                    print("   - 평균회귀 거래 전략")
                    print("   - 박스권 유지 시스템")
                    
                    confirm = input("정말 테스트 하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.test_optimal_box_trade()
                    else:
                        print("테스트 취소됨")
                    
                elif choice == '4':
                    print("\n⚠️ 적정용량 박스권 자가매매 시작 주의사항:")
                    print("- 200~20,000 SPSI의 적정용량으로 거래합니다")
                    print("- ±2% 박스권을 유지하며 지지/저항선을 생성합니다")
                    print("- 박스권 위치에 따라 매수/매도 압력을 조절합니다")
                    print("- 평균회귀 전략으로 가격을 박스권 내로 유지합니다")
                    print("- 연속 같은 방향 거래를 방지하여 박스권을 유지합니다")
                    print("- 5분마다 3만~6만 SPSI 거래량을 생성합니다")
                    print("- 언제든지 중지할 수 있습니다")
                    
                    confirm = input("\n정말 시작하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.start_self_trading()
                        if st.running:
                            print("✅ 적정용량 박스권 자가매매 시스템이 시작되었습니다!")
                            print("💡 메뉴 1번으로 박스권 상태를 실시간 확인할 수 있습니다.")
                            print("📊 메뉴 7번으로 지지/저항선 차트를 확인할 수 있습니다.")
                            print("🔴 저항선 근처에서는 매도 압력이 증가합니다.")
                            print("🟢 지지선 근처에서는 매수 압력이 증가합니다.")
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
                    print("📊 박스권 거래 차트 생성 중...")
                    st.show_box_trading_chart()
                    
                elif choice == '8':
                    print("🎯 박스권 효율성 분석...")
                    stats = st.chart.get_enhanced_stats()
                    
                    print(f"\n📦 상세 박스권 분석:")
                    print(f"   - 총 거래 시도: {stats['total_trades']}회")
                    print(f"   - 매수 성공: {stats['total_buys']}회 (🟢)")
                    print(f"   - 매도 성공: {stats['total_sells']}회 (🔴)")
                    print(f"   - 총 거래량: {stats['buy_volume'] + stats['sell_volume']:,.0f} SPSI")
                    
                    # 거래 크기별 분석
                    if 'size_analysis' in stats:
                        print(f"\n💰 거래 크기별 분석:")
                        total_volume = sum(data['total_volume'] for data in stats['size_analysis'].values())
                        sorted_sizes = sorted(stats['size_analysis'].items(), key=lambda x: x[1]['total_volume'], reverse=True)
                        
                        for size_type, data in sorted_sizes:
                            percentage = (data['total_volume'] / total_volume * 100) if total_volume > 0 else 0
                            avg_trade = data['total_volume'] / data['count'] if data['count'] > 0 else 0
                            print(f"   - {size_type}: {data['count']}회, {data['total_volume']:,.0f} SPSI ({percentage:.1f}%)")
                            print(f"     평균: {avg_trade:,.0f} SPSI/거래")
                    
                    # 박스권 효율성 상세 분석
                    if 'box_analysis' in stats:
                        box = stats['box_analysis']
                        print(f"\n📦 박스권 효율성 상세:")
                        print(f"   - 박스 내 거래 비율: {box['box_efficiency']*100:.1f}%")
                        print(f"   - 평균 박스 위치: {box['avg_position']:.1f}%")
                        print(f"   - 위치 변동성: {box['position_volatility']:.2f}%")
                        print(f"   - 저항선 터치: {box['upper_touches']}회")
                        print(f"   - 지지선 터치: {box['lower_touches']}회")
                        
                        # 박스권 건강도 점수 계산
                        health_score = (
                            box['box_efficiency'] * 40 +  # 박스 내 거래 비율 (40점)
                            min(box['upper_touches'] / 5, 1) * 20 +  # 저항선 터치 (20점)
                            min(box['lower_touches'] / 5, 1) * 20 +  # 지지선 터치 (20점)
                            max(0, 1 - box['position_volatility'] / 50) * 20  # 안정성 (20점)
                        ) * 100
                        
                        print(f"\n🏆 박스권 건강도 점수: {health_score:.1f}/100")
                        
                        if health_score > 80:
                            print(f"   - 평가: 🟢 박스권이 매우 건강하게 유지됨!")
                            print(f"   - 상태: 지지선과 저항선이 잘 작동하고 있음")
                        elif health_score > 60:
                            print(f"   - 평가: 🟡 박스권이 양호하게 유지됨")
                            print(f"   - 상태: 대부분의 거래가 박스권 내에서 발생")
                        elif health_score > 40:
                            print(f"   - 평가: 🟠 박스권 유지 보통")
                            print(f"   - 개선: 더 강한 지지/저항 압력 필요")
                        else:
                            print(f"   - 평가: 🔴 박스권 유지 부족")
                            print(f"   - 개선: 박스권 전략 재조정 필요")
                    
                    # 현재 박스권 상태
                    if st.box_upper_bound and st.box_lower_bound:
                        print(f"\n📊 현재 박스권 상태:")
                        print(f"   - 저항선: ${st.box_upper_bound:.6f}")
                        print(f"   - 중심가: ${st.box_center_price:.6f}")
                        print(f"   - 지지선: ${st.box_lower_bound:.6f}")
                        print(f"   - 현재위치: {st.current_box_position*100:.1f}%")
                        print(f"   - 박스 유지 점수: {st.box_maintenance_score:.1f}")
                        
                        # 다음 거래 예측
                        if st.current_box_position > 0.8:
                            print(f"   - 다음 거래 예측: 🔴 매도 압력 (저항선 근처)")
                        elif st.current_box_position < 0.2:
                            print(f"   - 다음 거래 예측: 🟢 매수 압력 (지지선 근처)")
                        elif 0.4 <= st.current_box_position <= 0.6:
                            print(f"   - 다음 거래 예측: 🔵 균형 거래 (박스 중앙)")
                        else:
                            print(f"   - 다음 거래 예측: 🟡 편향 거래 (중간 지역)")
                    
                    # 거래량 목표 달성률
                    if st.total_volume_today > 0:
                        daily_target = (st.min_volume_per_5min + st.max_volume_per_5min) / 2 * 12 * 8  # 8시간 기준
                        achievement_rate = (st.total_volume_today / daily_target) * 100
                        print(f"\n🎯 거래량 목표 달성률:")
                        print(f"   - 오늘 거래량: {st.total_volume_today:,.0f} SPSI")
                        print(f"   - 일일 목표: {daily_target:,.0f} SPSI (8시간 기준)")
                        print(f"   - 달성률: {achievement_rate:.1f}%")
                        
                        if achievement_rate > 100:
                            print(f"   - 상태: 🟢 목표 초과 달성!")
                        elif achievement_rate > 80:
                            print(f"   - 상태: 🟡 목표 근접")
                        else:
                            print(f"   - 상태: 🔴 목표 미달")
                
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