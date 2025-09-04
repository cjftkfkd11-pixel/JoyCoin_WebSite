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
        self.volume_history = deque(500)
        self.balance_history = deque(maxlen=500)
        self.trade_history = deque(maxlen=300)
        self.buy_orders = deque(maxlen=300)
        self.sell_orders = deque(maxlen=300)
        
        # 실시간 통계
        self.total_buys = 0
        self.total_sells = 0
        self.total_buy_volume = 0
        self.total_sell_volume = 0
        
        # 거래 패턴 추적
        self.recent_trade_sizes = deque(maxlen=100)
        self.recent_price_impacts = deque(maxlen=100)
        self.price_momentum = deque(maxlen=30)
        self.mode_history = deque(maxlen=50)  # 모드 변화 기록
        
    def add_price_data(self, price: float, volume: float = 0):
        """가격 데이터 추가"""
        timestamp = datetime.now()
        self.price_history.append({
            'time': timestamp,
            'price': price,
            'volume': volume
        })
        
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
                
            self.recent_trade_sizes.append({
                'amount': amount,
                'value': amount * price,
                'type': trade_type,
                'size_type': trade_size_type
            })
    
    def add_mode_data(self, mode: str, price: float, spsi_balance: float):
        """모드 변화 데이터 추가"""
        self.mode_history.append({
            'time': datetime.now(),
            'mode': mode,
            'price': price,
            'spsi_balance': spsi_balance
        })
    
    def plot_growth_chart(self, save_path: str = None):
        """🔥 성장 모드 차트 생성"""
        if len(self.price_history) < 2:
            print("⚠️ 가격 데이터 부족")
            return
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 12))
        
        # 1. 🔥 가격 상승 차트 + 모드 표시
        times = [d['time'] for d in self.price_history]
        prices = [d['price'] for d in self.price_history]
        
        ax1.plot(times, prices, 'b-', linewidth=3, label='SPSI 가격')
        
        # 모드별 배경색
        if self.mode_history:
            for i, mode_data in enumerate(self.mode_history):
                if i > 0:
                    prev_time = self.mode_history[i-1]['time']
                    curr_time = mode_data['time']
                    if mode_data['mode'] == 'growth':
                        ax1.axvspan(prev_time, curr_time, alpha=0.2, color='green', label='성장 모드')
                    else:
                        ax1.axvspan(prev_time, curr_time, alpha=0.2, color='blue', label='균형 모드')
        
        # 거래 포인트
        if self.buy_orders:
            buy_times = [d['time'] for d in self.buy_orders]
            buy_prices = [d['price'] for d in self.buy_orders]
            ax1.scatter(buy_times, buy_prices, color='green', s=50, alpha=0.7, marker='^', label='매수')
                
        if self.sell_orders:
            sell_times = [d['time'] for d in self.sell_orders]
            sell_prices = [d['price'] for d in self.sell_orders]
            ax1.scatter(sell_times, sell_prices, color='red', s=50, alpha=0.7, marker='v', label='매도')
        
        ax1.set_title('🚀 점진적 가격 상승 + 거래 모드', fontsize=16, fontweight='bold')
        ax1.set_ylabel('가격 (USDT)', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. SPSI 잔고 변화
        if self.balance_history:
            balance_times = [d['time'] for d in self.balance_history]
            spsi_balances = [d['spsi'] for d in self.balance_history]
            
            ax2.plot(balance_times, spsi_balances, 'orange', linewidth=3, label='SPSI 잔고')
            ax2.fill_between(balance_times, spsi_balances, alpha=0.3, color='orange')
            
            # 위험선 표시
            if spsi_balances:
                min_spsi = min(spsi_balances)
                max_spsi = max(spsi_balances)
                danger_line = min_spsi + (max_spsi - min_spsi) * 0.2
                ax2.axhline(y=danger_line, color='red', linestyle='--', alpha=0.7, label='위험선 (20%)')
            
            ax2.set_title('🪙 SPSI 잔고 변화 (코인 보유량)', fontsize=16, fontweight='bold')
            ax2.set_ylabel('SPSI 개수', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # 3. 거래량 시간별 분포
        if self.recent_trade_sizes:
            recent_times = list(range(len(self.recent_trade_sizes)))
            volumes = [t['amount'] for t in self.recent_trade_sizes]
            colors = ['green' if t['type'] == 'buy' else 'red' for t in self.recent_trade_sizes]
            
            ax3.bar(recent_times, volumes, color=colors, alpha=0.7)
            ax3.set_title('📊 거래량 분포 (최근 100회)', fontsize=16, fontweight='bold')
            ax3.set_ylabel('거래량 (SPSI)', fontsize=12)
            ax3.set_xlabel('거래 순서', fontsize=12)
            ax3.grid(True, alpha=0.3)
            
            # 목표선
            target_min = 3000  # 5분에 3만이면 회당 3천
            target_max = 6000  # 5분에 6만이면 회당 6천
            ax3.axhline(y=target_min, color='blue', linestyle='--', alpha=0.7, label=f'목표 최소: {target_min}')
            ax3.axhline(y=target_max, color='blue', linestyle='--', alpha=0.7, label=f'목표 최대: {target_max}')
            ax3.legend()
        
        # 4. 매수/매도 균형 추이
        if len(self.recent_trade_sizes) > 20:
            window = 20
            balance_ratios = []
            times_window = []
            
            for i in range(window, len(self.recent_trade_sizes)):
                recent_window = self.recent_trade_sizes[i-window:i]
                buy_vol = sum(t['amount'] for t in recent_window if t['type'] == 'buy')
                sell_vol = sum(t['amount'] for t in recent_window if t['type'] == 'sell')
                total_vol = buy_vol + sell_vol
                
                if total_vol > 0:
                    buy_ratio = buy_vol / total_vol * 100
                    balance_ratios.append(buy_ratio)
                    times_window.append(i)
            
            if balance_ratios:
                ax4.plot(times_window, balance_ratios, 'purple', linewidth=3, label='매수 비율')
                ax4.axhline(y=50, color='black', linestyle='-', alpha=0.5, label='균형선 (50%)')
                ax4.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='매수 과다 (70%)')
                ax4.axhline(y=30, color='red', linestyle='--', alpha=0.7, label='매도 과다 (30%)')
                
                ax4.set_title('⚖️ 매수/매도 균형 추이', fontsize=16, fontweight='bold')
                ax4.set_ylabel('매수 비율 (%)', fontsize=12)
                ax4.set_xlabel('거래 순서', fontsize=12)
                ax4.set_ylim(0, 100)
                ax4.legend()
                ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 성장 모드 차트 저장됨: {save_path}")
        
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
                'volatility_score': np.std(self.recent_price_impacts) * 100
            }
        
        # 균형 분석
        if self.total_buy_volume > 0 or self.total_sell_volume > 0:
            total_volume = self.total_buy_volume + self.total_sell_volume
            stats['balance_analysis'] = {
                'buy_ratio': self.total_buy_volume / total_volume * 100 if total_volume > 0 else 50,
                'sell_ratio': self.total_sell_volume / total_volume * 100 if total_volume > 0 else 50,
                'volume_imbalance': abs(self.total_buy_volume - self.total_sell_volume),
                'count_imbalance': abs(self.total_buys - self.total_sells)
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

class SmartOrderManager:
    """🎯 스마트 주문 관리 시스템 - 매수5개+매도5개 유지"""
    
    def __init__(self, trading_system):
        self.trading_system = trading_system
        self.max_buy_orders = 5
        self.max_sell_orders = 5
        self.max_total_orders = 10
        
        # 주문 정리 기준
        self.max_order_age_minutes = 30  # 30분 이상 된 주문 정리
        self.max_price_deviation = 0.02  # 현재가에서 2% 이상 차이나는 주문 정리
        
        # 통계
        self.cleanup_stats = {
            'total_cleanups': 0,
            'orders_canceled': 0,
            'old_orders_canceled': 0,
            'deviation_orders_canceled': 0
        }

    def get_categorized_orders(self, current_price: float = None) -> Dict[str, Any]:
        """📊 주문을 카테고리별로 분류"""
        try:
            open_orders = self.trading_system.get_open_orders()
            
            categorized = {
                'buy_orders': [],
                'sell_orders': [],
                'old_orders': [],
                'deviation_orders': [],
                'total_count': len(open_orders),
                'buy_count': 0,
                'sell_count': 0
            }
            
            current_time = time.time()
            
            for order in open_orders:
                order_type = order.get('type', '').lower()
                order_price = float(order.get('price', 0))
                order_time = order.get('create_time', current_time)
                order_age_minutes = (current_time - order_time) / 60
                
                # 기본 분류
                if order_type == 'buy':
                    categorized['buy_orders'].append(order)
                    categorized['buy_count'] += 1
                elif order_type in ['sell', 'sell_market']:
                    categorized['sell_orders'].append(order)
                    categorized['sell_count'] += 1
                
                # 오래된 주문 체크
                if order_age_minutes > self.max_order_age_minutes:
                    categorized['old_orders'].append(order)
                
                # 가격 편차 체크
                if current_price and order_price > 0:
                    if order_type == 'buy':
                        deviation = (order_price - current_price) / current_price
                        if deviation < -self.max_price_deviation:  # 현재가보다 2% 이상 낮은 매수 주문
                            categorized['deviation_orders'].append(order)
                    elif order_type in ['sell', 'sell_market']:
                        deviation = (order_price - current_price) / current_price
                        if deviation > self.max_price_deviation:  # 현재가보다 2% 이상 높은 매도 주문
                            categorized['deviation_orders'].append(order)
            
            return categorized
            
        except Exception as e:
            print(f"   ❌ 주문 분류 오류: {e}")
            return {
                'buy_orders': [], 'sell_orders': [], 'old_orders': [], 'deviation_orders': [],
                'total_count': 0, 'buy_count': 0, 'sell_count': 0
            }

    def should_cleanup_orders(self, current_price: float = None) -> Dict[str, Any]:
        """🔍 주문 정리 필요성 판단"""
        categorized = self.get_categorized_orders(current_price)
        
        cleanup_needed = {
            'cleanup_required': False,
            'reasons': [],
            'buy_excess': 0,
            'sell_excess': 0,
            'old_count': len(categorized['old_orders']),
            'deviation_count': len(categorized['deviation_orders'])
        }
        
        # 1. 총 주문 개수 초과
        if categorized['total_count'] > self.max_total_orders:
            cleanup_needed['cleanup_required'] = True
            cleanup_needed['reasons'].append(f"총 주문 초과 ({categorized['total_count']} > {self.max_total_orders})")
        
        # 2. 매수 주문 초과
        if categorized['buy_count'] > self.max_buy_orders:
            cleanup_needed['cleanup_required'] = True
            cleanup_needed['buy_excess'] = categorized['buy_count'] - self.max_buy_orders
            cleanup_needed['reasons'].append(f"매수 주문 초과 ({categorized['buy_count']} > {self.max_buy_orders})")
        
        # 3. 매도 주문 초과
        if categorized['sell_count'] > self.max_sell_orders:
            cleanup_needed['cleanup_required'] = True
            cleanup_needed['sell_excess'] = categorized['sell_count'] - self.max_sell_orders
            cleanup_needed['reasons'].append(f"매도 주문 초과 ({categorized['sell_count']} > {self.max_sell_orders})")
        
        # 4. 오래된 주문 존재
        if len(categorized['old_orders']) > 0:
            cleanup_needed['cleanup_required'] = True
            cleanup_needed['reasons'].append(f"오래된 주문 {len(categorized['old_orders'])}개")
        
        # 5. 가격 편차 주문 존재
        if len(categorized['deviation_orders']) > 0:
            cleanup_needed['cleanup_required'] = True
            cleanup_needed['reasons'].append(f"가격 편차 주문 {len(categorized['deviation_orders'])}개")
        
        return cleanup_needed

    def execute_smart_cleanup(self, current_price: float = None, force: bool = False) -> Dict[str, Any]:
        """🧹 스마트 주문 정리 실행"""
        try:
            print(f"   🧹 스마트 주문 정리 시작...")
            
            cleanup_check = self.should_cleanup_orders(current_price)
            
            if not cleanup_check['cleanup_required'] and not force:
                print(f"   ✅ 주문 정리 불필요 (적정 수준)")
                return {'success': True, 'canceled_count': 0, 'reason': 'no_cleanup_needed'}
            
            print(f"   📊 정리 이유:")
            for reason in cleanup_check['reasons']:
                print(f"      - {reason}")
            
            categorized = self.get_categorized_orders(current_price)
            orders_to_cancel = []
            
            # 1. 우선순위 1: 오래된 주문들
            if categorized['old_orders']:
                orders_to_cancel.extend(categorized['old_orders'])
                print(f"   ⏰ 오래된 주문 {len(categorized['old_orders'])}개 선택")
            
            # 2. 우선순위 2: 가격 편차가 큰 주문들
            deviation_orders = [o for o in categorized['deviation_orders'] if o not in orders_to_cancel]
            if deviation_orders:
                orders_to_cancel.extend(deviation_orders)
                print(f"   📉 가격 편차 주문 {len(deviation_orders)}개 선택")
            
            # 3. 우선순위 3: 초과된 매수 주문 (가장 오래된 것부터)
            if cleanup_check['buy_excess'] > 0:
                remaining_buy_orders = [o for o in categorized['buy_orders'] if o not in orders_to_cancel]
                # 생성 시간 기준으로 정렬 (오래된 것부터)
                remaining_buy_orders.sort(key=lambda x: x.get('create_time', 0))
                excess_buy_orders = remaining_buy_orders[:cleanup_check['buy_excess']]
                orders_to_cancel.extend(excess_buy_orders)
                print(f"   🛒 초과 매수 주문 {len(excess_buy_orders)}개 선택")
            
            # 4. 우선순위 4: 초과된 매도 주문 (가장 오래된 것부터)
            if cleanup_check['sell_excess'] > 0:
                remaining_sell_orders = [o for o in categorized['sell_orders'] if o not in orders_to_cancel]
                # 생성 시간 기준으로 정렬 (오래된 것부터)
                remaining_sell_orders.sort(key=lambda x: x.get('create_time', 0))
                excess_sell_orders = remaining_sell_orders[:cleanup_check['sell_excess']]
                orders_to_cancel.extend(excess_sell_orders)
                print(f"   💰 초과 매도 주문 {len(excess_sell_orders)}개 선택")
            
            # 5. 중복 제거
            unique_orders = []
            seen_order_ids = set()
            for order in orders_to_cancel:
                order_id = order.get('order_id')
                if order_id and order_id not in seen_order_ids:
                    unique_orders.append(order)
                    seen_order_ids.add(order_id)
            
            orders_to_cancel = unique_orders
            
            if not orders_to_cancel:
                print(f"   ✅ 정리할 주문 없음")
                return {'success': True, 'canceled_count': 0, 'reason': 'no_orders_to_cancel'}
            
            print(f"   🎯 총 {len(orders_to_cancel)}개 주문 취소 실행...")
            
            # 6. 실제 주문 취소 실행
            canceled_count = 0
            for i, order in enumerate(orders_to_cancel):
                try:
                    order_id = order.get('order_id')
                    order_type = order.get('type', 'unknown')
                    order_price = float(order.get('price', 0))
                    order_amount = float(order.get('amount', 0))
                    
                    print(f"      {i+1}/{len(orders_to_cancel)}: {order_type} {order_amount:,.0f} @ ${order_price:.6f}")
                    
                    if self.trading_system.cancel_order(order_id):
                        canceled_count += 1
                        
                        # 통계 업데이트
                        if order in categorized['old_orders']:
                            self.cleanup_stats['old_orders_canceled'] += 1
                        if order in categorized['deviation_orders']:
                            self.cleanup_stats['deviation_orders_canceled'] += 1
                        
                        # 주문 리스트에서 제거
                        try:
                            self.trading_system.current_orders.remove(order_id)
                        except ValueError:
                            pass
                    
                    # 연속 요청 부하 방지
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"         ❌ 주문 {order.get('order_id')} 취소 실패: {e}")
            
            # 7. 통계 업데이트
            self.cleanup_stats['total_cleanups'] += 1
            self.cleanup_stats['orders_canceled'] += canceled_count
            
            print(f"   ✅ 스마트 정리 완료: {canceled_count}/{len(orders_to_cancel)}개 취소됨")
            
            # 8. 정리 후 상태 확인
            time.sleep(1)  # 취소 처리 대기
            final_categorized = self.get_categorized_orders(current_price)
            
            print(f"   📊 정리 후 상태:")
            print(f"      - 총 주문: {final_categorized['total_count']}개")
            print(f"      - 매수 주문: {final_categorized['buy_count']}개 (목표: ≤{self.max_buy_orders})")
            print(f"      - 매도 주문: {final_categorized['sell_count']}개 (목표: ≤{self.max_sell_orders})")
            
            return {
                'success': True,
                'canceled_count': canceled_count,
                'final_buy_count': final_categorized['buy_count'],
                'final_sell_count': final_categorized['sell_count'],
                'final_total_count': final_categorized['total_count']
            }
            
        except Exception as e:
            print(f"   💥 스마트 주문 정리 오류: {e}")
            return {'success': False, 'error': str(e)}

    def pre_trade_cleanup(self, current_price: float, trade_type: str) -> bool:
        """🎯 거래 전 사전 정리"""
        try:
            print(f"   🔍 {trade_type} 거래 전 주문 상태 확인...")
            
            categorized = self.get_categorized_orders(current_price)
            
            # 거래 타입별 체크
            if trade_type == 'buy' and categorized['buy_count'] >= self.max_buy_orders:
                print(f"   ⚠️ 매수 주문 한도 도달 ({categorized['buy_count']}/{self.max_buy_orders}) - 사전 정리 필요")
                cleanup_result = self.execute_smart_cleanup(current_price)
                return cleanup_result.get('success', False)
            
            elif trade_type == 'sell' and categorized['sell_count'] >= self.max_sell_orders:
                print(f"   ⚠️ 매도 주문 한도 도달 ({categorized['sell_count']}/{self.max_sell_orders}) - 사전 정리 필요")
                cleanup_result = self.execute_smart_cleanup(current_price)
                return cleanup_result.get('success', False)
            
            elif categorized['total_count'] >= self.max_total_orders:
                print(f"   ⚠️ 총 주문 한도 도달 ({categorized['total_count']}/{self.max_total_orders}) - 사전 정리 필요")
                cleanup_result = self.execute_smart_cleanup(current_price)
                return cleanup_result.get('success', False)
            
            else:
                print(f"   ✅ {trade_type} 주문 가능 ({categorized['buy_count']}B + {categorized['sell_count']}S = {categorized['total_count']})")
                return True
                
        except Exception as e:
            print(f"   ❌ 거래 전 정리 체크 오류: {e}")
            return False

class SmartGrowthTradingSystem:
    """🔥 스마트 성장 거래 시스템 - 점진적 상승 + 균형 관리 + 스마트 주문 관리"""
    
    BASE_URL = "https://api.lbank.info/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.running = False
        self.trading_thread = None
        
        # 거래 설정
        self.symbol = "spsi_usdt"
        
        # 🔥 목표 거래량 설정 (5분에 3만~6만)
        self.min_volume_per_5min = 30000
        self.max_volume_per_5min = 60000
        self.trade_interval_base = 30  # 30초마다
        
        # 🔥 거래 크기 설정 (5분에 10회 거래 기준)
        self.trade_sizes = {
            'micro': {'min': 1000, 'max': 3000, 'probability': 0.2},     # 20%
            'small': {'min': 3000, 'max': 6000, 'probability': 0.3},     # 30%
            'medium': {'min': 6000, 'max': 10000, 'probability': 0.3},   # 30%
            'large': {'min': 10000, 'max': 15000, 'probability': 0.15},  # 15%
            'huge': {'min': 15000, 'max': 20000, 'probability': 0.05}    # 5%
        }
        
        # 🔥 모드 시스템
        self.current_mode = "growth"  # growth(성장) 또는 balance(균형)
        self.mode_switch_threshold = 0.7  # SPSI 잔고 70% 이하시 성장모드
        self.growth_mode_duration = 0  # 성장모드 지속 시간
        self.max_growth_duration = 86400  # 최대 24시간 성장모드
        
        # 🔥 가격 상승 설정
        self.target_growth_rate = 0.001  # 0.1% 상승/시간 목표
        self.aggressive_growth_rate = 0.002  # 0.2% 공격적 상승
        self.last_price_update = time.time()
        self.accumulated_growth = 0.0
        
        # 🔥 균형 관리 설정
        self.critical_spsi_ratio = 0.3  # SPSI 30% 이하시 위험
        self.critical_usdt_ratio = 0.3  # USDT 30% 이하시 위험
        self.force_buy_threshold = 0.2  # SPSI 20% 이하시 강제 매수
        self.force_sell_threshold = 0.2  # USDT 20% 이하시 강제 매도
        
        # 가격 전략
        self.price_strategies = {
            'aggressive_buy': {'probability': 0.4},   # 40% - 공격적 매수
            'normal_buy': {'probability': 0.3},       # 30% - 일반 매수
            'balanced': {'probability': 0.2},         # 20% - 균형 거래
            'conservative_sell': {'probability': 0.1} # 10% - 보수적 매도
        }
        
        # 기본 설정
        self.min_order_size = 1000
        self.min_trade_value_usd = 2.0
        self.max_trade_value_usd = 100.0
        
        self.base_price = None
        self.current_orders = []
        
        # 통계
        self.total_volume_today = 0
        self.total_trades_today = 0
        self.total_fees_paid = 0.0
        self.successful_buys = 0
        self.successful_sells = 0
        
        # 🔥 모드별 통계
        self.mode_stats = {
            'growth_time': 0,
            'balance_time': 0,
            'forced_buys': 0,
            'forced_sells': 0,
            'price_growth_achieved': 0.0
        }
        
        # 패턴별 통계
        self.pattern_stats = {
            'micro': 0, 'small': 0, 'medium': 0, 'large': 0, 'huge': 0,
            'aggressive_buy': 0, 'normal_buy': 0, 'balanced': 0, 'conservative_sell': 0
        }
        
        # 시스템 구성 요소들
        self.chart = TradingChart()
        self.response_handler = SafeAPIResponseHandler()
        
        # 🎯 스마트 주문 관리자 추가
        self.order_manager = SmartOrderManager(self)
        
        print("🚀 스마트 성장 거래 시스템 초기화 완료")
        print(f"📈 목표 거래량: {self.min_volume_per_5min:,} ~ {self.max_volume_per_5min:,} SPSI/5분")
        print(f"🎲 거래 크기: 1,000 ~ 20,000 SPSI (5단계)")
        print(f"🔄 모드: 성장 모드(SPSI 복구) ↔ 균형 모드(박스권)")
        print(f"📈 성장률: 시간당 {self.target_growth_rate*100:.1f}% 상승")
        print(f"🎯 주문 관리: 매수 {self.order_manager.max_buy_orders}개 + 매도 {self.order_manager.max_sell_orders}개 = 총 {self.order_manager.max_total_orders}개")
        logger.info("스마트 성장 거래 시스템 초기화 완료")

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
                logger.info(f"기준 가격 설정: ${self.base_price:.6f}")
            
            return market_price
            
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

    def check_order_status(self, order_id: str) -> Optional[Dict]:
        """주문 상태 확인"""
        try:
            endpoint = "/orders_info.do"
            params = {
                'symbol': self.symbol,
                'order_id': str(order_id)
            }
            
            response = self._make_request('POST', endpoint, params, signed=True, silent=True)
            
            if response and response.get("success"):
                data = response.get("data", {})
                orders = self.response_handler.safe_get(data, 'orders', [])
                
                if orders and len(orders) > 0:
                    order_info = orders[0]
                    status = self.response_handler.safe_get(order_info, 'status', 0)
                    
                    # LBank 주문 상태: 0=미체결, 1=부분체결, 2=완전체결, -1=취소됨
                    if status == 2:
                        return {'status': 'filled', 'info': order_info}
                    elif status == 1:
                        return {'status': 'partial', 'info': order_info}
                    elif status == 0:
                        return {'status': 'open', 'info': order_info}
                    else:
                        return {'status': 'cancelled', 'info': order_info}
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ 주문 상태 확인 오류: {e}")
            return None

    # 🚀 향상된 매수 관련 메서드들 추가
    def calculate_aggressive_buy_price(self, current_price: float, mode: str, urgency: str) -> float:
        """🔥 공격적 매수 가격 계산 - 체결률 최대화"""
        try:
            # 호가창 분석을 위한 추가 스프레드
            base_spread = 0.002  # 기본 0.2%
            
            if mode == 'emergency_buy':
                # 긴급 매수 - 확실한 체결을 위해 높은 가격
                aggressive_spread = random.uniform(0.008, 0.015)  # 0.8-1.5% 높게
                target_price = current_price * (1 + aggressive_spread)
                print(f"      🚨 긴급매수 가격: +{aggressive_spread*100:.2f}%")
                
            elif mode == 'growth':
                if urgency == 'high':
                    # 높은 긴급도 - 체결 우선
                    aggressive_spread = random.uniform(0.005, 0.012)  # 0.5-1.2%
                    target_price = current_price * (1 + aggressive_spread)
                    print(f"      📈 고긴급매수: +{aggressive_spread*100:.2f}%")
                else:
                    # 중간 긴급도
                    aggressive_spread = random.uniform(0.003, 0.008)  # 0.3-0.8%
                    target_price = current_price * (1 + aggressive_spread)
                    print(f"      📈 성장매수: +{aggressive_spread*100:.2f}%")
            else:
                # 균형 모드 - 적당한 프리미엄
                aggressive_spread = random.uniform(0.002, 0.005)  # 0.2-0.5%
                target_price = current_price * (1 + aggressive_spread)
                print(f"      ⚖️ 균형매수: +{aggressive_spread*100:.2f}%")
            
            return round(target_price, 6)
            
        except Exception as e:
            print(f"   ❌ 공격적 매수 가격 계산 오류: {e}")
            # 안전한 기본값 - 현재가의 1% 위
            return round(current_price * 1.01, 6)

    def get_market_depth_adjustment(self, current_price: float) -> float:
        """호가창 깊이를 고려한 가격 조정"""
        try:
            # 거래량이 적은 시간대는 더 공격적으로
            current_hour = datetime.now().hour
            if 2 <= current_hour <= 6:  # 새벽 시간대
                return 0.008  # 0.8% 추가 프리미엄
            elif 9 <= current_hour <= 11 or 21 <= current_hour <= 23:  # 활발한 시간
                return 0.003  # 0.3% 적당한 프리미엄
            else:
                return 0.005  # 0.5% 기본 프리미엄
                
        except Exception as e:
            return 0.005

    def analyze_trading_feasibility(self, balance: Dict[str, float], current_price: float) -> Dict[str, Any]:
        """🔍 거래 실행 가능성 상세 분석"""
        try:
            analysis = {
                'can_buy': False,
                'can_sell': False,
                'max_buy_amount': 0,
                'max_sell_amount': 0,
                'recommended_buy_amount': 0,
                'recommended_sell_amount': 0,
                'usdt_utilization': 0,
                'spsi_utilization': 0,
                'warnings': []
            }
            
            # USDT 잔고 분석
            available_usdt = balance['usdt'] * 0.95  # 5% 버퍼
            min_trade_value = 2.0  # 최소 거래 금액
            
            if available_usdt >= min_trade_value:
                analysis['can_buy'] = True
                analysis['max_buy_amount'] = (available_usdt / current_price) * 0.9  # 10% 추가 버퍼
                
                # 권장 매수량 (단계별)
                if available_usdt >= 100:  # $100 이상
                    analysis['recommended_buy_amount'] = random.uniform(8000, 15000)
                    analysis['usdt_utilization'] = 0.3  # 30% 활용
                elif available_usdt >= 50:  # $50 이상
                    analysis['recommended_buy_amount'] = random.uniform(5000, 10000)
                    analysis['usdt_utilization'] = 0.4  # 40% 활용
                elif available_usdt >= 20:  # $20 이상
                    analysis['recommended_buy_amount'] = random.uniform(3000, 6000)
                    analysis['usdt_utilization'] = 0.5  # 50% 활용
                elif available_usdt >= 5:  # $5 이상
                    analysis['recommended_buy_amount'] = random.uniform(1000, 3000)
                    analysis['usdt_utilization'] = 0.6  # 60% 활용
                else:
                    analysis['recommended_buy_amount'] = available_usdt / current_price * 0.8
                    analysis['usdt_utilization'] = 0.8  # 80% 활용
                    analysis['warnings'].append(f"USDT 잔고 부족: ${available_usdt:.2f}")
            else:
                analysis['warnings'].append(f"매수 불가: USDT ${available_usdt:.2f} < ${min_trade_value}")
            
            # SPSI 잔고 분석
            available_spsi = balance['spsi'] * 0.95  # 5% 버퍼
            min_spsi_amount = 1000  # 최소 SPSI 거래량
            
            if available_spsi >= min_spsi_amount:
                analysis['can_sell'] = True
                analysis['max_sell_amount'] = available_spsi * 0.9  # 10% 추가 버퍼
                
                # 권장 매도량
                if available_spsi >= 50000:  # 5만 이상
                    analysis['recommended_sell_amount'] = random.uniform(8000, 15000)
                    analysis['spsi_utilization'] = 0.2  # 20% 활용
                elif available_spsi >= 20000:  # 2만 이상
                    analysis['recommended_sell_amount'] = random.uniform(5000, 10000)
                    analysis['spsi_utilization'] = 0.3  # 30% 활용
                elif available_spsi >= 10000:  # 1만 이상
                    analysis['recommended_sell_amount'] = random.uniform(3000, 6000)
                    analysis['spsi_utilization'] = 0.4  # 40% 활용
                else:
                    analysis['recommended_sell_amount'] = available_spsi * 0.5
                    analysis['spsi_utilization'] = 0.5  # 50% 활용
                    analysis['warnings'].append(f"SPSI 잔고 부족: {available_spsi:,.0f}")
            else:
                analysis['warnings'].append(f"매도 불가: SPSI {available_spsi:,.0f} < {min_spsi_amount}")
            
            # 최종 권장량을 최대량으로 제한
            analysis['recommended_buy_amount'] = min(
                analysis['recommended_buy_amount'], 
                analysis['max_buy_amount']
            )
            analysis['recommended_sell_amount'] = min(
                analysis['recommended_sell_amount'], 
                analysis['max_sell_amount']
            )
            
            return analysis
            
        except Exception as e:
            print(f"   ❌ 거래 실행 가능성 분석 오류: {e}")
            return {
                'can_buy': False, 'can_sell': False, 'warnings': [str(e)]
            }

    def execute_smart_buy_with_retry(self, current_price: float, balance: Dict[str, float], 
                                   mode: str, urgency: str, max_retries: int = 3) -> Dict[str, Any]:
        """🔄 재시도 로직이 있는 스마트 매수"""
        
        for attempt in range(max_retries):
            try:
                print(f"   🎯 매수 시도 {attempt + 1}/{max_retries}")
                
                # 거래 실행 가능성 분석
                feasibility = self.analyze_trading_feasibility(balance, current_price)
                
                if not feasibility['can_buy']:
                    print(f"   ❌ 매수 불가능:")
                    for warning in feasibility['warnings']:
                        print(f"      - {warning}")
                    return {'success': False, 'reason': 'insufficient_balance'}
                
                # 시도별 가격 조정 (재시도할수록 더 공격적으로)
                price_multiplier = 1.0 + (attempt * 0.005)  # 시도할 때마다 0.5%씩 더 높게
                
                # 매수량 결정 (재시도시 조금씩 줄임)
                amount_multiplier = 1.0 - (attempt * 0.1)  # 시도할 때마다 10%씩 줄임
                buy_amount = feasibility['recommended_buy_amount'] * amount_multiplier
                
                if buy_amount < 1000:  # 최소량 보장
                    buy_amount = min(1000, feasibility['max_buy_amount'])
                
                # 가격 계산
                base_price = self.calculate_aggressive_buy_price(current_price, mode, urgency)
                buy_price = round(base_price * price_multiplier, 6)
                
                # 필요 자금 확인
                required_usdt = buy_amount * buy_price
                if required_usdt > balance['usdt'] * 0.95:
                    # 자금 부족시 금액 조정
                    buy_amount = (balance['usdt'] * 0.9) / buy_price
                    print(f"      💰 매수량 조정: {buy_amount:,.0f} SPSI (자금 한도)")
                
                print(f"      🛒 매수 시도: {buy_amount:,.0f} SPSI @ ${buy_price:.6f}")
                print(f"      📈 현재가 대비: +{((buy_price/current_price-1)*100):.2f}%")
                print(f"      💵 필요 자금: ${required_usdt:.2f}")
                
                # 주문 실행
                order_id = self.enhanced_place_order('buy', buy_amount, buy_price)
                
                if order_id:
                    print(f"      ✅ 매수 주문 성공! (시도 {attempt + 1})")
                    
                    # 즉시 체결 확인
                    time.sleep(2)
                    order_status = self.check_order_status(order_id)
                    
                    result = {
                        'success': True,
                        'order_id': order_id,
                        'amount': buy_amount,
                        'price': buy_price,
                        'attempt': attempt + 1,
                        'filled': order_status and order_status.get('status') == 'filled'
                    }
                    
                    if result['filled']:
                        print(f"      🎉 즉시 체결 성공!")
                    else:
                        print(f"      ⏳ 주문 대기 중...")
                    
                    return result
                else:
                    print(f"      ❌ 매수 주문 실패 (시도 {attempt + 1})")
                    if attempt < max_retries - 1:
                        print(f"      ⏳ 3초 후 재시도...")
                        time.sleep(3)
                        # 잔고 새로고침
                        balance = self.get_account_balance() or balance
                
            except Exception as e:
                print(f"   💥 매수 시도 {attempt + 1} 오류: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        print(f"   ❌ {max_retries}회 시도 모두 실패")
        return {'success': False, 'reason': 'max_retries_exceeded'}

    def enhanced_place_order(self, side: str, amount: float, price: float) -> Optional[str]:
        """🎯 향상된 주문 등록 (사전 정리 포함)"""
        try:
            current_price = self.get_reference_price()
            
            # 1. 거래 전 사전 정리
            if not self.order_manager.pre_trade_cleanup(current_price, side):
                print(f"   ⚠️ 사전 정리 실패 - {side} 주문 진행")
            
            # 2. 기존 주문 등록 로직
            order_id = self.place_order(side, amount, price)
            
            if order_id:
                print(f"   ✅ {side} 주문 성공 (ID: {order_id})")
                
                # 3. 주문 후 상태 확인
                time.sleep(0.5)
                categorized = self.order_manager.get_categorized_orders(current_price)
                print(f"   📊 현재 주문: {categorized['buy_count']}B + {categorized['sell_count']}S = {categorized['total_count']}개")
                
            return order_id
            
        except Exception as e:
            print(f"   ❌ 향상된 주문 등록 오류: {e}")
            return None

    # 기존 메서드들 계속...
    def analyze_balance_status(self, balance: Dict[str, float], current_price: float) -> Dict[str, Any]:
        """🔥 잔고 상태 분석 및 모드 결정"""
        try:
            usdt_value = balance['usdt']
            spsi_value = balance['spsi'] * current_price
            total_value = usdt_value + spsi_value
            
            if total_value <= 0:
                return {'mode': 'error', 'reason': '총 자산이 0'}
            
            usdt_ratio = usdt_value / total_value
            spsi_ratio = spsi_value / total_value
            
            # 🔥 모드 결정 로직
            if spsi_ratio < self.force_buy_threshold:
                # SPSI 20% 이하 - 위험! 강제 매수 모드
                recommended_mode = "emergency_buy"
                urgency = "critical"
            elif spsi_ratio < self.mode_switch_threshold:
                # SPSI 70% 이하 - 성장 모드 (매수 우선)
                recommended_mode = "growth"
                urgency = "high" if spsi_ratio < 0.5 else "medium"
            elif usdt_ratio < self.force_sell_threshold:
                # USDT 20% 이하 - 강제 매도 모드
                recommended_mode = "emergency_sell"
                urgency = "critical"
            else:
                # 균형 상태 - 균형 모드
                recommended_mode = "balance"
                urgency = "low"
            
            return {
                'usdt_ratio': usdt_ratio,
                'spsi_ratio': spsi_ratio,
                'total_value': total_value,
                'recommended_mode': recommended_mode,
                'urgency': urgency,
                'spsi_shortage': max(0, self.mode_switch_threshold - spsi_ratio),
                'usdt_shortage': max(0, self.mode_switch_threshold - usdt_ratio)
            }
            
        except Exception as e:
            print(f"   ❌ 잔고 상태 분석 오류: {e}")
            return {'mode': 'error', 'reason': str(e)}

    def update_trading_mode(self, balance_status: Dict[str, Any], current_price: float, balance: Dict[str, float]):
        """🔥 거래 모드 업데이트"""
        try:
            old_mode = self.current_mode
            recommended_mode = balance_status['recommended_mode']
            urgency = balance_status['urgency']
            
            # 긴급 상황 처리
            if recommended_mode in ['emergency_buy', 'emergency_sell']:
                self.current_mode = recommended_mode
            elif recommended_mode == 'growth':
                self.current_mode = 'growth'
                if old_mode != 'growth':
                    self.growth_mode_duration = 0
            elif recommended_mode == 'balance':
                # 성장 모드에서 균형 모드로 전환 조건
                if (self.current_mode == 'growth' and 
                    balance_status['spsi_ratio'] > self.mode_switch_threshold and
                    self.growth_mode_duration > 3600):  # 최소 1시간 성장 후
                    self.current_mode = 'balance'
                elif self.current_mode not in ['growth', 'emergency_buy', 'emergency_sell']:
                    self.current_mode = 'balance'
            
            # 모드 전환 로깅
            if old_mode != self.current_mode:
                print(f"   🔄 모드 전환: {old_mode} → {self.current_mode}")
                print(f"      - SPSI 비율: {balance_status['spsi_ratio']*100:.1f}%")
                print(f"      - USDT 비율: {balance_status['usdt_ratio']*100:.1f}%")
                print(f"      - 긴급도: {urgency}")
                
                # 차트에 모드 데이터 추가
                self.chart.add_mode_data(self.current_mode, current_price, balance['spsi'])
            
            # 성장 모드 시간 추적
            if self.current_mode == 'growth':
                self.growth_mode_duration += self.trade_interval_base
                self.mode_stats['growth_time'] += self.trade_interval_base
            else:
                self.mode_stats['balance_time'] += self.trade_interval_base
            
        except Exception as e:
            print(f"   ❌ 모드 업데이트 오류: {e}")

    def select_random_trade_size(self) -> str:
        """🎲 랜덤 거래 크기 선택"""
        rand = random.random()
        cumulative = 0
        
        for size_type, config in self.trade_sizes.items():
            cumulative += config['probability']
            if rand <= cumulative:
                return size_type
        
        return 'medium'

    def generate_smart_trade_amount(self, size_type: str, current_price: float, balance: Dict[str, float], balance_status: Dict[str, Any]) -> Dict[str, float]:
        """🔥 스마트 거래량 생성 (모드별 맞춤)"""
        try:
            # 1. 기본 거래량
            size_config = self.trade_sizes[size_type]
            min_amount = size_config['min']
            max_amount = size_config['max']
            base_amount = random.uniform(min_amount, max_amount)
            
            # 2. 🔥 모드별 거래량 및 비율 조정
            mode = self.current_mode
            urgency = balance_status['urgency']
            
            if mode == 'emergency_buy':
                # 긴급 매수 - 매수 100%, 거래량 2배
                buy_ratio = 1.0
                sell_ratio = 0.0
                base_amount *= 2.0
                self.mode_stats['forced_buys'] += 1
                print(f"      - 🚨 긴급 매수 모드: SPSI {balance_status['spsi_ratio']*100:.1f}% 위험!")
                
            elif mode == 'emergency_sell':
                # 긴급 매도 - 매도 100%, 거래량 2배
                buy_ratio = 0.0
                sell_ratio = 1.0
                base_amount *= 2.0
                self.mode_stats['forced_sells'] += 1
                print(f"      - 🚨 긴급 매도 모드: USDT {balance_status['usdt_ratio']*100:.1f}% 위험!")
                
            elif mode == 'growth':
                # 성장 모드 - 매수 우선
                if urgency == 'high':
                    buy_ratio = 0.9
                    sell_ratio = 0.1
                    base_amount *= 1.5
                elif urgency == 'medium':
                    buy_ratio = 0.8
                    sell_ratio = 0.2
                    base_amount *= 1.2
                else:
                    buy_ratio = 0.7
                    sell_ratio = 0.3
                print(f"      - 📈 성장 모드: 매수 우선 ({buy_ratio*100:.0f}:{sell_ratio*100:.0f})")
                
            else:  # balance 모드
                # 균형 모드 - 일반 박스권 거래
                buy_ratio = random.uniform(0.4, 0.6)
                sell_ratio = 1 - buy_ratio
                print(f"      - ⚖️ 균형 모드: 균형 거래 ({buy_ratio*100:.0f}:{sell_ratio*100:.0f})")
            
            # 3. 잔고 제한 적용
            available_usdt = balance['usdt'] * 0.9
            available_spsi = balance['spsi'] * 0.9
            
            max_buy_amount = available_usdt / current_price if current_price > 0 else 0
            max_sell_amount = available_spsi
            
            buy_amount = min(base_amount * buy_ratio, max_buy_amount)
            sell_amount = min(base_amount * sell_ratio, max_sell_amount)
            
            # 4. 최소값 보장
            if buy_amount < self.min_order_size and buy_ratio > 0:
                buy_amount = min(self.min_order_size, max_buy_amount)
            if sell_amount < self.min_order_size and sell_ratio > 0:
                sell_amount = min(self.min_order_size, max_sell_amount)
            
            return {
                'buy_amount': round(buy_amount, 2),
                'sell_amount': round(sell_amount, 2),
                'size_type': size_type,
                'mode': mode,
                'urgency': urgency,
                'buy_ratio': buy_ratio,
                'sell_ratio': sell_ratio
            }
            
        except Exception as e:
            print(f"   ❌ 스마트 거래량 생성 오류: {e}")
            return {
                'buy_amount': 3000,
                'sell_amount': 3000,
                'size_type': 'medium',
                'mode': 'balance',
                'urgency': 'low',
                'buy_ratio': 0.5,
                'sell_ratio': 0.5
            }

    def calculate_smart_price(self, trade_type: str, current_price: float, mode: str, urgency: str) -> float:
        """🔥 스마트 가격 계산 (모드별 최적화)"""
        try:
            if mode == 'emergency_buy':
                # 긴급 매수 - 현재가보다 높게 (즉시 체결)
                if trade_type == 'buy':
                    spread = random.uniform(0.002, 0.005)  # 0.2-0.5% 높게
                    target_price = current_price * (1 + spread)
                else:
                    # 긴급 매수 모드에서는 매도 안함
                    target_price = current_price * (1 - 0.001)
                    
            elif mode == 'emergency_sell':
                # 긴급 매도 - 현재가보다 낮게 (즉시 체결)
                if trade_type == 'sell':
                    spread = random.uniform(0.002, 0.005)  # 0.2-0.5% 낮게
                    target_price = current_price * (1 - spread)
                else:
                    # 긴급 매도 모드에서는 매수 안함
                    target_price = current_price * (1 + 0.001)
                    
            elif mode == 'growth':
                # 성장 모드 - 가격 상승 유도
                if trade_type == 'buy':
                    # 매수는 현재가보다 높게 (상승 압력)
                    if urgency == 'high':
                        spread = random.uniform(0.001, 0.003)  # 0.1-0.3%
                    else:
                        spread = random.uniform(0.0005, 0.002)  # 0.05-0.2%
                    target_price = current_price * (1 + spread)
                else:
                    # 매도는 현재가보다 약간 높게 (상승 유지)
                    spread = random.uniform(0.0002, 0.001)  # 0.02-0.1%
                    target_price = current_price * (1 + spread)
                    
            else:  # balance 모드
                # 균형 모드 - 일반 박스권 거래
                spread = random.uniform(0.0005, 0.002)  # 0.05-0.2%
                if trade_type == 'buy':
                    target_price = current_price * (1 + spread)
                else:
                    target_price = current_price * (1 - spread)
            
            return round(target_price, 6)
            
        except Exception as e:
            print(f"   ❌ 스마트 가격 계산 오류: {e}")
            # 기본값
            spread = 0.001
            if trade_type == 'buy':
                return round(current_price * (1 + spread), 6)
            else:
                return round(current_price * (1 - spread), 6)

    def execute_enhanced_smart_growth_trade(self, current_price: float, balance: Dict[str, float]) -> Dict[str, Any]:
        """🚀 향상된 스마트 성장 거래 실행 - 매수 문제 해결 + 주문 관리"""
        try:
            print(f"   🚀 향상된 스마트 성장 거래 실행:")
            print(f"      - 현재가: ${current_price:.6f}")
            
            # 1. 심화 잔고 상태 분석
            balance_status = self.analyze_balance_status(balance, current_price)
            feasibility = self.analyze_trading_feasibility(balance, current_price)
            
            # 2. 모드 업데이트
            self.update_trading_mode(balance_status, current_price, balance)
            
            # 3. 거래 파라미터 최적화
            recent_performance = {
                'success_rate': self.successful_buys / max(1, self.successful_buys + self.total_trades_today - self.successful_buys)
            }
            
            results = {
                'buy_success': False,
                'sell_success': False,
                'buy_order_id': None,
                'sell_order_id': None,
                'executed_trades': 0,
                'mode': self.current_mode,
                'urgency': balance_status['urgency']
            }
            
            executed_trades = 0
            
            # 4. 🔥 향상된 매수 실행
            if feasibility['can_buy'] and (
                self.current_mode in ['growth', 'emergency_buy'] or 
                balance_status['urgency'] in ['high', 'critical']
            ):
                print(f"      🛒 향상된 매수 실행...")
                
                buy_result = self.execute_smart_buy_with_retry(
                    current_price, balance, self.current_mode, 
                    balance_status['urgency'], max_retries=3
                )
                
                if buy_result['success']:
                    results['buy_success'] = True
                    results['buy_order_id'] = buy_result['order_id']
                    executed_trades += 1
                    self.successful_buys += 1
                    
                    # 차트에 기록
                    self.chart.add_trade_data(
                        'buy', buy_result['amount'], buy_result['price'], 
                        True, 'enhanced'
                    )
                    
                    print(f"      ✅ 향상된 매수 성공!")
                    print(f"         - 주문ID: {buy_result['order_id']}")
                    print(f"         - 거래량: {buy_result['amount']:,.0f} SPSI")
                    print(f"         - 가격: ${buy_result['price']:.6f}")
                    print(f"         - 시도횟수: {buy_result['attempt']}")
                    
                    # 즉시 체결 확인
                    if buy_result.get('filled'):
                        print(f"         - 상태: 🎉 즉시 체결됨!")
                    else:
                        print(f"         - 상태: ⏳ 체결 대기중...")
                else:
                    print(f"      ❌ 향상된 매수 실패: {buy_result.get('reason', 'unknown')}")
                    
                    # 실패 분석 및 조치
                    if buy_result.get('reason') == 'insufficient_balance':
                        print(f"         💡 조치: 잔고 확인 필요")
                    elif buy_result.get('reason') == 'max_retries_exceeded':
                        print(f"         💡 조치: 가격 전략 재검토 필요")
                    else:
                        print(f"         💡 조치: API 연결 상태 확인")
            else:
                if not feasibility['can_buy']:
                    print(f"      ⚠️ 매수 조건 미충족:")
                    for warning in feasibility.get('warnings', []):
                        print(f"         - {warning}")
                else:
                    print(f"      💡 현재 모드에서 매수 우선순위 낮음")
            
            # 5. 매도 실행 (기존 로직 유지하되 개선)
            if feasibility['can_sell'] and (
                self.current_mode in ['balance', 'emergency_sell'] or
                (self.current_mode == 'growth' and random.random() < 0.3)  # 성장모드에서도 30% 확률로 매도
            ):
                time.sleep(random.uniform(0.5, 2.0))  # 매수 후 잠시 대기
                
                print(f"      💰 매도 실행...")
                
                # 매도량 계산
                sell_amount = feasibility['recommended_sell_amount']
                sell_amount = min(sell_amount, feasibility['max_sell_amount'])
                
                if sell_amount >= 1000:
                    sell_price = self.calculate_smart_price(
                        'sell', current_price, self.current_mode, balance_status['urgency']
                    )
                    
                    print(f"         - 매도량: {sell_amount:,.0f} SPSI")
                    print(f"         - 매도가: ${sell_price:.6f}")
                    
                    sell_order_id = self.enhanced_place_order('sell', sell_amount, sell_price)
                    
                    if sell_order_id:
                        results['sell_success'] = True
                        results['sell_order_id'] = sell_order_id
                        executed_trades += 1
                        self.successful_sells += 1
                        
                        self.chart.add_trade_data('sell', sell_amount, sell_price, True, 'enhanced')
                        print(f"      ✅ 매도 성공!")
                    else:
                        print(f"      ❌ 매도 실패")
                        self.chart.add_trade_data('sell', sell_amount, sell_price, False, 'enhanced')
            
            results['executed_trades'] = executed_trades
            
            # 6. 결과 요약
            if executed_trades > 0:
                # 주문 관리
                if results['buy_order_id']:
                    self.current_orders.append(results['buy_order_id'])
                if results['sell_order_id']:
                    self.current_orders.append(results['sell_order_id'])
                
                # 통계 업데이트
                self.total_trades_today += executed_trades
                
                # 성과 요약
                print(f"   📊 향상된 거래 결과:")
                print(f"      - 실행거래: {executed_trades}회")
                print(f"      - 매수 성공: {'✅' if results['buy_success'] else '❌'}")
                print(f"      - 매도 성공: {'✅' if results['sell_success'] else '❌'}")
                print(f"      - 현재 모드: {self.current_mode}")
                print(f"      - 긴급도: {balance_status['urgency']}")
                
                return results
            else:
                print(f"   ❌ 모든 거래 실패 - 다음 조치:")
                print(f"      1. 잔고 상태 재확인")
                print(f"      2. 가격 전략 조정")
                print(f"      3. 미체결 주문 정리")
                return results
                
        except Exception as e:
            print(f"   💥 향상된 스마트 성장 거래 오류: {e}")
            logger.error(f"향상된 스마트 성장 거래 오류: {e}")
            return {'executed_trades': 0, 'error': str(e)}

    def get_dynamic_interval(self) -> int:
        """🔥 동적 거래 간격 (모드별)"""
        base = self.trade_interval_base
        
        if self.current_mode in ['emergency_buy', 'emergency_sell']:
            # 긴급 모드 - 매우 빠른 거래
            return random.randint(5, 15)
        elif self.current_mode == 'growth':
            # 성장 모드 - 빠른 거래
            return random.randint(base // 2, base)
        else:
            # 균형 모드 - 일반 속도
            return random.randint(base, base * 2)

    def execute_smart_growth_cycle(self) -> bool:
        """🔥 스마트 성장 자가매매 사이클 (향상된 버전)"""
        try:
            print("   🚀 향상된 스마트 성장 자가매매 사이클 시작...")
            
            # 1. 기본 정보 수집
            current_price = self.get_reference_price()
            if not current_price:
                print("   ❌ 현재 가격 조회 실패")
                return False
            
            balance = self.get_account_balance()
            if not balance:
                print("   ❌ 잔고 조회 실패")
                return False
            
            # 2. 스마트 주문 관리
            categorized = self.order_manager.get_categorized_orders(current_price)
            if categorized['total_count'] > self.order_manager.max_total_orders:
                print(f"   🧹 주문 한도 초과 ({categorized['total_count']} > {self.order_manager.max_total_orders}) - 자동 정리...")
                self.order_manager.execute_smart_cleanup(current_price)
                time.sleep(1)
                
                balance = self.get_account_balance()
                if not balance:
                    print("   ❌ 정리 후 잔고 확인 실패")
                    return False
            
            # 3. 최소 자산 확인
            total_value = balance['usdt'] + (balance['spsi'] * current_price)
            if total_value < 5.0:
                print(f"   ❌ 총 자산 부족: ${total_value:.2f} < $5.0")
                return False
            
            # 4. 향상된 스마트 성장 거래 실행
            results = self.execute_enhanced_smart_growth_trade(current_price, balance)
            
            # 5. 결과 평가
            if results['executed_trades'] > 0:
                print(f"   ✅ 향상된 스마트 성장 거래 성공 ({results['executed_trades']} 거래)")
                return True
            else:
                print(f"   ❌ 모든 거래 실패")
                return False
                
        except Exception as e:
            print(f"   💥 향상된 스마트 성장 거래 사이클 오류: {e}")
            logger.error(f"향상된 스마트 성장 거래 사이클 오류: {e}")
            return False

    # 🧹 향상된 주문 정리 메서드
    def enhanced_cleanup_old_orders(self):
        """🧹 향상된 주문 정리 (기존 함수 대체)"""
        try:
            current_price = self.get_reference_price()
            result = self.order_manager.execute_smart_cleanup(current_price, force=True)
            
            if result['success']:
                print(f"✅ 스마트 주문 정리 완료: {result['canceled_count']}개 취소")
                return result['canceled_count']
            else:
                print(f"❌ 스마트 주문 정리 실패")
                return 0
                
        except Exception as e:
            print(f"❌ 향상된 주문 정리 오류: {e}")
            return 0

    # 📊 상세 상태 조회 메서드들
    def show_order_status(self):
        """📊 상세 주문 현황 표시"""
        try:
            current_price = self.get_reference_price()
            categorized = self.order_manager.get_categorized_orders(current_price)
            cleanup_stats = self.order_manager.cleanup_stats
            
            print(f"\n📊 상세 주문 현황:")
            print(f"{'='*50}")
            print(f"💰 현재가: ${current_price:.6f}")
            print(f"📋 총 주문: {categorized['total_count']}개 (한도: {self.order_manager.max_total_orders})")
            print(f"🛒 매수 주문: {categorized['buy_count']}개 (한도: {self.order_manager.max_buy_orders})")
            print(f"💰 매도 주문: {categorized['sell_count']}개 (한도: {self.order_manager.max_sell_orders})")
            print(f"⏰ 오래된 주문: {len(categorized['old_orders'])}개")
            print(f"📉 편차 주문: {len(categorized['deviation_orders'])}개")
            
            # 상태 평가
            if categorized['total_count'] <= self.order_manager.max_total_orders:
                if categorized['buy_count'] <= self.order_manager.max_buy_orders and categorized['sell_count'] <= self.order_manager.max_sell_orders:
                    print(f"✅ 주문 상태: 양호")
                else:
                    print(f"⚠️ 주문 상태: 타입별 초과")
            else:
                print(f"🚨 주문 상태: 총 개수 초과")
            
            # 정리 통계
            print(f"\n🧹 정리 통계:")
            print(f"   - 총 정리 횟수: {cleanup_stats['total_cleanups']}회")
            print(f"   - 취소된 주문: {cleanup_stats['orders_canceled']}개")
            if cleanup_stats['total_cleanups'] > 0:
                avg_per_cleanup = cleanup_stats['orders_canceled'] / cleanup_stats['total_cleanups']
                print(f"   - 회당 평균: {avg_per_cleanup:.1f}개")
            
            # 주문 목록 (최대 10개)
            if categorized['buy_orders']:
                print(f"\n🛒 매수 주문 (최신 5개):")
                for i, order in enumerate(categorized['buy_orders'][:5]):
                    order_price = float(order.get('price', 0))
                    order_amount = float(order.get('amount', 0))
                    price_diff = ((order_price / current_price - 1) * 100) if current_price > 0 else 0
                    print(f"   {i+1}. {order_amount:,.0f} SPSI @ ${order_price:.6f} ({price_diff:+.2f}%)")
            
            if categorized['sell_orders']:
                print(f"\n💰 매도 주문 (최신 5개):")
                for i, order in enumerate(categorized['sell_orders'][:5]):
                    order_price = float(order.get('price', 0))
                    order_amount = float(order.get('amount', 0))
                    price_diff = ((order_price / current_price - 1) * 100) if current_price > 0 else 0
                    print(f"   {i+1}. {order_amount:,.0f} SPSI @ ${order_price:.6f} ({price_diff:+.2f}%)")
            
        except Exception as e:
            print(f"❌ 주문 현황 조회 오류: {e}")

    def diagnose_buy_issues(self):
        """🔧 매수 문제 진단"""
        print("🔧 매수 문제 진단 시작...")
        
        issues_found = []
        recommendations = []
        
        # 1. 기본 연결 테스트
        print("\n1️⃣ API 연결 테스트:")
        balance = self.get_account_balance()
        price = self.get_reference_price()
        
        if not balance:
            issues_found.append("API 잔고 조회 실패")
            recommendations.append("API 키와 시크릿 확인")
        else:
            print(f"   ✅ 잔고 조회 성공")
        
        if not price:
            issues_found.append("가격 조회 실패")
            recommendations.append("네트워크 연결 및 심볼 확인")
        else:
            print(f"   ✅ 가격 조회 성공: ${price:.6f}")
        
        if not balance or not price:
            print("❌ 기본 연결 문제로 진단 중단")
            return
        
        # 2. 잔고 분석
        print("\n2️⃣ 잔고 분석:")
        total_value = balance['usdt'] + (balance['spsi'] * price)
        
        print(f"   💰 총 자산: ${total_value:.2f}")
        print(f"   💵 USDT: ${balance['usdt']:.2f}")
        print(f"   🪙 SPSI: {balance['spsi']:,.0f} (${balance['spsi'] * price:.2f})")
        
        if balance['usdt'] < 5:
            issues_found.append(f"USDT 잔고 부족: ${balance['usdt']:.2f}")
            recommendations.append("최소 $5 이상의 USDT 필요")
        
        if total_value < 10:
            issues_found.append(f"총 자산 부족: ${total_value:.2f}")
            recommendations.append("최소 $10 이상의 총 자산 필요")
        
        # 3. 거래 가능성 분석
        print("\n3️⃣ 거래 가능성 분석:")
        feasibility = self.analyze_trading_feasibility(balance, price)
        
        if feasibility['can_buy']:
            print(f"   ✅ 매수 가능")
            print(f"   💡 최대 매수량: {feasibility['max_buy_amount']:,.0f} SPSI")
            print(f"   🎯 권장 매수량: {feasibility['recommended_buy_amount']:,.0f} SPSI")
        else:
            print(f"   ❌ 매수 불가능")
            for warning in feasibility['warnings']:
                issues_found.append(warning)
        
        # 4. 가격 전략 분석
        print("\n4️⃣ 가격 전략 분석:")
        balance_status = self.analyze_balance_status(balance, price)
        
        test_buy_price = self.calculate_aggressive_buy_price(
            price, balance_status['recommended_mode'], balance_status['urgency']
        )
        
        price_premium = ((test_buy_price / price - 1) * 100)
        
        print(f"   📊 현재가: ${price:.6f}")
        print(f"   📈 예상 매수가: ${test_buy_price:.6f}")
        print(f"   💹 프리미엄: +{price_premium:.2f}%")
        
        if price_premium < 0.1:
            issues_found.append("가격 프리미엄 부족 (체결 어려움)")
            recommendations.append("더 공격적인 가격 설정 필요")
        elif price_premium > 2.0:
            issues_found.append("가격 프리미엄 과다 (비효율적)")
            recommendations.append("가격 전략 조정 필요")
        
        # 5. 미체결 주문 분석
        print("\n5️⃣ 미체결 주문 분석:")
        categorized = self.order_manager.get_categorized_orders(price)
        
        print(f"   📋 총 미체결 주문: {categorized['total_count']}개")
        print(f"   🛒 미체결 매수 주문: {categorized['buy_count']}개")
        
        if categorized['buy_count'] > 10:
            issues_found.append(f"미체결 매수 주문 과다: {categorized['buy_count']}개")
            recommendations.append("주문 정리 후 재시도")
        
        for i, order in enumerate(categorized['buy_orders'][:5]):
            order_price = float(order.get('price', 0))
            order_amount = float(order.get('amount', 0))
            price_diff = ((order_price / price - 1) * 100) if price > 0 else 0
            
            print(f"   📝 주문 {i+1}: {order_amount:,.0f} SPSI @ ${order_price:.6f} ({price_diff:+.2f}%)")
            
            if price_diff < -1.0:
                issues_found.append(f"주문 {i+1} 가격이 너무 낮음 ({price_diff:.1f}%)")
        
        # 6. 진단 결과 출력
        print(f"\n🏥 진단 결과:")
        
        if not issues_found:
            print("   ✅ 매수 시스템 정상")
            print("   💡 추천: 스마트 매수 테스트 실행")
        else:
            print(f"   ⚠️ {len(issues_found)}개 문제 발견:")
            for issue in issues_found:
                print(f"      - {issue}")
            
            print(f"\n💊 개선 방안:")
            for recommendation in recommendations:
                print(f"      - {recommendation}")
        
        # 7. 즉시 개선 가능한 항목 제안
        print(f"\n🚀 즉시 실행 가능한 개선책:")
        
        if categorized['buy_count'] > 5:
            print("   1. 미체결 주문 정리 (메뉴 6번)")
        
        if balance['usdt'] >= 5:
            print("   2. 1회 스마트 매수 테스트 (메뉴 3번)")
        
        if feasibility['can_buy']:
            print("   3. 실시간 모니터링 시작 (메뉴 8번)")
        
        print("   4. 성장 모드 차트 확인 (메뉴 7번)")

    def real_time_buy_monitor(self, duration_minutes: int = 30):
        """🔍 실시간 매수 모니터링 (디버깅용)"""
        print(f"🔍 {duration_minutes}분간 실시간 매수 모니터링 시작...")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        initial_balance = self.get_account_balance()
        if not initial_balance:
            print("❌ 초기 잔고 조회 실패")
            return
        
        print(f"📊 모니터링 시작 잔고:")
        print(f"   - USDT: ${initial_balance['usdt']:.2f}")
        print(f"   - SPSI: {initial_balance['spsi']:,.0f}")
        
        while time.time() < end_time:
            try:
                current_time = datetime.now()
                current_price = self.get_reference_price()
                current_balance = self.get_account_balance()
                
                if not current_price or not current_balance:
                    print(f"⚠️ {current_time.strftime('%H:%M:%S')} - 데이터 조회 실패")
                    time.sleep(10)
                    continue
                
                # 매수 조건 분석
                balance_status = self.analyze_balance_status(current_balance, current_price)
                feasibility = self.analyze_trading_feasibility(current_balance, current_price)
                categorized = self.order_manager.get_categorized_orders(current_price)
                
                print(f"\n⏰ {current_time.strftime('%H:%M:%S')} 상태:")
                print(f"   💰 가격: ${current_price:.6f}")
                print(f"   💳 USDT: ${current_balance['usdt']:.2f}")
                print(f"   🪙 SPSI: {current_balance['spsi']:,.0f}")
                print(f"   📊 SPSI비율: {balance_status['spsi_ratio']*100:.1f}%")
                print(f"   🔄 권장모드: {balance_status['recommended_mode']}")
                print(f"   🛒 매수가능: {'✅' if feasibility['can_buy'] else '❌'}")
                print(f"   📋 주문현황: {categorized['buy_count']}B + {categorized['sell_count']}S = {categorized['total_count']}개")
                
                if feasibility['can_buy']:
                    print(f"   💡 권장매수량: {feasibility['recommended_buy_amount']:,.0f} SPSI")
                    
                    # 테스트 매수가 계산
                    test_price = self.calculate_aggressive_buy_price(
                        current_price, balance_status['recommended_mode'], balance_status['urgency']
                    )
                    print(f"   📈 예상매수가: ${test_price:.6f} (+{((test_price/current_price-1)*100):.2f}%)")
                
                # 자동 정리 체크
                cleanup_check = self.order_manager.should_cleanup_orders(current_price)
                if cleanup_check['cleanup_required']:
                    print(f"   🧹 자동 정리 필요: {', '.join(cleanup_check['reasons'])}")
                
                time.sleep(30)  # 30초마다 체크
                
            except KeyboardInterrupt:
                print(f"\n⏹️ 모니터링 중단됨")
                break
            except Exception as e:
                print(f"   ❌ 모니터링 오류: {e}")
                time.sleep(10)

    def create_buy_success_report(self):
        """📊 매수 성공률 리포트 생성"""
        stats = self.chart.get_enhanced_stats()
        
        print(f"\n📊 매수 성공률 리포트:")
        print(f"{'='*50}")
        
        # 기본 통계
        total_buy_attempts = stats.get('total_buys', 0)
        if total_buy_attempts > 0:
            print(f"🛒 총 매수 시도: {total_buy_attempts}회")
            print(f"✅ 매수 성공: {self.successful_buys}회")
            print(f"📈 매수 성공률: {(self.successful_buys/total_buy_attempts)*100:.1f}%")
        else:
            print(f"🛒 매수 시도: 0회")
        
        # 모드별 분석
        print(f"\n🔄 모드별 통계:")
        print(f"   📈 성장 모드 시간: {self.mode_stats['growth_time']//3600:.1f}시간")
        print(f"   ⚖️ 균형 모드 시간: {self.mode_stats['balance_time']//3600:.1f}시간")
        print(f"   🚨 강제 매수: {self.mode_stats['forced_buys']}회")
        
        # 크기별 분석
        if 'size_analysis' in stats:
            print(f"\n🎲 거래 크기별 분석:")
            for size_type, data in stats['size_analysis'].items():
                print(f"   {size_type}: {data['count']}회, {data['total_volume']:,.0f} SPSI")
        
        # 개선 제안
        if total_buy_attempts > 0:
            success_rate = (self.successful_buys/total_buy_attempts)*100
            
            if success_rate < 50:
                print(f"\n⚠️ 매수 성공률 개선 필요:")
                print(f"   - 더 공격적인 가격 설정 고려")
                print(f"   - 거래량 조정 검토")
                print(f"   - 시장 타이밍 분석")
            elif success_rate > 80:
                print(f"\n✅ 우수한 매수 성공률:")
                print(f"   - 현재 전략 유지")
                print(f"   - 거래량 확대 고려")
            else:
                print(f"\n🔵 적정한 매수 성공률:")
                print(f"   - 세부 튜닝으로 개선 가능")

    def test_enhanced_buy(self):
        """🚀 향상된 매수 테스트"""
        print("🚀 향상된 매수 테스트 실행...")
        
        # 거래 전 상태
        before_balance = self.get_account_balance()
        current_price = self.get_reference_price()
        
        if before_balance and current_price:
            print(f"\n📊 거래 전 상태:")
            print(f"   - USDT: ${before_balance['usdt']:.2f}")
            print(f"   - SPSI: {before_balance['spsi']:,.0f}")
            print(f"   - 현재 가격: ${current_price:.6f}")
            
            # 잔고 분석
            balance_status = self.analyze_balance_status(before_balance, current_price)
            print(f"   - SPSI 비율: {balance_status['spsi_ratio']*100:.1f}%")
            print(f"   - USDT 비율: {balance_status['usdt_ratio']*100:.1f}%")
            print(f"   - 권장 모드: {balance_status['recommended_mode']}")
            print(f"   - 긴급도: {balance_status['urgency']}")
            
            # 주문 상태
            categorized = self.order_manager.get_categorized_orders(current_price)
            print(f"   - 현재 주문: {categorized['buy_count']}B + {categorized['sell_count']}S = {categorized['total_count']}개")
        
        # 테스트 실행
        result = self.execute_smart_growth_cycle()
        
        if result:
            print("\n✅ 향상된 매수 테스트 성공!")
            print("🎯 실제 향상된 주문이 모드에 따라 배치되었습니다.")
            print("📊 스마트 주문 관리가 자동으로 적용되었습니다.")
            
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
                
                # 새로운 주문 상태
                new_categorized = self.order_manager.get_categorized_orders(current_price)
                print(f"   - 새 주문 상태: {new_categorized['buy_count']}B + {new_categorized['sell_count']}S = {new_categorized['total_count']}개")
                
                if spsi_diff > 0:
                    print(f"   - 결과: 🟢 SPSI 증가 (성공적인 복구)")
                elif spsi_diff < 0:
                    print(f"   - 결과: 🔴 SPSI 감소 (추가 복구 필요)")
                else:
                    print(f"   - 결과: 🔵 SPSI 변화 없음")
            
            print("\n💡 다음 단계:")
            print("   - 메뉴 11번: 상세 주문 현황 확인")
            print("   - 메뉴 7번: 성장 차트 확인")
            print("   - 메뉴 4번: 향상된 자가매매 시작")
            return True
        else:
            print("\n❌ 향상된 매수 테스트 실패!")
            print("💡 메뉴 9번(문제 진단)을 실행하여 원인을 파악하세요.")
            return False

    def start_self_trading(self):
        """자가매매 시작 (향상된 버전)"""
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
        
        # 초기 주문 정리
        categorized = self.order_manager.get_categorized_orders(current_price)
        if categorized['total_count'] > self.order_manager.max_total_orders:
            print("🧹 시작 전 주문 정리...")
            self.order_manager.execute_smart_cleanup(current_price, force=True)
        
        # 초기 모드 설정
        balance_status = self.analyze_balance_status(balance, current_price)
        self.update_trading_mode(balance_status, current_price, balance)
        
        self.running = True
        print("🚀 향상된 스마트 성장 자가매매 시스템 시작!")
        print(f"🎯 특징: 향상된 매수 로직 + 스마트 주문 관리 + 적절한 거래량")
        print(f"📈 목표 거래량: {self.min_volume_per_5min:,} ~ {self.max_volume_per_5min:,} SPSI/5분")
        print(f"🎯 주문 한도: 매수 {self.order_manager.max_buy_orders}개 + 매도 {self.order_manager.max_sell_orders}개")
        print(f"🔄 현재 모드: {self.current_mode}")
        print(f"💰 자산 현황: SPSI {balance_status['spsi_ratio']*100:.1f}% / USDT {balance_status['usdt_ratio']*100:.1f}%")
        
        def trading_loop():
            consecutive_failures = 0
            max_failures = 3
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - 향상된 스마트 성장 자가매매 실행")
                    
                    # 향상된 스마트 성장 자가매매 실행
                    success = self.execute_smart_growth_cycle()
                    
                    if success:
                        consecutive_failures = 0
                        
                        # 🔥 상세 통계 출력
                        print(f"   📈 실시간 통계:")
                        print(f"      - 오늘 거래량: {self.total_volume_today:,.0f} SPSI")
                        print(f"      - 오늘 거래 횟수: {self.total_trades_today}회")
                        print(f"      - 매수 성공: {self.successful_buys}회")
                        print(f"      - 매도 성공: {self.successful_sells}회")
                        
                        # 주문 관리 상태
                        current_price_now = self.get_reference_price()
                        if current_price_now:
                            categorized = self.order_manager.get_categorized_orders(current_price_now)
                            print(f"      - 주문 상황: {categorized['buy_count']}B + {categorized['sell_count']}S = {categorized['total_count']}개")
                            
                            if categorized['total_count'] > self.order_manager.max_total_orders:
                                print(f"      - ⚠️ 주문 한도 초과, 다음 사이클에서 정리됨")
                        
                        # 모드 정보
                        print(f"   🔄 모드 정보:")
                        print(f"      - 현재 모드: {self.current_mode}")
                        if self.current_mode == 'growth':
                            print(f"      - 성장 지속시간: {self.growth_mode_duration//3600:.1f}시간")
                        print(f"      - 강제 매수: {self.mode_stats['forced_buys']}회")
                        print(f"      - 강제 매도: {self.mode_stats['forced_sells']}회")
                        
                    else:
                        consecutive_failures += 1
                        print(f"   ⚠️ 거래 실패 ({consecutive_failures}/{max_failures})")
                        
                        if consecutive_failures >= max_failures:
                            print(f"   🛑 연속 {max_failures}회 실패로 일시 정지")
                            print(f"   ⏳ 1분 후 재시도...")
                            time.sleep(60)
                            consecutive_failures = 0
                    
                    # 🔥 동적 대기 (모드별)
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
        print("⏹️ 향상된 스마트 성장 자가매매 중지 요청됨...")
        
        # 필요시 주문 정리
        try:
            current_price = self.get_reference_price()
            if current_price:
                categorized = self.order_manager.get_categorized_orders(current_price)
                if categorized['total_count'] > 15:  # 15개 이상일 때만 정리
                    print("🧹 중지 전 과도한 주문 정리...")
                    self.order_manager.execute_smart_cleanup(current_price)
        except Exception as e:
            print(f"⚠️ 중지 전 정리 오류: {e}")
        
        if self.trading_thread:
            print("⏳ 거래 스레드 종료 대기...")
            self.trading_thread.join(timeout=10)
        
        print("✅ 향상된 자가매매 완전 중지됨")

    def get_status(self):
        """상태 조회 (향상된 버전)"""
        try:
            balance = self.get_account_balance()
            current_price = self.get_reference_price()
            
            print(f"\n{'='*80}")
            print(f"🚀 향상된 스마트 성장 자가매매 시스템 상태")
            print(f"{'='*80}")
            print(f"💰 현재 가격: ${current_price:.6f}" if current_price else "💰 현재 가격: 조회 실패")
            
            if balance and current_price:
                balance_status = self.analyze_balance_status(balance, current_price)
                
                print(f"💳 자산 현황:")
                print(f"   - USDT 잔고: ${balance['usdt']:.2f}")
                print(f"   - SPSI 잔고: {balance['spsi']:,.2f}")
                print(f"   - 총 자산: ${balance_status['total_value']:.2f}")
                print(f"   - SPSI 비율: {balance_status['spsi_ratio']*100:.1f}%")
                print(f"   - USDT 비율: {balance_status['usdt_ratio']*100:.1f}%")
                
                # 주문 관리 상태
                categorized = self.order_manager.get_categorized_orders(current_price)
                print(f"\n🎯 주문 관리 상태:")
                print(f"   - 총 주문: {categorized['total_count']}개 (한도: {self.order_manager.max_total_orders})")
                print(f"   - 매수 주문: {categorized['buy_count']}개 (한도: {self.order_manager.max_buy_orders})")
                print(f"   - 매도 주문: {categorized['sell_count']}개 (한도: {self.order_manager.max_sell_orders})")
                
                if categorized['total_count'] <= self.order_manager.max_total_orders:
                    print(f"   - 상태: ✅ 주문 관리 양호")
                else:
                    print(f"   - 상태: 🚨 주문 수 초과 (정리 필요)")
                
                # 상태 평가
                if balance_status['spsi_ratio'] < 0.2:
                    print(f"   - 상태: 🚨 SPSI 위험 수준!")
                elif balance_status['spsi_ratio'] < 0.5:
                    print(f"   - 상태: ⚠️ SPSI 부족")
                elif balance_status['spsi_ratio'] > 0.7:
                    print(f"   - 상태: ✅ SPSI 충분")
                else:
                    print(f"   - 상태: 🔵 SPSI 보통")
            else:
                print("💰 잔고: 조회 실패")
            
            print(f"🔄 실행 상태: {'🟢 활성' if self.running else '🔴 중지'}")
            print(f"🎯 현재 모드: {self.current_mode}")
            
            # 거래 통계
            stats = self.chart.get_enhanced_stats()
            print(f"📊 거래 통계:")
            print(f"   - 오늘 총 거래량: {self.total_volume_today:,.0f} SPSI")
            print(f"   - 오늘 총 거래 횟수: {self.total_trades_today}회")
            print(f"   - 매수 성공: {self.successful_buys}회")
            print(f"   - 매도 성공: {self.successful_sells}회")
            print(f"   - 누적 수수료: ${self.total_fees_paid:.4f}")
            
            # 주문 관리 통계
            cleanup_stats = self.order_manager.cleanup_stats
            print(f"🧹 주문 관리 통계:")
            print(f"   - 총 정리 횟수: {cleanup_stats['total_cleanups']}회")
            print(f"   - 취소된 주문: {cleanup_stats['orders_canceled']}개")
            if cleanup_stats['total_cleanups'] > 0:
                avg_per_cleanup = cleanup_stats['orders_canceled'] / cleanup_stats['total_cleanups']
                print(f"   - 회당 평균: {avg_per_cleanup:.1f}개")
            
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            print(f"❌ 상태 조회 중 오류 발생: {e}")

    def show_growth_chart(self):
        """성장 모드 차트 표시"""
        try:
            print("📊 스마트 성장 차트 생성 중...")
            
            # 차트 생성
            chart_filename = f"enhanced_growth_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.chart.plot_growth_chart(chart_filename)
            
            # 통계 출력
            stats = self.chart.get_enhanced_stats()
            print(f"\n🚀 향상된 스마트 성장 통계:")
            print(f"   - 총 거래 시도: {stats['total_trades']}회")
            print(f"   - 매수 성공: {stats['total_buys']}회 (🟢)")
            print(f"   - 매도 성공: {stats['total_sells']}회 (🔴)")
            print(f"   - 매수 거래량: {stats['buy_volume']:,.0f} SPSI")
            print(f"   - 매도 거래량: {stats['sell_volume']:,.0f} SPSI")
            
            # 균형 분석
            if 'balance_analysis' in stats:
                balance = stats['balance_analysis']
                print(f"\n⚖️ 매수/매도 균형 분석:")
                print(f"   - 매수 비율: {balance['buy_ratio']:.1f}%")
                print(f"   - 매도 비율: {balance['sell_ratio']:.1f}%")
                print(f"   - 거래량 불균형: {balance['volume_imbalance']:,.0f} SPSI")
                print(f"   - 횟수 불균형: {balance['count_imbalance']}회")
                
                if balance['buy_ratio'] > 60:
                    print(f"   - 평가: 🟢 매수 우위 (SPSI 복구 중)")
                elif balance['sell_ratio'] > 60:
                    print(f"   - 평가: 🔴 매도 우위 (SPSI 감소 중)")
                else:
                    print(f"   - 평가: 🔵 균형 상태")
            
        except Exception as e:
            print(f"❌ 성장 차트 생성 오류: {e}")
            logger.error(f"성장 차트 생성 오류: {e}")

def main():
    print("🚀 향상된 스마트 성장 LBank 자가매매 시스템")
    print("🎯 특징: 매수 성공률 개선 + 스마트 주문 관리 + 3만~6만 거래량")
    print("💡 해결책: 공격적 매수 + 재시도 로직 + 매수5개+매도5개 관리")
    
    # matplotlib 설정
    try:
        import matplotlib
        matplotlib.use('Agg')
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
        print("📡 향상된 스마트 성장 자가매매 시스템 초기화 중...")
        st = SmartGrowthTradingSystem(API_KEY, API_SECRET)
        
        while True:
            try:
                print("\n" + "="*80)
                print("🚀 향상된 스마트 성장 LBank 자가매매 시스템")
                print("="*80)
                print("🎯 특징: 매수 성공률 개선 + 스마트 주문 관리 + 적절한 거래량")
                print("💡 해결책: 공격적 매수 + 재시도 로직 + 매수5개+매도5개 자동 관리")
                print("🔄 모드: 성장(SPSI복구) ↔ 균형(박스권) 자동 전환")
                print("="*80)
                print("1. 💰 상태 확인 (모드 + 균형 + 주문 관리)")
                print("2. 🧪 시스템 테스트 (API + 모드 분석)")
                print("3. 🚀 향상된 매수 테스트 (재시도 + 주문 관리)")
                print("4. 🔥 향상된 자가매매 시작")
                print("5. ⏹️ 자가매매 중지")
                print("6. 🧹 스마트 주문 정리 (매수5개+매도5개 유지)")
                print("7. 📊 성장 차트 보기")
                print("8. 🔍 실시간 매수 모니터링 (30분)")
                print("9. 🔧 매수 문제 진단")
                print("10. 📈 매수 성공률 리포트")
                print("11. 📋 상세 주문 현황")
                print("12. 🎯 주문 관리 모니터링 (10분)")
                print("0. 🚪 종료")
                
                choice = input("\n선택하세요 (0-12): ").strip()
                
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
                        
                        # 주문 관리 테스트
                        categorized = st.order_manager.get_categorized_orders(price)
                        print(f"✅ 주문 관리 시스템: {categorized['buy_count']}B + {categorized['sell_count']}S = {categorized['total_count']}개")
                        
                        # 잔고 상태 분석
                        balance_status = st.analyze_balance_status(balance, price)
                        feasibility = st.analyze_trading_feasibility(balance, price)
                        
                        print(f"\n🔍 상세 분석:")
                        print(f"   - SPSI 비율: {balance_status['spsi_ratio']*100:.1f}%")
                        print(f"   - USDT 비율: {balance_status['usdt_ratio']*100:.1f}%")
                        print(f"   - 총 자산: ${balance_status['total_value']:.2f}")
                        print(f"   - 권장 모드: {balance_status['recommended_mode']}")
                        print(f"   - 긴급도: {balance_status['urgency']}")
                        print(f"   - 매수 가능: {'✅' if feasibility['can_buy'] else '❌'}")
                        print(f"   - 매도 가능: {'✅' if feasibility['can_sell'] else '❌'}")
                        
                        if feasibility['can_buy']:
                            print(f"   - 권장 매수량: {feasibility['recommended_buy_amount']:,.0f} SPSI")
                            test_price = st.calculate_aggressive_buy_price(price, balance_status['recommended_mode'], balance_status['urgency'])
                            print(f"   - 예상 매수가: ${test_price:.6f} (+{((test_price/price-1)*100):.2f}%)")
                        
                        # 총 자산 확인
                        if balance_status['total_value'] >= 10:
                            print("✅ 향상된 자가매매 실행 가능")
                        else:
                            print("❌ 자산 부족 (최소 $10 필요)")
                    else:
                        print("❌ 기본 정보 조회 실패")
                    
                elif choice == '3':
                    print("\n⚠️ 실제 향상된 매수가 실행됩니다!")
                    print("🚀 향상된 매수 테스트:")
                    print("   - 재시도 로직 적용 (최대 3회)")
                    print("   - 공격적 가격 전략 (체결률 우선)")
                    print("   - 스마트 주문 관리 (자동 정리)")
                    print("   - 실시간 체결 확인")
                    
                    confirm = input("정말 테스트 하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.test_enhanced_buy()
                    else:
                        print("테스트 취소됨")
                    
                elif choice == '4':
                    print("\n⚠️ 향상된 자가매매 시작 주의사항:")
                    print("- 매수 성공률을 높이기 위한 공격적 가격 적용")
                    print("- 매수 실패시 자동 재시도 (최대 3회)")
                    print("- 주문 수를 매수5개+매도5개로 자동 관리")
                    print("- SPSI 잔고 상태를 지속적으로 모니터링")
                    print("- 모드별 동적 거래 간격 적용")
                    print("- 모든 기능이 자동으로 최적화됨")
                    
                    confirm = input("\n정말 시작하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        st.start_self_trading()
                        if st.running:
                            print("✅ 향상된 스마트 성장 자가매매 시스템이 시작되었습니다!")
                            print("💡 모든 기능이 자동으로 최적화되어 실행됩니다.")
                        else:
                            print("❌ 자가매매 시작 실패")
                    else:
                        print("자가매매 시작 취소됨")
                    
                elif choice == '5':
                    st.stop_self_trading()
                    
                elif choice == '6':
                    print("🧹 스마트 주문 정리 (매수5개+매도5개 유지)...")
                    current_price = st.get_reference_price()
                    
                    if current_price:
                        # 정리 전 상태
                        before_categorized = st.order_manager.get_categorized_orders(current_price)
                        print(f"정리 전: {before_categorized['buy_count']}B + {before_categorized['sell_count']}S = {before_categorized['total_count']}개")
                        
                        # 스마트 정리 실행
                        result = st.order_manager.execute_smart_cleanup(current_price, force=True)
                        
                        if result['success']:
                            print(f"✅ {result['canceled_count']}개 주문 정리 완료")
                            print(f"정리 후: {result['final_buy_count']}B + {result['final_sell_count']}S = {result['final_total_count']}개")
                        else:
                            print(f"❌ 주문 정리 실패")
                    else:
                        print("❌ 현재 가격 조회 실패")
                    
                elif choice == '7':
                    st.show_growth_chart()
                    
                elif choice == '8':
                    duration = input("모니터링 시간을 입력하세요 (분, 기본값 30): ").strip()
                    try:
                        duration = int(duration) if duration else 30
                    except:
                        duration = 30
                    
                    st.real_time_buy_monitor(duration)
                    
                elif choice == '9':
                    st.diagnose_buy_issues()
                    
                elif choice == '10':
                    st.create_buy_success_report()
                    
                elif choice == '11':
                    st.show_order_status()
                    
                elif choice == '12':
                    duration = input("주문 모니터링 시간을 입력하세요 (분, 기본값 10): ").strip()
                    try:
                        duration = int(duration) if duration else 10
                    except:
                        duration = 10
                    
                    st.order_manager.monitor_orders_realtime(duration)
                    
                elif choice == '0':
                    if st.running:
                        print("⚠️ 자가매매가 실행 중입니다. 먼저 중지하시겠습니까? (y/N): ", end="")
                        stop_confirm = input().strip().lower()
                        if stop_confirm == 'y':
                            st.stop_self_trading()
                        else:
                            continue
                    
                    print("👋 향상된 스마트 성장 자가매매 시스템을 종료합니다.")
                    break
                    
                else:
                    print("❌ 잘못된 선택입니다. 0-12 사이의 번호를 입력하세요.")
                    
            except KeyboardInterrupt:
                print("\n⏹️ 사용자 중단 요청")
                if st.running:
                    st.stop_self_trading()
                break
            except Exception as e:
                print(f"💥 메뉴 처리 오류: {e}")
                logger.error(f"메뉴 처리 오류: {e}")
                time.sleep(1)
                
    except Exception as e:
        print(f"💥 시스템 초기화 오류: {e}")
        logger.error(f"시스템 초기화 오류: {e}")
        input("Enter를 눌러 종료...")

if __name__ == "__main__":
    main()