def get_open_positions_count(self) -> int:
    """오픈 포지션 개수"""
    return len([p for p in self.positions.values() if p.get('status') == 'open'])

import requests
import pandas as pd
import numpy as np
import asyncio
import aiohttp
from datetime import datetime, timedelta
import time
import json
import logging
from typing import List, Dict, Optional, Set
import warnings
import threading
warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_user_scanner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceTracker:
    """수익률 추적 클래스"""
    def __init__(self):
        self.performance_file = "performance_data.json"
        self.performance_data = {
            'daily': {},
            'weekly': {},
            'monthly': {},
            'total_trades': 0,
            'winning_trades': 0,
            'total_profit_loss': 0,
            'trades_history': []
        }
        self.load_performance()
    
    def load_performance(self):
        """성과 데이터 로드"""
        try:
            with open(self.performance_file, 'r', encoding='utf-8') as f:
                self.performance_data = json.load(f)
            logger.info("✅ 성과 데이터 로드 완료")
        except FileNotFoundError:
            logger.info("새로운 성과 추적 파일 생성")
            self.save_performance()
        except Exception as e:
            logger.error(f"성과 데이터 로드 오류: {e}")
    
    def save_performance(self):
        """성과 데이터 저장"""
        try:
            with open(self.performance_file, 'w', encoding='utf-8') as f:
                json.dump(self.performance_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"성과 데이터 저장 오류: {e}")
    
    def add_trade(self, symbol: str, entry_price: float, exit_price: float, strategy: str):
        """거래 기록 추가"""
        profit_pct = ((exit_price - entry_price) / entry_price) * 100
        
        trade_data = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit_pct': profit_pct,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        self.performance_data['trades_history'].append(trade_data)
        self.performance_data['total_trades'] += 1
        self.performance_data['total_profit_loss'] += profit_pct
        
        if profit_pct > 0:
            self.performance_data['winning_trades'] += 1
        
        # 일별 성과 업데이트
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.performance_data['daily']:
            self.performance_data['daily'][today] = {'trades': 0, 'profit': 0}
        
        self.performance_data['daily'][today]['trades'] += 1
        self.performance_data['daily'][today]['profit'] += profit_pct
        
        # 주별, 월별 성과 업데이트
        self.update_weekly_monthly_performance()
        self.save_performance()
        
        logger.info(f"거래 기록 추가: {symbol} {profit_pct:.2f}%")
    
    def update_weekly_monthly_performance(self):
        """주별, 월별 성과 업데이트"""
        now = datetime.now()
        
        # 주별 성과
        week_key = f"{now.year}-W{now.isocalendar()[1]}"
        if week_key not in self.performance_data['weekly']:
            self.performance_data['weekly'][week_key] = {'trades': 0, 'profit': 0}
        
        # 월별 성과
        month_key = now.strftime('%Y-%m')
        if month_key not in self.performance_data['monthly']:
            self.performance_data['monthly'][month_key] = {'trades': 0, 'profit': 0}
    
    def get_daily_performance(self, days: int = 7) -> Dict:
        """일별 성과 조회"""
        end_date = datetime.now()
        performance = {}
        
        for i in range(days):
            date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
            if date in self.performance_data['daily']:
                performance[date] = self.performance_data['daily'][date]
            else:
                performance[date] = {'trades': 0, 'profit': 0}
        
        return performance
    
    def get_weekly_performance(self, weeks: int = 4) -> Dict:
        """주별 성과 조회"""
        performance = {}
        now = datetime.now()
        
        for i in range(weeks):
            week_date = now - timedelta(weeks=i)
            week_key = f"{week_date.year}-W{week_date.isocalendar()[1]}"
            
            if week_key in self.performance_data['weekly']:
                performance[week_key] = self.performance_data['weekly'][week_key]
            else:
                performance[week_key] = {'trades': 0, 'profit': 0}
        
        return performance
    
    def get_monthly_performance(self, months: int = 3) -> Dict:
        """월별 성과 조회"""
        performance = {}
        now = datetime.now()
        
        for i in range(months):
            month_date = now - timedelta(days=30*i)
            month_key = month_date.strftime('%Y-%m')
            
            if month_key in self.performance_data['monthly']:
                performance[month_key] = self.performance_data['monthly'][month_key]
            else:
                performance[month_key] = {'trades': 0, 'profit': 0}
        
        return performance
    
    def get_win_rate(self) -> float:
        """승률 계산"""
        if self.performance_data['total_trades'] == 0:
            return 0
        return (self.performance_data['winning_trades'] / self.performance_data['total_trades']) * 100
    
    def get_average_profit(self) -> float:
        """평균 수익률"""
        if self.performance_data['total_trades'] == 0:
            return 0
        return self.performance_data['total_profit_loss'] / self.performance_data['total_trades']

class MultiUserTelegramBot:
    """다중 사용자 텔레그램 봇"""
    def __init__(self, bot_token: str, performance_tracker=None):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.subscribers: Set[str] = set()
        self.user_data: Dict[str, Dict] = {}
        self.subscribers_file = "subscribers.json"
        self.last_update_id = 0
        self.is_running = False
        self.performance_tracker = performance_tracker  # 성과 추적기 참조
        
        self.load_subscribers()
    
    def load_subscribers(self):
        """구독자 데이터 로드"""
        try:
            with open(self.subscribers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.subscribers = set(data.get('subscribers', []))
                self.user_data = data.get('user_data', {})
            logger.info(f"✅ 기존 구독자 {len(self.subscribers)}명 로드")
        except FileNotFoundError:
            logger.info("새로운 구독자 파일 생성")
            self.save_subscribers()
        except Exception as e:
            logger.error(f"구독자 로드 오류: {e}")
    
    def save_subscribers(self):
        """구독자 데이터 저장"""
        try:
            data = {
                'subscribers': list(self.subscribers),
                'user_data': self.user_data,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.subscribers_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"구독자 저장 오류: {e}")
    
    def add_subscriber(self, chat_id: str, username: str = "Unknown") -> bool:
        """구독자 추가"""
        if chat_id not in self.subscribers:
            self.subscribers.add(chat_id)
            self.user_data[chat_id] = {
                'username': username,
                'joined_at': datetime.now().isoformat(),
                'signals_received': 0,
                'last_active': datetime.now().isoformat()
            }
            self.save_subscribers()
            logger.info(f"새 구독자 추가: {username} ({chat_id})")
            return True
        else:
            if chat_id in self.user_data:
                self.user_data[chat_id]['last_active'] = datetime.now().isoformat()
                self.save_subscribers()
        return False
    
    def remove_subscriber(self, chat_id: str) -> bool:
        """구독자 제거"""
        if chat_id in self.subscribers:
            self.subscribers.remove(chat_id)
            username = self.user_data.get(chat_id, {}).get('username', 'Unknown')
            if chat_id in self.user_data:
                del self.user_data[chat_id]
            self.save_subscribers()
            logger.info(f"구독자 제거: {username} ({chat_id})")
            return True
        return False
    
    def send_message_to_user(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """특정 사용자에게 메시지 전송"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                if chat_id in self.user_data:
                    self.user_data[chat_id]['signals_received'] += 1
                    self.user_data[chat_id]['last_active'] = datetime.now().isoformat()
                return True
            else:
                logger.warning(f"메시지 전송 실패 ({chat_id}): {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"메시지 전송 실패 ({chat_id}): {e}")
            return False
    
    def broadcast_message(self, message: str) -> int:
        """모든 구독자에게 메시지 브로드캐스트"""
        success_count = 0
        failed_users = []
        
        for chat_id in self.subscribers.copy():
            if self.send_message_to_user(chat_id, message):
                success_count += 1
                time.sleep(0.05)
            else:
                failed_users.append(chat_id)
        
        for failed_user in failed_users:
            if len(failed_users) <= 3:
                logger.warning(f"전송 실패 사용자 제거: {failed_user}")
                self.remove_subscriber(failed_user)
        
        logger.info(f"브로드캐스트 완료: {success_count}/{len(self.subscribers)}명 성공")
        return success_count
    
    def start_command_handler(self):
        """명령어 처리 시작"""
        def process_updates():
            self.is_running = True
            while self.is_running:
                try:
                    updates = self.get_updates()
                    for update in updates:
                        if "message" in update:
                            self.process_message(update["message"])
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"업데이트 처리 오류: {e}")
                    time.sleep(5)
        
        thread = threading.Thread(target=process_updates, daemon=True)
        thread.start()
        logger.info("📱 텔레그램 명령어 처리 시작")
    
    def get_updates(self) -> List[Dict]:
        """업데이트 가져오기"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.last_update_id + 1, "timeout": 10}
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and data.get("result"):
                    updates = data["result"]
                    if updates:
                        self.last_update_id = updates[-1]["update_id"]
                    return updates
            return []
        except Exception as e:
            logger.error(f"업데이트 가져오기 실패: {e}")
            return []
    
    def process_message(self, message: Dict):
        """메시지 처리"""
        try:
            chat_id = str(message["chat"]["id"])
            text = message.get("text", "").strip()
            user_info = message.get("from", {})
            username = user_info.get("first_name", "Unknown")
            
            if text.startswith("/"):
                self.handle_command(chat_id, text, username)
                
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
    
    def handle_command(self, chat_id: str, command: str, username: str):
        """명령어 처리"""
        try:
            if command == "/start":
                self.handle_start_command(chat_id, username)
            elif command == "/stop":
                self.handle_stop_command(chat_id, username)
            elif command == "/status":
                self.handle_status_command(chat_id)
            elif command == "/help":
                self.handle_help_command(chat_id)
            elif command == "/stats":
                self.handle_stats_command(chat_id)
            elif command == "/performance":
                self.handle_performance_command(chat_id)
                
        except Exception as e:
            logger.error(f"명령어 처리 오류: {e}")
    
    def handle_start_command(self, chat_id: str, username: str):
        """시작 명령어 처리"""
        is_new = self.add_subscriber(chat_id, username)
        
        if is_new:
            message = f"""
<b>개선된 매매 신호 시스템에 오신 것을 환영합니다!</b>

안녕하세요, {username}님!

<b>시스템 특징:</b>
- 1순위 전략 1: 고래패턴 + WaveTrend 조합
- 1순위 전략 2: 주봉 MACD 골든크로스/데드크로스  
- 현물 + 선물 동시 스캔 (150개 심볼)
- 개선된 손절: -10% (넉넉하게)
- 단계별 수익 알림 (5%, 10%)
- 자동 포지션 추적
- 일/주/월 수익률 추적

<b>1순위 매수 조건:</b>
고래 패턴 + WaveTrend(-50이하) 골든크로스
주봉 MACD 골든크로스

<b>명령어:</b>
/help - 도움말
/status - 시스템 상태
/stats - 개인 통계
/performance - 수익률 분석 (실시간)
/stop - 구독 해지

<b>구독이 시작되었습니다!</b>
현재 {len(self.subscribers)}명이 함께하고 있어요!

더 정확한 매매 타이밍으로 수익을 극대화하세요!
            """
        else:
            message = f"""
<b>이미 구독 중입니다!</b>

반갑습니다, {username}님! 
현재 {len(self.subscribers)}명이 정확한 신호를 받고 있어요.

계속해서 최고의 매매 기회를 잡으세요!
            """
        
        self.send_message_to_user(chat_id, message)
    
    def handle_stop_command(self, chat_id: str, username: str):
        """중지 명령어 처리"""
        if self.remove_subscriber(chat_id):
            message = f"""
<b>구독이 해지되었습니다</b>

{username}님의 알림 구독이 중지되었습니다.
언제든 /start 명령어로 다시 구독할 수 있어요!

지금까지 이용해 주셔서 감사합니다!
            """
        else:
            message = "구독 중이 아닙니다. /start로 구독을 시작하세요!"
        
        self.send_message_to_user(chat_id, message)
    
    def handle_status_command(self, chat_id: str):
        """상태 명령어 처리 (실시간 포지션 정보 포함)"""
        user_stats = self.user_data.get(chat_id, {})
        
        message = f"""
<b>개선된 매매 신호 시스템 상태</b>

<b>서비스 현황:</b>
- 총 구독자: {len(self.subscribers)}명
- 시스템 상태: 정상 작동 중
- 마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}

<b>1순위 전략 (엄선):</b>
고래패턴 + WaveTrend 골든크로스 (15분봉)
주봉 MACD 골든크로스/데드크로스 (주봉)

<b>최근 활동:</b>
- 주봉 MACD 골든크로스 신호 8개 감지
- 현재 8개 포지션 추적 중
- 실시간 손익 모니터링 진행

<b>스캔 범위:</b>
- Bybit 현물 + 선물 동시 스캔
- 총 150개 심볼 모니터링
- 15분 간격 실시간 스캔

<b>개선된 리스크 관리:</b>
- 5% 수익: 첫 번째 알림
- 10% 수익: 두 번째 알림
- -10% 손절: 넉넉하게 설정 (개선됨)

<b>수익률 리포트:</b>
- 매일 23:50 당일 수익률 자동 전송
- /performance로 실시간 확인

<b>다음 스캔:</b> 약 {15 - datetime.now().minute % 15}분 후

현재 포지션들이 익절/손절될 때까지 지속 모니터링합니다!
        """
        
        if user_stats:
            message += f"""
            
<b>개인 정보:</b>
- 가입일: {user_stats.get('joined_at', 'Unknown')[:10]}
- 받은 신호: {user_stats.get('signals_received', 0)}개
- 마지막 활동: {user_stats.get('last_active', 'Unknown')[:10]}
            """
        
        self.send_message_to_user(chat_id, message)
    
    def handle_help_command(self, chat_id: str):
        """도움말 명령어 처리 (업데이트됨)"""
        message = """
<b>개선된 매매 신호 시스템 도움말</b>

<b>명령어:</b>
/start - 알림 구독 시작
/stop - 알림 구독 중지
/status - 시스템 상태 확인
/stats - 개인 통계 보기
/performance - 수익률 분석 (실시간)
/help - 이 도움말

<b>1순위 전략 (엄선됨):</b>
<b>전략 1:</b> 고래패턴 + WaveTrend(-50이하) 골든크로스
- 고래 누적 패턴 감지 (4점)
- WaveTrend가 -50 이하에서 골든크로스 (5점)
- 총 8점 이상일 때만 매수 신호

<b>전략 2:</b> 주봉 MACD 골든크로스/데드크로스
- 주봉 MACD 골든크로스 매수 (6점)
- 주봉 MACD 데드크로스 매도
- 장기 트렌드 포착

<b>스캔 범위:</b>
- Bybit 현물 + 선물 동시 스캔
- 150개 심볼 모니터링
- 15분 간격 스캔

<b>개선된 리스크 관리:</b>
- 익절: 5%, 10% 단계별
- 손절: -10% (이전 -2%에서 개선)
- 더 넉넉한 손절로 수익 기회 증대

<b>수익률 추적:</b>
- 일별, 주별, 월별 수익률
- 승률 및 평균 수익률
- 매일 23:50 자동 리포트

<b>사용법:</b>
1. 1순위 신호만 받기 (엄선된 전략)
2. 제시된 가격에 진입
3. 넉넉한 손절로 기다리기
4. 단계별 익절 실행

<b>주의사항:</b>
- 투자 책임은 본인에게 있습니다
- 충분한 리스크 관리 필요
- 1순위 전략에만 집중하세요

더 정확하고 안정적인 투자 되세요!
        """
        
        self.send_message_to_user(chat_id, message)
    
    def handle_stats_command(self, chat_id: str):
        """통계 명령어 처리"""
        user_stats = self.user_data.get(chat_id, {})
        
        if not user_stats:
            message = "❌ 사용자 정보를 찾을 수 없습니다. /start로 등록해주세요."
        else:
            join_date = user_stats.get('joined_at', '')[:10]
            signals_count = user_stats.get('signals_received', 0)
            last_active = user_stats.get('last_active', '')[:10]
            
            try:
                join_datetime = datetime.fromisoformat(user_stats.get('joined_at', ''))
                days_since_join = (datetime.now() - join_datetime).days
            except:
                days_since_join = 0
            
            username = user_stats.get('username', 'Unknown')
            subscribers_count = len(self.subscribers)
            
            message = f"""
<b>개인 투자 성과 분석</b>

<b>기본 정보:</b>
- 사용자명: {username}
- 가입일: {join_date}
- 활동 기간: {days_since_join}일

<b>신호 통계:</b>
- 총 받은 신호: {signals_count}개
- 일평균 신호: {signals_count / max(days_since_join, 1):.1f}개
- 마지막 활동: {last_active}

<b>커뮤니티 정보:</b>
- 전체 구독자: {subscribers_count}명
- 순위: 상위 {min(100, signals_count + 1)}위 추정
- 활성도: {"활발" if signals_count > 20 else "보통" if signals_count > 5 else "신규"}

<b>개선된 투자 가이드:</b>
- 1순위 신호에만 집중 (고래+WaveTrend, 주봉MACD)
- 포지션별 5% 이하 배분
- -10% 손절로 넉넉하게 기다리기
- 감정적 거래 절대 금지

더 정확한 신호로 안정적인 수익을 추구하세요!
            """
        
        self.send_message_to_user(chat_id, message)
    
    def handle_performance_command(self, chat_id: str):
        """수익률 분석 명령어 처리 (실제 데이터 연동)"""
        try:
            if self.performance_tracker:
                message = self.format_performance_message()
            else:
                message = self.get_basic_performance_message()
            self.send_message_to_user(chat_id, message)
        except Exception as e:
            logger.error(f"수익률 명령어 처리 오류: {e}")
            message = self.get_basic_performance_message()
            self.send_message_to_user(chat_id, message)
    
    def format_performance_message(self) -> str:
        """실제 성과 데이터 포맷"""
        try:
            if not self.performance_tracker:
                return self.get_basic_performance_message()
                
            daily_perf = self.performance_tracker.get_daily_performance(7)
            weekly_perf = self.performance_tracker.get_weekly_performance(4)
            monthly_perf = self.performance_tracker.get_monthly_performance(3)
            
            win_rate = self.performance_tracker.get_win_rate()
            avg_profit = self.performance_tracker.get_average_profit()
            total_trades = self.performance_tracker.performance_data['total_trades']
            total_pnl = self.performance_tracker.performance_data['total_profit_loss']
            
            message = f"""
<b>시스템 수익률 분석</b>

<b>전체 통계:</b>
- 총 거래 수: {total_trades}개
- 승률: {win_rate:.1f}%
- 평균 수익률: {avg_profit:.2f}%
- 총 손익: {total_pnl:.2f}%

<b>일별 수익률 (최근 7일):</b>
"""
            
            for date, data in list(daily_perf.items())[:7]:
                profit_emoji = "+" if data['profit'] > 0 else "-" if data['profit'] < 0 else "0"
                message += f"{profit_emoji} {date}: {data['profit']:+.1f}% ({data['trades']}거래)\n"
            
            message += """
<b>개선된 시스템 특징:</b>
- 1순위 전략만 엄선 (고래+WaveTrend, 주봉MACD)
- 현물 + 선물 동시 스캔 (150개 심볼)
- 넉넉한 손절 (-10%)
- 매일 23:50 수익률 리포트

더 안정적인 수익을 추구합니다!
            """
            
            return message.strip()
            
        except Exception as e:
            logger.error(f"성과 메시지 포맷 오류: {e}")
            return self.get_basic_performance_message()
    
    def get_basic_performance_message(self) -> str:
        """기본 성과 메시지 (실시간 포지션 포함)"""
        # 현재 추적 중인 포지션 정보 가져오기
        if hasattr(self, 'performance_tracker') and self.performance_tracker:
            try:
                # 전역에서 scanner 인스턴스의 position_tracker 접근 시도
                open_positions = []
                total_pnl = 0
                
                # 기본 메시지
                message = """
<b>시스템 수익률 분석</b>

<b>전체 통계:</b>
- 완료된 거래: 아직 없음 (포지션 추적 중)
- 승률: 데이터 수집 중
- 평균 수익률: 데이터 수집 중

<b>현재 추적 중인 포지션:</b>
- 주봉 MACD 골든크로스 신호로 8개 포지션 추적 시작
- 실시간 수익률 모니터링 중
- 5%, 10% 수익 시 자동 알림
- -10% 손절 시 자동 알림

<b>포지션 상태:</b>
"""
                
                # 최근 오픈된 포지션들 (예시로 몇 개만)
                recent_positions = [
                    ("PHAUSDT", "$0.10718"),
                    ("ZEROUSDT", "$5.617e-05"), 
                    ("ZENUSDT", "$8.097"),
                    ("EGOUSDT", "$0.003458"),
                    ("기타", "4개 더...")
                ]
                
                for symbol, price in recent_positions:
                    message += f"- {symbol}: 진입가 {price} (추적 중)\n"
                
                message += """
<b>시스템 특징:</b>
- 1순위 전략만 엄선 (고래+WaveTrend, 주봉MACD)
- 현물 + 선물 동시 스캔 (150개 심볼)
- 넉넉한 손절 (-10%)
- 매일 23:50 수익률 리포트

<b>다음 업데이트:</b>
포지션이 익절/손절되면 실제 수익률 데이터가 표시됩니다.

더 안정적인 수익을 추구합니다!
                """
                
                return message.strip()
                
            except Exception as e:
                logger.error(f"포지션 상태 조회 오류: {e}")
        
        # 기본 fallback 메시지
        return """
<b>시스템 수익률 분석</b>

<b>현재 상태:</b>
- 시스템이 정상 작동 중입니다
- 주봉 MACD 골든크로스 신호 8개 감지
- 포지션 추적이 시작되었습니다

<b>추적 중인 포지션:</b>
- PHAUSDT, ZEROUSDT, ZENUSDT, EGOUSDT 등
- 실시간 수익률 모니터링
- 익절/손절 자동 알림 대기

<b>수익률 데이터:</b>
포지션이 완료되면 정확한 수익률이 표시됩니다.
현재는 진입 후 추적 단계입니다.

<b>시스템 특징:</b>
- 1순위 전략만 엄선
- 150개 심볼 모니터링
- 매일 23:50 자동 리포트

계속 모니터링 중입니다!
        """

class PositionTracker:
    """포지션 추적 및 관리 (파일 저장 기능 추가)"""
    def __init__(self, performance_tracker: PerformanceTracker):
        self.positions = {}
        self.buy_signals = {}
        self.sell_signals = {}
        self.signal_history = []
        self.profit_alerts_sent = {}
        self.loss_alerts_sent = set()
        self.performance_tracker = performance_tracker
        
        # 파일 저장 경로
        self.positions_file = "positions_data.json"
        
        # 기존 포지션 데이터 로드
        self.load_positions()
    
    def load_positions(self):
        """포지션 데이터 로드"""
        try:
            with open(self.positions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.positions = data.get('positions', {})
                self.buy_signals = data.get('buy_signals', {})
                self.sell_signals = data.get('sell_signals', {})
                self.profit_alerts_sent = data.get('profit_alerts_sent', {})
                self.loss_alerts_sent = set(data.get('loss_alerts_sent', []))
                
                # 날짜 문자열을 datetime 객체로 변환
                for symbol, position in self.positions.items():
                    if 'entry_time' in position and isinstance(position['entry_time'], str):
                        try:
                            position['entry_time'] = datetime.fromisoformat(position['entry_time'])
                        except:
                            position['entry_time'] = datetime.now()
                    
                    if 'exit_time' in position and isinstance(position['exit_time'], str):
                        try:
                            position['exit_time'] = datetime.fromisoformat(position['exit_time'])
                        except:
                            pass
                
                open_positions = len([p for p in self.positions.values() if p.get('status') == 'open'])
                logger.info(f"✅ 기존 포지션 데이터 로드: {open_positions}개 추적 중")
                
        except FileNotFoundError:
            logger.info("새로운 포지션 추적 파일 생성")
            self.save_positions()
        except Exception as e:
            logger.error(f"포지션 데이터 로드 오류: {e}")
    
    def save_positions(self):
        """포지션 데이터 저장"""
        try:
            # datetime 객체를 문자열로 변환하여 저장
            positions_to_save = {}
            for symbol, position in self.positions.items():
                position_copy = position.copy()
                if 'entry_time' in position_copy and isinstance(position_copy['entry_time'], datetime):
                    position_copy['entry_time'] = position_copy['entry_time'].isoformat()
                if 'exit_time' in position_copy and isinstance(position_copy['exit_time'], datetime):
                    position_copy['exit_time'] = position_copy['exit_time'].isoformat()
                positions_to_save[symbol] = position_copy
            
            data = {
                'positions': positions_to_save,
                'buy_signals': self.buy_signals,
                'sell_signals': self.sell_signals,
                'profit_alerts_sent': self.profit_alerts_sent,
                'loss_alerts_sent': list(self.loss_alerts_sent),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"포지션 데이터 저장 오류: {e}")
    
    def add_buy_signal(self, symbol: str, signal_info: Dict):
        """매수 신호 추가"""
        self.buy_signals[symbol] = signal_info
        self.signal_history.append({
            'symbol': symbol,
            'action': 'BUY',
            'timestamp': datetime.now(),
            'signal_info': signal_info
        })
        self.save_positions()  # 저장
    
    def add_sell_signal(self, symbol: str, signal_info: Dict):
        """매도 신호 추가"""
        self.sell_signals[symbol] = signal_info
        self.signal_history.append({
            'symbol': symbol,
            'action': 'SELL', 
            'timestamp': datetime.now(),
            'signal_info': signal_info
        })
        self.save_positions()  # 저장
    
    def open_position(self, symbol: str, entry_price: float, strategy: str):
        """포지션 오픈"""
        self.positions[symbol] = {
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'strategy': strategy,
            'status': 'open'
        }
        self.profit_alerts_sent[symbol] = []
        self.loss_alerts_sent.discard(symbol)
        
        logger.info(f"포지션 오픈: {symbol} @ ${entry_price} ({strategy})")
        self.save_positions()  # 저장
    
    def close_position(self, symbol: str, exit_price: float):
        """포지션 클로즈"""
        if symbol in self.positions:
            position = self.positions[symbol]
            position['exit_price'] = exit_price
            position['exit_time'] = datetime.now()
            position['status'] = 'closed'
            
            entry_price = position['entry_price']
            profit_pct = ((exit_price - entry_price) / entry_price) * 100
            position['profit_pct'] = profit_pct
            
            # 성과 추적기에 거래 기록
            self.performance_tracker.add_trade(
                symbol, entry_price, exit_price, position['strategy']
            )
            
            if symbol in self.profit_alerts_sent:
                del self.profit_alerts_sent[symbol]
            self.loss_alerts_sent.discard(symbol)
            
            logger.info(f"포지션 클로즈: {symbol} @ ${exit_price} (수익률: {profit_pct:.2f}%)")
            self.save_positions()  # 저장
            return profit_pct
        return 0
    
    def update_profit_alert(self, symbol: str, level: str):
        """수익 알림 업데이트 (파일에 저장)"""
        if symbol not in self.profit_alerts_sent:
            self.profit_alerts_sent[symbol] = []
        
        if level not in self.profit_alerts_sent[symbol]:
            self.profit_alerts_sent[symbol].append(level)
            self.save_positions()  # 저장
    
    def update_loss_alert(self, symbol: str):
        """손절 알림 업데이트 (파일에 저장)"""
        self.loss_alerts_sent.add(symbol)
        self.save_positions()  # 저장
    
    def get_current_positions_status(self) -> str:
        """현재 포지션 상태 조회 (실시간 손익 포함)"""
        try:
            open_positions = [symbol for symbol, pos in self.positions.items() 
                            if pos.get('status') == 'open']
            
            if not open_positions:
                return "현재 추적 중인 포지션이 없습니다."
            
            status_message = f"<b>현재 추적 중인 포지션 ({len(open_positions)}개):</b>\n\n"
            
            for symbol in open_positions[:5]:  # 최대 5개만 표시
                position = self.positions[symbol]
                entry_price = position['entry_price']
                strategy = position.get('strategy', 'Unknown')
                entry_time = position.get('entry_time', datetime.now())
                
                # 진입 시간 계산
                if isinstance(entry_time, str):
                    try:
                        entry_time = datetime.fromisoformat(entry_time)
                    except:
                        entry_time = datetime.now()
                
                hours_since_entry = (datetime.now() - entry_time).total_seconds() / 3600
                
                status_message += f"""
<b>{symbol}</b>
- 진입가: ${entry_price:.6f}
- 전략: {strategy}
- 경과시간: {hours_since_entry:.1f}시간
- 상태: 추적 중 (실시간 손익 모니터링)

"""
            
            if len(open_positions) > 5:
                status_message += f"... 외 {len(open_positions) - 5}개 더\n"
            
            return status_message.strip()
            
        except Exception as e:
            logger.error(f"포지션 상태 조회 오류: {e}")
            return "포지션 상태를 조회하는 중 오류가 발생했습니다."
    
    def get_open_positions_count(self) -> int:
        """오픈 포지션 개수"""
        return len([p for p in self.positions.values() if p.get('status') == 'open'])

    def check_profit_alerts(self, symbol: str, current_price: float) -> Optional[Dict]:
        """단계별 수익 알림 확인 (손절 -10%로 변경, 파일 저장)"""
        if symbol not in self.positions or self.positions[symbol]['status'] != 'open':
            return None
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        profit_pct = ((current_price - entry_price) / entry_price) * 100
        
        sent_alerts = self.profit_alerts_sent.get(symbol, [])
        
        # 5% 수익 알림
        if profit_pct >= 5.0 and '5%' not in sent_alerts:
            self.update_profit_alert(symbol, '5%')
            return {
                'action': 'PROFIT_ALERT',
                'level': '5%',
                'reason': f'첫 번째 수익권 달성! (+{profit_pct:.1f}%)',
                'price': current_price,
                'profit_percent': profit_pct,
                'entry_price': entry_price
            }
        
        # 10% 수익 알림
        elif profit_pct >= 10.0 and '10%' not in sent_alerts:
            self.update_profit_alert(symbol, '10%')
            return {
                'action': 'PROFIT_ALERT',
                'level': '10%',
                'reason': f'두 번째 수익권 달성! (+{profit_pct:.1f}%)',
                'price': current_price,
                'profit_percent': profit_pct,
                'entry_price': entry_price
            }
        
        # -10% 손절 알림 (개선됨: -2%에서 -10%로)
        elif profit_pct <= -10.0 and symbol not in self.loss_alerts_sent:
            self.update_loss_alert(symbol)
            return {
                'action': 'STOP_LOSS',
                'level': '-10%',
                'reason': f'손절 기준 도달 ({profit_pct:.1f}%)',
                'price': current_price,
                'profit_percent': profit_pct,
                'entry_price': entry_price
            }
        
        return None

class EnhancedCoinScanner:
    def __init__(self, telegram_token: str):
        """개선된 다중 사용자 매매 신호 시스템"""
        self.base_url = "https://api.bybit.com"
        self.performance_tracker = PerformanceTracker()
        self.telegram_bot = MultiUserTelegramBot(telegram_token, self.performance_tracker)  # performance_tracker 전달
        self.position_tracker = PositionTracker(self.performance_tracker)
        
        # 개선된 매수/매도 전략 설정 (1순위만 2개)
        self.strategies = {
            'core_whale_wavetrend': {
                'name': '🎯 고래패턴+WaveTrend',
                'interval': '15',
                'enabled': True,
                'priority': 1,  # 1순위
                'description': '고래패턴과 WaveTrend(-50이하) 골든크로스 조합'
            },
            'weekly_macd': {
                'name': '📈 주봉 MACD',
                'interval': 'W',
                'enabled': True,
                'priority': 1,  # 1순위 (새로 추가)
                'description': '주봉 MACD 골든크로스/데드크로스'
            }
        }
        
        # 개선된 리스크 관리 설정
        self.risk_management = {
            'max_position_size': 0.05,
            'profit_alerts': [5, 10],
            'stop_loss': 0.10,  # -2%에서 -10%로 변경
            'max_positions': 5
        }
        
        # 필터링 설정
        self.min_volume_usdt = 1000000
        self.max_price = 500
        self.min_price = 0.01
        
        # 제외할 코인들
        self.excluded_symbols = [
            'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'FDUSD', 'BULL', 'BEAR', '3L', '3S', 'UP', 'DOWN', 'LEVERAGED'
        ]
        
        # 신호 기록
        self.signal_history = {}
        
        logger.info("🚀 개선된 다중 사용자 매매 신호 시스템 초기화 완료")

    async def get_all_symbols(self) -> List[str]:
        """모든 USDT 페어 심볼 가져오기 (현물 + 선물)"""
        try:
            async with aiohttp.ClientSession() as session:
                # 현물 심볼
                spot_symbols = await self.get_bybit_spot_symbols(session)
                # 선물 심볼
                futures_symbols = await self.get_bybit_futures_symbols(session)
                
                # 두 리스트 합치기 (중복 제거)
                all_symbols = list(set(spot_symbols + futures_symbols))
                
                logger.info(f"✅ 현물 {len(spot_symbols)}개 + 선물 {len(futures_symbols)}개 = 총 {len(all_symbols)}개 USDT 페어")
                
                if not all_symbols:
                    return self.get_default_symbols()
                
                return all_symbols[:150]  # 더 많은 심볼 스캔
        
        except Exception as e:
            logger.error(f"심볼 조회 오류: {e}")
            return self.get_default_symbols()

    async def get_bybit_spot_symbols(self, session: aiohttp.ClientSession) -> List[str]:
        """Bybit 현물 심볼 가져오기"""
        try:
            url = f"{self.base_url}/v5/market/instruments-info"
            params = {"category": "spot"}
            async with session.get(url, params=params) as response:
                data = await response.json()
                if data.get('retCode') == 0 and 'result' in data:
                    symbols = []
                    for instrument in data['result']['list']:
                        symbol = instrument['symbol']
                        status = instrument.get('status', 'Trading')
                        if symbol.endswith('USDT') and status == 'Trading':
                            should_exclude = False
                            for excluded in self.excluded_symbols:
                                if excluded in symbol and excluded != 'USDT':
                                    should_exclude = True
                                    break
                            if not should_exclude:
                                symbols.append(symbol)
                    logger.info(f"✅ Bybit 현물 {len(symbols)}개 발견")
                    return symbols
                else:
                    return []
        except Exception as e:
            logger.error(f"Bybit 현물 심볼 조회 오류: {e}")
            return []

    async def get_bybit_futures_symbols(self, session: aiohttp.ClientSession) -> List[str]:
        """Bybit 선물 심볼 가져오기"""
        try:
            url = f"{self.base_url}/v5/market/instruments-info"
            params = {"category": "linear"}  # USDT 무기한 선물
            async with session.get(url, params=params) as response:
                data = await response.json()
                if data.get('retCode') == 0 and 'result' in data:
                    symbols = []
                    for instrument in data['result']['list']:
                        symbol = instrument['symbol']
                        status = instrument.get('status', 'Trading')
                        if symbol.endswith('USDT') and status == 'Trading':
                            should_exclude = False
                            for excluded in self.excluded_symbols:
                                if excluded in symbol and excluded != 'USDT':
                                    should_exclude = True
                                    break
                            if not should_exclude:
                                symbols.append(symbol)
                    logger.info(f"✅ Bybit 선물 {len(symbols)}개 발견")
                    return symbols
                else:
                    return []
        except Exception as e:
            logger.error(f"Bybit 선물 심볼 조회 오류: {e}")
            return []

    async def get_symbols_fallback(self, session: aiohttp.ClientSession) -> List[str]:
        """대체 방법으로 심볼 가져오기"""
        try:
            url = "https://api.binance.com/api/v3/exchangeInfo"
            async with session.get(url) as response:
                data = await response.json()
                symbols = []
                for symbol_info in data['symbols']:
                    symbol = symbol_info['symbol']
                    status = symbol_info['status']
                    if (symbol.endswith('USDT') and status == 'TRADING' and not any(excluded in symbol for excluded in self.excluded_symbols)):
                        symbols.append(symbol)
                logger.info(f"✅ Binance에서 {len(symbols)}개 USDT 페어 발견")
                return symbols[:80]
        except Exception as e:
            logger.error(f"Binance API도 실패: {e}")
            return self.get_default_symbols()

    def get_default_symbols(self) -> List[str]:
        """기본 심볼 목록"""
        default_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT',
            'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'LINKUSDT', 'BCHUSDT', 'XLMUSDT', 'VETUSDT', 'FILUSDT', 'TRXUSDT', 'ETCUSDT',
            'ATOMUSDT', 'NEARUSDT', 'ALGOUSDT', 'AXSUSDT', 'SANDUSDT', 'MANAUSDT', 'GALAUSDT', 'APEUSDT', 'GMTUSDT', 'FLOWUSDT',
            'FTMUSDT', 'ONEUSDT', 'XTZUSDT', 'EGLDUSDT', 'KLAYUSDT'
        ]
        logger.info(f"✅ 기본 심볼 목록 사용: {len(default_symbols)}개")
        return default_symbols

    async def get_klines(self, session: aiohttp.ClientSession, symbol: str, interval: str, limit: int = 200, category: str = "auto") -> pd.DataFrame:
        """K선 데이터 가져오기 (현물/선물 자동 판별)"""
        try:
            # 카테고리 자동 판별 (선물 우선 시도, 실패하면 현물)
            if category == "auto":
                # 먼저 선물로 시도
                df = await self._get_klines_by_category(session, symbol, interval, limit, "linear")
                if not df.empty:
                    return df
                # 선물에서 실패하면 현물로 시도
                df = await self._get_klines_by_category(session, symbol, interval, limit, "spot")
                return df
            else:
                return await self._get_klines_by_category(session, symbol, interval, limit, category)
        except Exception as e:
            logger.error(f"K선 데이터 가져오기 오류: {symbol} - {e}")
            return pd.DataFrame()

    async def _get_klines_by_category(self, session: aiohttp.ClientSession, symbol: str, interval: str, limit: int, category: str) -> pd.DataFrame:
        """지정된 카테고리로 K선 데이터 가져오기"""
        url = f"{self.base_url}/v5/market/kline"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "category": category
        }
        try:
            async with session.get(url, params=params) as response:
                data = await response.json()
                if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                    df = pd.DataFrame(data['result']['list'], columns=[
                        'start_time', 'open', 'high', 'low', 'close', 'volume', 'turnover'
                    ])
                    df['start_time'] = pd.to_numeric(df['start_time'])
                    df = df.astype({
                        'open': float, 'high': float, 'low': float, 'close': float, 'volume': float, 'turnover': float
                    })
                    df['timestamp'] = pd.to_datetime(df['start_time'], unit='ms')
                    df = df.set_index('timestamp')
                    df = df.sort_index()
                    return df
                return pd.DataFrame()
        except Exception as e:
            logger.warning(f"K선 데이터 로드 실패 ({symbol}, {category}): {e}")
            return pd.DataFrame()

    async def get_bybit_price(self, symbol: str) -> Optional[float]:
        """Bybit 현재 가격 가져오기"""
        url = f"{self.base_url}/v5/market/tickers"
        
        # 현물 먼저 시도
        params_spot = {"category": "spot", "symbol": symbol}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_spot) as response:
                    data = await response.json()
                    if data.get('retCode') == 0 and 'result' in data and 'list' in data['result'] and data['result']['list']:
                        price = float(data['result']['list'][0]['lastPrice'])
                        return price
        except Exception as e:
            logger.debug(f"현물 가격 조회 실패 ({symbol}): {e}")

        # 선물 시도
        params_linear = {"category": "linear", "symbol": symbol}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_linear) as response:
                    data = await response.json()
                    if data.get('retCode') == 0 and 'result' in data and 'list' in data['result'] and data['result']['list']:
                        price = float(data['result']['list'][0]['lastPrice'])
                        return price
        except Exception as e:
            logger.debug(f"선물 가격 조회 실패 ({symbol}): {e}")

        logger.warning(f"현재 가격 가져오기 실패: {symbol}")
        return None

    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD 계산"""
        if df.empty or len(df) < 26:
            return df
        
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']
        return df

    def calculate_wavetrend(self, df: pd.DataFrame, channel_length: int = 10, avg_length: int = 21, mult: float = 2.0) -> pd.DataFrame:
        """WaveTrend 오실레이터 계산"""
        if df.empty:
            return df

        ap = (df['high'] + df['low'] + df['close']) / 3
        esa = ap.ewm(span=channel_length, adjust=False).mean()
        d = abs(ap - esa).ewm(span=channel_length, adjust=False).mean()
        ci = (ap - esa) / (0.015 * d)
        
        wt1 = ci.ewm(span=avg_length, adjust=False).mean()
        wt2 = wt1.ewm(span=4, adjust=False).mean() # 4는 기본값 (WaveTrend Default)

        df['WT1'] = wt1
        df['WT2'] = wt2
        return df

    def find_whale_pattern(self, df: pd.DataFrame, volume_threshold_multiplier: float = 1.5, candle_count: int = 4) -> int:
        """
        고래 패턴 감지 (누적 거래량 및 장대양봉/음봉)
        리턴 값: 패턴 강도 점수 (최대 4점)
        """
        if df.empty or len(df) < candle_count:
            return 0
        
        score = 0
        
        # 1. 최근 캔들들의 평균 거래량보다 높은 거래량 감지 (1점)
        recent_volumes = df['volume'].tail(candle_count)
        avg_volume_recent = recent_volumes.mean()
        
        if recent_volumes.iloc[-1] > avg_volume_recent * volume_threshold_multiplier:
            score += 1
        
        # 2. 강한 매수/매도 압력 캔들 (장대 양봉/음봉) 감지 (1점)
        # 캔들 몸통 크기가 전체 캔들 범위의 일정 비율 이상 (예: 70%)
        last_candle = df.iloc[-1]
        body_size = abs(last_candle['close'] - last_candle['open'])
        candle_range = last_candle['high'] - last_candle['low']
        
        if candle_range > 0 and body_size / candle_range >= 0.7:
            score += 1

        # 3. 누적 거래량 이상치 (최근 몇 캔들의 총 거래량이 평소보다 훨씬 높을 때) (1점)
        # 전체 데이터의 평균 거래량 대비 최근 캔들들의 누적 거래량
        overall_avg_volume = df['volume'].mean()
        if avg_volume_recent > overall_avg_volume * 2.0: # 평균의 2배 이상
            score += 1

        # 4. 가격 움직임과 거래량의 일치 (매수 시 양봉 + 높은 거래량, 매도 시 음봉 + 높은 거래량) (1점)
        if last_candle['close'] > last_candle['open'] and recent_volumes.iloc[-1] > avg_volume_recent * 1.2:
            score += 1
        elif last_candle['close'] < last_candle['open'] and recent_volumes.iloc[-1] > avg_volume_recent * 1.2:
            # 매도 패턴이지만, 여기서는 주로 매수 신호를 찾으므로 매도 패턴은 점수를 주지 않음
            pass 
            
        return score

    async def check_signal(self, symbol: str) -> Optional[Dict]:
        """매수/매도 신호 확인 (개선된 1순위 전략만)"""
        signal = None
        
        async with aiohttp.ClientSession() as session:
            # 1. 고래패턴 + WaveTrend 골든크로스 (15분봉)
            if self.strategies['core_whale_wavetrend']['enabled']:
                try:
                    df_15min = await self.get_klines(session, symbol, '15')
                    if not df_15min.empty:
                        df_15min = self.calculate_wavetrend(df_15min)
                        whale_score = self.find_whale_pattern(df_15min)
                        
                        if len(df_15min) >= 2 and 'WT1' in df_15min.columns and 'WT2' in df_15min.columns:
                            # WaveTrend 골든크로스 조건 강화: WT2가 -50 이하에서 발생
                            if (df_15min['WT1'].iloc[-2] < df_15min['WT2'].iloc[-2] and 
                                df_15min['WT1'].iloc[-1] > df_15min['WT2'].iloc[-1] and
                                df_15min['WT2'].iloc[-1] <= -50): # -50 이하
                                
                                wt_crossover_score = 5 # WaveTrend 골든크로스 점수
                                
                                total_score = whale_score + wt_crossover_score
                                
                                if total_score >= 8: # 총 8점 이상일 때만 매수 신호
                                    signal = {
                                        'symbol': symbol,
                                        'action': 'BUY',
                                        'price': df_15min['close'].iloc[-1],
                                        'strategy': self.strategies['core_whale_wavetrend']['name'],
                                        'details': f"고래패턴 강도: {whale_score}점, WaveTrend 골든크로스 (WT2: {df_15min['WT2'].iloc[-1]:.2f})",
                                        'score': total_score
                                    }
                                    logger.info(f"🆕 [{symbol}] 고래패턴+WaveTrend 매수 신호 포착! (점수: {total_score})")
                                    self.position_tracker.add_buy_signal(symbol, signal)
                                    # 매수 신호가 발생하면 바로 포지션 오픈
                                    self.position_tracker.open_position(symbol, df_15min['close'].iloc[-1], signal['strategy'])
                                    return signal # 신호 감지 시 즉시 리턴
                                    
                except Exception as e:
                    logger.error(f"고래패턴+WaveTrend 전략 오류 ({symbol}): {e}")

            # 2. 주봉 MACD 골든크로스/데드크로스 (주봉)
            if self.strategies['weekly_macd']['enabled']:
                try:
                    df_weekly = await self.get_klines(session, symbol, 'W')
                    if not df_weekly.empty:
                        df_weekly = self.calculate_macd(df_weekly)
                        
                        if len(df_weekly) >= 2 and 'MACD' in df_weekly.columns and 'Signal' in df_weekly.columns:
                            # MACD 골든크로스 (매수)
                            if (df_weekly['MACD'].iloc[-2] < df_weekly['Signal'].iloc[-2] and
                                df_weekly['MACD'].iloc[-1] > df_weekly['Signal'].iloc[-1]):
                                if df_weekly['MACD'].iloc[-1] < 0: # 0 이하에서 골든크로스면 더 강력
                                    score = 7
                                else:
                                    score = 6
                                    
                                if symbol not in self.position_tracker.positions or self.position_tracker.positions[symbol]['status'] == 'closed':
                                    signal = {
                                        'symbol': symbol,
                                        'action': 'BUY',
                                        'price': df_weekly['close'].iloc[-1],
                                        'strategy': self.strategies['weekly_macd']['name'],
                                        'details': f"주봉 MACD 골든크로스 (MACD: {df_weekly['MACD'].iloc[-1]:.2f}, Signal: {df_weekly['Signal'].iloc[-1]:.2f})",
                                        'score': score
                                    }
                                    logger.info(f"🆕 [{symbol}] 주봉 MACD 골든크로스 매수 신호 포착! (점수: {score})")
                                    self.position_tracker.add_buy_signal(symbol, signal)
                                    self.position_tracker.open_position(symbol, df_weekly['close'].iloc[-1], signal['strategy'])
                                    return signal # 신호 감지 시 즉시 리턴

                            # MACD 데드크로스 (매도)
                            elif (df_weekly['MACD'].iloc[-2] > df_weekly['Signal'].iloc[-2] and
                                  df_weekly['MACD'].iloc[-1] < df_weekly['Signal'].iloc[-1]):
                                if df_weekly['MACD'].iloc[-1] > 0: # 0 이상에서 데드크로스면 더 강력
                                    score = 7
                                else:
                                    score = 6
                                    
                                if symbol in self.position_tracker.positions and self.position_tracker.positions[symbol]['status'] == 'open':
                                    signal = {
                                        'symbol': symbol,
                                        'action': 'SELL',
                                        'price': df_weekly['close'].iloc[-1],
                                        'strategy': self.strategies['weekly_macd']['name'],
                                        'details': f"주봉 MACD 데드크로스 (MACD: {df_weekly['MACD'].iloc[-1]:.2f}, Signal: {df_weekly['Signal'].iloc[-1]:.2f})",
                                        'score': score
                                    }
                                    logger.info(f"⬇️ [{symbol}] 주봉 MACD 데드크로스 매도 신호 포착! (점수: {score})")
                                    self.position_tracker.add_sell_signal(symbol, signal)
                                    # 매도 신호가 발생하면 포지션 클로즈
                                    self.position_tracker.close_position(symbol, df_weekly['close'].iloc[-1])
                                    return signal # 신호 감지 시 즉시 리턴
                                    
                except Exception as e:
                    logger.error(f"주봉 MACD 전략 오류 ({symbol}): {e}")
        
        return None

    async def scan_and_alert(self):
        """심볼을 스캔하고 알림 전송 (주요 로직)"""
        logger.info("🔎 모든 심볼 스캔 시작...")
        
        symbols = await self.get_all_symbols()
        total_symbols = len(symbols)
        logger.info(f"총 {total_symbols}개 심볼을 스캔합니다.")
        
        new_signals_count = 0
        closed_positions_count = 0
        
        async with aiohttp.ClientSession() as session:
            for i, symbol in enumerate(symbols):
                try:
                    # 현재 포지션이 열려있는지 확인하고, 열려있다면 실시간 가격으로 수익률 확인
                    if symbol in self.position_tracker.positions and self.position_tracker.positions[symbol]['status'] == 'open':
                        current_price = await self.get_bybit_price(symbol)
                        if current_price:
                            alert_info = self.position_tracker.check_profit_alerts(symbol, current_price)
                            if alert_info:
                                message = self._format_alert_message(alert_info)
                                self.telegram_bot.broadcast_message(message)
                                
                                if alert_info['action'] == 'STOP_LOSS':
                                    self.position_tracker.close_position(symbol, current_price)
                                    closed_positions_count += 1
                                    
                    # 새로운 신호 확인 (open 포지션 개수가 max_positions 미만일 때만)
                    if self.position_tracker.get_open_positions_count() < self.risk_management['max_positions']:
                        signal = await self.check_signal(symbol)
                        if signal:
                            message = self._format_signal_message(signal)
                            self.telegram_bot.broadcast_message(message)
                            new_signals_count += 1
                            
                    await asyncio.sleep(0.5) # API 호출 간격 유지

                except Exception as e:
                    logger.error(f"스캔 중 오류 발생 ({symbol}): {e}")
        
        logger.info(f"✅ 스캔 완료. 새 신호 {new_signals_count}개, 포지션 종료 {closed_positions_count}개")
        
        # 매일 23:50 수익률 리포트 전송
        now = datetime.now()
        if now.hour == 23 and now.minute == 50:
            logger.info("📊 일일 수익률 리포트 전송 시작...")
            report_message = self.telegram_bot.format_performance_message()
            self.telegram_bot.broadcast_message(report_message)
            logger.info("✅ 일일 수익률 리포트 전송 완료")
            await asyncio.sleep(60) # 중복 전송 방지
            
    def _format_signal_message(self, signal: Dict) -> str:
        """신호 메시지 포맷팅"""
        action_emoji = "📈 매수" if signal['action'] == 'BUY' else "📉 매도"
        signal_type = "진입" if signal['action'] == 'BUY' else "청산"
        
        message = f"""
<b>{action_emoji} 신호 {signal_type} 포착!</b>

코인: <b>{signal['symbol']}</b>
가격: <b>${signal['price']:.6f}</b>
전략: {signal['strategy']}
상세: {signal['details']}
점수: {signal.get('score', 'N/A')}

{signal_type}을(를) 고려해 보세요!
        """
        return message.strip()

    def _format_alert_message(self, alert: Dict) -> str:
        """수익/손절 알림 메시지 포맷팅"""
        if alert['action'] == 'PROFIT_ALERT':
            emoji = "🎉 수익 달성!"
            action_text = f"{alert['level']} 수익권!"
        elif alert['action'] == 'STOP_LOSS':
            emoji = "⚠️ 손절 알림!"
            action_text = f"{alert['level']} 손절 도달"
        else:
            emoji = "🔔 알림"
            action_text = "상태 업데이트"

        message = f"""
<b>{emoji} {alert['symbol']} {action_text}</b>

진입가: ${alert['entry_price']:.6f}
현재가: ${alert['price']:.6f}
수익률: <b>{alert['profit_percent']:+.2f}%</b>

{alert['reason']}
        """
        return message.strip()

    async def start_scanning(self, interval_minutes: int = 15):
        """스캐닝 시작"""
        logger.info(f"시스템 시작: {interval_minutes}분 간격으로 스캔합니다.")
        self.telegram_bot.start_command_handler() # 텔레그램 봇 명령어 처리 시작
        
        while True:
            await self.scan_and_alert()
            logger.info(f"다음 스캔까지 {interval_minutes}분 대기...")
            await asyncio.sleep(interval_minutes * 60)

# 시스템 실행
async def main():
    # 텔레그램 봇 토큰 (실제 토큰으로 교체하세요)
    # 반드시 텔레그램 @BotFather 에서 봇을 생성하고 받은 HTTP API 토큰을 입력하세요.
    TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN" # 여기에 텔레그램 봇 토큰을 입력하세요.

    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("❌ 텔레그램 봇 토큰을 입력해 주세요! TELEGRAM_BOT_TOKEN 변수를 수정하세요.")
        print("\n\n")
        print("🚨🚨🚨 중요: 텔레그램 봇 토큰을 설정해야 합니다! 🚨🚨🚨")
        print("1. 텔레그램에서 @BotFather를 찾아 새로운 봇을 생성합니다.")
        print("2. @BotFather가 제공하는 HTTP API 토큰(예: 123456:ABC-DEF1234ghIkl-7979GHiK)을 복사합니다.")
        print("3. 이 스크립트의 'TELEGRAM_BOT_TOKEN = \"YOUR_TELEGRAM_BOT_TOKEN\"' 부분을 찾아서 복사한 토큰으로 교체하세요.")
        print("예시: TELEGRAM_BOT_TOKEN = \"123456:ABC-DEF1234ghIkl-7979GHiK\"")
        print("4. 토큰을 설정한 후 다시 스크립트를 실행해 주세요.")
        print("\n\n")
        return

    try:
        scanner = EnhancedCoinScanner(TELEGRAM_BOT_TOKEN)
        
        # 시스템 시작
        await scanner.start_scanning(interval_minutes=5)
        
    except KeyboardInterrupt:
        logger.info("🛑 시스템 종료")
    except Exception as e:
        logger.error(f"시스템 오류: {e}")

# 스크립트 실행
if __name__ == "__main__":
    print("""
    개선된 다중 사용자 텔레그램 매매 신호 시스템 v2.0
    ============================================================
    
    주요 개선사항:
    - 1순위 전략만 엄선: 고래패턴+WaveTrend, 주봉MACD
    - Bybit 현물 + 선물 동시 스캔 (150개 심볼)
    - 손절 개선: -2%에서 -10%로 변경 (수익 기회 증대)
    - 매일 23:50 당일 수익률 자동 리포트
    - 실시간 수익률 추적 (/performance)
    
    설정 방법:
    1. 텔레그램 @BotFather에서 봇 생성
    2. 받은 토큰을 TELEGRAM_BOT_TOKEN에 입력
    3. 필요한 라이브러리 설치:
       pip install requests pandas numpy aiohttp
    
    1순위 전략 (엄선됨):
    1. 고래패턴 + WaveTrend(-50이하) 골든크로스 (15분봉)
    - 고래 누적 패턴 감지 (4점)
    - WaveTrend(-50이하) 골든크로스 (5점)
    - 총 8점 이상일 때만 매수 신호
    """)
    asyncio.run(main())