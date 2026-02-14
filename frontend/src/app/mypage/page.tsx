"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLanguage } from '@/lib/LanguageContext';
import { useAuth } from '@/lib/AuthContext';
import { useToast } from '@/components/Toast';
import { getApiBaseUrl } from '@/lib/apiBase';
import { copyText } from '@/lib/clipboard';

export default function MyPage() {
  const router = useRouter();
  const { t, locale } = useLanguage();
  const { user, isLoggedIn, isLoading: authLoading, logout } = useAuth();
  const { toast } = useToast();

  const [deposits, setDeposits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  // 비밀번호 변경 상태
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState({ type: '', text: '' });

  // 지갑 주소 변경 상태
  const [showWalletModal, setShowWalletModal] = useState(false);
  const [newWalletAddress, setNewWalletAddress] = useState("");
  const [walletLoading, setWalletLoading] = useState(false);
  const [walletMessage, setWalletMessage] = useState({ type: '', text: '' });

  // 알림 상태
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);

  const API_BASE_URL = getApiBaseUrl();

  useEffect(() => {
    if (authLoading) return;
    if (!isLoggedIn) {
      router.push('/auth/login');
      return;
    }

    const fetchDeposits = async () => {
      try {
        setLoading(true);
        const depositRes = await fetch(`${API_BASE_URL}/deposits/my`, { credentials: 'include' });
        if (depositRes.ok) {
          const depositData = await depositRes.json();
          const items = depositData.items || depositData;
          setDeposits(items);

          // 알림 확인: 최근 승인/거절된 내역 중 아직 확인하지 않은 것
          const seenNotifs = JSON.parse(localStorage.getItem('seenNotifications') || '[]');
          const newNotifs = items.filter((dep: any) =>
            (dep.status === 'approved' || dep.status === 'rejected') &&
            !seenNotifs.includes(dep.id)
          );
          setNotifications(newNotifs);
          if (newNotifs.length > 0 && window.innerWidth >= 1024) {
            setShowNotifications(true);
          }
        }
      } catch (err) {
        console.error("데이터 로드 실패:", err);
        setErrorMessage(locale === 'ko' ? "서버와 통신하는 중 문제가 발생했습니다." : "Failed to communicate with server.");
      } finally {
        setLoading(false);
      }
    };

    fetchDeposits();
  }, [authLoading, isLoggedIn, router, locale]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending': return <span className="px-2 py-1 bg-yellow-500/20 text-yellow-500 text-[10px] font-bold rounded-md">{t("pending").toUpperCase()}</span>;
      case 'approved': return <span className="px-2 py-1 bg-green-500/20 text-green-500 text-[10px] font-bold rounded-md">{t("approved").toUpperCase()}</span>;
      case 'rejected': return <span className="px-2 py-1 bg-red-500/20 text-red-500 text-[10px] font-bold rounded-md">{t("rejected").toUpperCase()}</span>;
      default: return <span className="text-slate-500">{status}</span>;
    }
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = '/';
  };

  const copyToClipboard = async (text: string, successMessage: string) => {
    const copied = await copyText(text);
    if (copied) {
      toast(successMessage, 'success');
    } else {
      toast(locale === 'ko' ? '복사에 실패했습니다.' : 'Copy failed.', 'error');
    }
  };

  const handleChangeWallet = async () => {
    if (!newWalletAddress.trim() || newWalletAddress.trim().length < 6) {
      setWalletMessage({ type: 'error', text: locale === 'ko' ? '유효한 지갑 주소를 입력하세요 (6자 이상).' : 'Enter a valid wallet address (min 6 chars).' });
      return;
    }
    setWalletLoading(true);
    setWalletMessage({ type: '', text: '' });
    try {
      const res = await fetch(`${API_BASE_URL}/auth/wallet-address`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ wallet_address: newWalletAddress.trim() })
      });
      if (res.ok) {
        setWalletMessage({ type: 'success', text: locale === 'ko' ? '지갑 주소가 변경되었습니다.' : 'Wallet address updated.' });
        setTimeout(() => { setShowWalletModal(false); window.location.reload(); }, 1200);
      } else {
        const error = await res.json();
        setWalletMessage({ type: 'error', text: error.detail || (locale === 'ko' ? '변경 실패' : 'Update failed') });
      }
    } catch {
      setWalletMessage({ type: 'error', text: locale === 'ko' ? '서버 연결 실패' : 'Server connection failed' });
    } finally {
      setWalletLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setPasswordMessage({ type: 'error', text: locale === 'ko' ? '새 비밀번호가 일치하지 않습니다.' : 'New passwords do not match.' });
      return;
    }
    if (newPassword.length < 6) {
      setPasswordMessage({ type: 'error', text: locale === 'ko' ? '비밀번호는 6자 이상이어야 합니다.' : 'Password must be at least 6 characters.' });
      return;
    }

    setPasswordLoading(true);
    setPasswordMessage({ type: '', text: '' });

    try {
      const res = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      if (res.ok) {
        setPasswordMessage({ type: 'success', text: locale === 'ko' ? '비밀번호가 변경되었습니다.' : 'Password changed successfully.' });
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setTimeout(() => setShowPasswordModal(false), 1500);
      } else {
        const error = await res.json();
        setPasswordMessage({ type: 'error', text: error.detail || (locale === 'ko' ? '비밀번호 변경 실패' : 'Failed to change password') });
      }
    } catch {
      setPasswordMessage({ type: 'error', text: locale === 'ko' ? '서버 연결 실패' : 'Server connection failed' });
    } finally {
      setPasswordLoading(false);
    }
  };

  if (authLoading || loading) return <div className="min-h-screen bg-[#020617] flex items-center justify-center text-white font-black italic">{t("loading").toUpperCase()}</div>;

  return (
    <div className="min-h-screen bg-[#020617] text-white p-4 sm:p-8 pb-24 font-sans">
      {/* 알림 모달 */}
      {showNotifications && notifications.length > 0 && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 sm:p-6">
          <div className="glass p-5 sm:p-8 rounded-2xl sm:rounded-[2rem] w-full max-w-md border border-blue-500/20 shadow-2xl relative max-h-[95vh] overflow-y-auto">
            <h2 className="text-lg sm:text-xl font-black text-blue-500 mb-4 sm:mb-6 flex items-center gap-2">
              <span className="text-xl sm:text-2xl">🔔</span>
              {locale === 'ko' ? '알림' : 'Notifications'}
            </h2>
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  className={`p-4 rounded-xl border ${
                    notif.status === 'approved'
                      ? 'bg-green-500/10 border-green-500/20'
                      : 'bg-red-500/10 border-red-500/20'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">{notif.status === 'approved' ? '✅' : '❌'}</span>
                    <span className={`text-sm font-black ${notif.status === 'approved' ? 'text-green-400' : 'text-red-400'}`}>
                      {notif.status === 'approved'
                        ? (locale === 'ko' ? '입금 승인됨' : 'Deposit Approved')
                        : (locale === 'ko' ? '입금 거절됨' : 'Deposit Rejected')
                      }
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    {notif.expected_amount} USDT → {(notif.joy_amount || 0).toLocaleString()} JOY
                  </p>
                </div>
              ))}
            </div>
            <button
              onClick={() => {
                const seenNotifs = JSON.parse(localStorage.getItem('seenNotifications') || '[]');
                const newSeen = [...seenNotifs, ...notifications.map((n: any) => n.id)];
                localStorage.setItem('seenNotifications', JSON.stringify(newSeen));
                setShowNotifications(false);
                setNotifications([]);
              }}
              className="mt-6 w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-black transition-all"
            >
              {locale === 'ko' ? '확인' : 'OK'}
            </button>
          </div>
        </div>
      )}

      {/* 지갑 주소 변경 모달 */}
      {showWalletModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 sm:p-6">
          <div className="glass p-5 sm:p-8 rounded-2xl sm:rounded-[2rem] w-full max-w-md border border-yellow-500/20 shadow-2xl relative max-h-[95vh] overflow-y-auto">
            <button
              onClick={() => setShowWalletModal(false)}
              className="absolute top-3 right-3 sm:top-4 sm:right-4 text-slate-500 hover:text-white text-xl font-bold"
            >
              ×
            </button>
            <h2 className="text-xl font-black text-yellow-400 mb-6">
              {locale === 'ko' ? '지갑 주소 변경' : 'Change Wallet Address'}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">
                  {locale === 'ko' ? '새 지갑 주소' : 'New Wallet Address'}
                </label>
                <input
                  type="text"
                  value={newWalletAddress}
                  onChange={(e) => setNewWalletAddress(e.target.value)}
                  placeholder={locale === 'ko' ? 'JOY를 받을 지갑 주소 입력' : 'Enter wallet address for JOY'}
                  className="w-full bg-slate-900/50 border border-slate-700 p-3 rounded-xl outline-none focus:border-yellow-500 text-sm font-mono"
                />
              </div>
              <p className="text-[9px] text-yellow-600">
                {locale === 'ko' ? '⚠️ 잘못된 주소 입력 시 JOY를 받지 못할 수 있습니다. 정확히 입력하세요.' : '⚠️ Incorrect address may result in lost JOY. Please double-check.'}
              </p>
              {walletMessage.text && (
                <div className={`p-3 rounded-xl text-xs font-bold text-center ${
                  walletMessage.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                }`}>
                  {walletMessage.text}
                </div>
              )}
              <button
                onClick={handleChangeWallet}
                disabled={walletLoading}
                className="w-full py-3 bg-yellow-600 hover:bg-yellow-500 disabled:bg-slate-700 rounded-xl font-black transition-all"
              >
                {walletLoading ? t("loading") : (locale === 'ko' ? '변경하기' : 'Update')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 비밀번호 변경 모달 */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 sm:p-6">
          <div className="glass p-5 sm:p-8 rounded-2xl sm:rounded-[2rem] w-full max-w-md border border-blue-500/20 shadow-2xl relative max-h-[95vh] overflow-y-auto">
            <button
              onClick={() => { setShowPasswordModal(false); setPasswordMessage({ type: '', text: '' }); }}
              className="absolute top-3 right-3 sm:top-4 sm:right-4 text-slate-500 hover:text-white text-xl font-bold"
            >
              ×
            </button>
            <h2 className="text-xl font-black text-blue-500 mb-6">
              {locale === 'ko' ? '비밀번호 변경' : 'Change Password'}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">
                  {locale === 'ko' ? '현재 비밀번호' : 'Current Password'}
                </label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700 p-3 rounded-xl outline-none focus:border-blue-500 text-sm"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">
                  {locale === 'ko' ? '새 비밀번호 (6자 이상)' : 'New Password (min 6 chars)'}
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700 p-3 rounded-xl outline-none focus:border-blue-500 text-sm"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">
                  {locale === 'ko' ? '새 비밀번호 확인' : 'Confirm New Password'}
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700 p-3 rounded-xl outline-none focus:border-blue-500 text-sm"
                />
              </div>
              {passwordMessage.text && (
                <div className={`p-3 rounded-xl text-xs font-bold text-center ${
                  passwordMessage.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                }`}>
                  {passwordMessage.text}
                </div>
              )}
              <button
                onClick={handleChangePassword}
                disabled={passwordLoading}
                className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 rounded-xl font-black transition-all"
              >
                {passwordLoading ? t("loading") : (locale === 'ko' ? '변경하기' : 'Change')}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-4xl mx-auto">

        {/* 헤더 */}
        <div className="flex justify-between items-center mb-6 sm:mb-12">
          <h1 className="text-2xl sm:text-4xl font-black italic text-blue-500 uppercase tracking-tighter">{t("myPage")}</h1>
          <button
            onClick={handleLogout}
            className="text-xs font-bold text-red-500 hover:text-red-400 transition-all underline underline-offset-8"
          >
            {t("logout").toUpperCase()}
          </button>
        </div>

        {/* 에러 메시지 */}
        {errorMessage && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-xs text-center rounded-2xl font-bold">
            {errorMessage}
          </div>
        )}

        {/* 상단 카드: 잔액 및 정보 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 mb-6 sm:mb-12">
          <div className="glass p-5 sm:p-8 rounded-2xl sm:rounded-[2rem] border border-blue-500/10 shadow-xl bg-slate-900/40">
            <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] mb-4">{t("myInfo")}</h2>
            <p className="text-xl sm:text-2xl font-black mb-2">{user?.username || 'User'}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
            {user?.referral_code && (
              <div className="mt-4 p-3 bg-slate-800/50 rounded-xl">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{t("myReferralCode")}</p>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-mono font-bold text-blue-400">{user.referral_code}</span>
                  <button
                    type="button"
                    onClick={() => {
                      copyToClipboard(
                        user.referral_code || '',
                        locale === 'ko' ? '복사되었습니다!' : 'Copied!'
                      );
                    }}
                    className="text-[10px] font-bold text-blue-400 hover:text-blue-300 px-3 py-1 bg-blue-500/10 rounded-lg hover:bg-blue-500/20 transition-all touch-manipulation"
                  >
                    {locale === 'ko' ? '복사' : 'COPY'}
                  </button>
                </div>
              </div>
            )}
            {user?.recovery_code && (
              <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
                <p className="text-[10px] text-yellow-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                  <span>🔑</span>
                  {locale === 'ko' ? '복구 코드 (계정 찾기용)' : 'Recovery Code'}
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-mono font-bold text-yellow-300">{user.recovery_code}</span>
                  <button
                    type="button"
                    onClick={() => {
                      copyToClipboard(
                        user.recovery_code || '',
                        locale === 'ko' ? '복사되었습니다! 안전한 곳에 보관하세요.' : 'Copied! Keep it safe.'
                      );
                    }}
                    className="text-[10px] font-bold text-yellow-400 hover:text-yellow-300 px-3 py-1 bg-yellow-500/10 rounded-lg hover:bg-yellow-500/20 transition-all touch-manipulation"
                  >
                    {locale === 'ko' ? '복사' : 'COPY'}
                  </button>
                </div>
                <p className="text-[9px] text-yellow-600 mt-2">
                  {locale === 'ko' ? '⚠️ 이 코드로 아이디/비밀번호를 찾을 수 있습니다. 절대 타인에게 공유하지 마세요!' : '⚠️ Use this code to recover your account. Never share it!'}
                </p>
              </div>
            )}
            {/* 지갑 주소 */}
            <div className="mt-4 p-3 bg-slate-800/50 rounded-xl">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">
                {locale === 'ko' ? 'JOY 수령 지갑 주소' : 'JOY Wallet Address'}
              </p>
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-mono text-blue-400 truncate flex-1">
                  {user?.wallet_address || (locale === 'ko' ? '미등록' : 'Not set')}
                </span>
                <div className="flex gap-1 flex-shrink-0">
                  {user?.wallet_address && (
                    <button
                      type="button"
                      onClick={() => copyToClipboard(user.wallet_address || '', locale === 'ko' ? '복사되었습니다!' : 'Copied!')}
                      className="text-[10px] font-bold text-blue-400 hover:text-blue-300 px-2 py-1 bg-blue-500/10 rounded-lg hover:bg-blue-500/20 transition-all touch-manipulation"
                    >
                      {locale === 'ko' ? '복사' : 'COPY'}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => { setNewWalletAddress(user?.wallet_address || ''); setShowWalletModal(true); setWalletMessage({ type: '', text: '' }); }}
                    className="text-[10px] font-bold text-yellow-400 hover:text-yellow-300 px-2 py-1 bg-yellow-500/10 rounded-lg hover:bg-yellow-500/20 transition-all touch-manipulation"
                  >
                    {locale === 'ko' ? '변경' : 'EDIT'}
                  </button>
                </div>
              </div>
            </div>

            <button
              onClick={() => setShowPasswordModal(true)}
              className="mt-4 w-full py-2 text-xs font-bold text-slate-400 hover:text-white bg-slate-800/50 hover:bg-slate-700/50 rounded-xl transition-all"
            >
              {locale === 'ko' ? '비밀번호 변경' : 'Change Password'}
            </button>
          </div>

          <div className="glass p-5 sm:p-8 rounded-2xl sm:rounded-[2rem] border border-blue-500/10 shadow-xl bg-gradient-to-br from-blue-600/20 to-transparent">
            <h2 className="text-[10px] font-bold text-slate-300 uppercase tracking-[0.3em] mb-4">{t("totalJoy")}</h2>
            <p className="text-2xl sm:text-4xl font-black text-blue-400 mb-2">{user?.total_joy?.toLocaleString() || '0'} <span className="text-xs">JOY</span></p>

            {/* 포인트 잔액 */}
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">{t("totalPoints")}</span>
              <span className="text-sm font-black text-green-400">{user?.total_points?.toLocaleString() || '0'} P</span>
            </div>

            {/* 남은 추천 보상 횟수 */}
            {(user?.referral_reward_remaining ?? 0) > 0 && (
              <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-green-400 uppercase tracking-wider">{t("referralRewardRemaining")}</span>
                  <span className="text-sm font-black text-green-400">{user?.referral_reward_remaining}{locale === 'ko' ? '회' : 'x'}</span>
                </div>
                <p className="text-[9px] text-green-600 mt-1">{t("referralRewardDesc")}</p>
              </div>
            )}

            <button
              type="button"
              onClick={() => { window.location.href = '/buy'; }}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-black text-sm transition-all shadow-lg shadow-blue-900/30 touch-manipulation"
            >
              {locale === 'ko' ? 'JOY 충전하기' : 'CHARGE JOY'}
            </button>
          </div>
        </div>

        {/* 입금 내역 목록 */}
        <div className="glass p-4 sm:p-8 rounded-2xl sm:rounded-[2.5rem] border border-slate-800/50 bg-slate-900/20 shadow-2xl">
          <h2 className="text-xs sm:text-sm font-bold text-slate-400 uppercase tracking-[0.2em] mb-4 sm:mb-8">{t("depositHistory")}</h2>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[9px] sm:text-[10px] text-slate-600 uppercase border-b border-slate-800">
                  <th className="pb-3 sm:pb-4 font-black pr-2">ID</th>
                  <th className="pb-3 sm:pb-4 font-black pr-2">{t("amount")}</th>
                  <th className="pb-3 sm:pb-4 font-black pr-2">JOY</th>
                  <th className="pb-3 sm:pb-4 font-black pr-2">{t("chain")}</th>
                  <th className="pb-3 sm:pb-4 font-black pr-2">{t("status")}</th>
                  <th className="pb-3 sm:pb-4 font-black text-right">{t("requestTime")}</th>
                </tr>
              </thead>
              <tbody className="text-[11px] sm:text-xs">
                {deposits.length > 0 ? (
                  deposits.map((dep) => (
                    <tr key={dep.id} className="border-b border-slate-800/30 hover:bg-white/5 transition-colors">
                      <td className="py-3 sm:py-4 font-mono text-slate-500 pr-2">{dep.id.toString().slice(0, 6)}</td>
                      <td className="py-3 sm:py-4 font-black pr-2 whitespace-nowrap">{dep.expected_amount} USDT</td>
                      <td className="py-3 sm:py-4 font-black text-blue-400 pr-2 whitespace-nowrap">{(dep.joy_amount || 0).toLocaleString()}</td>
                      <td className="py-3 sm:py-4 text-slate-400 pr-2">{dep.chain}</td>
                      <td className="py-3 sm:py-4 pr-2">{getStatusBadge(dep.status)}</td>
                      <td className="py-3 sm:py-4 text-right text-slate-500 whitespace-nowrap">
                        {new Date(dep.created_at).toLocaleString(locale === 'ko' ? 'ko-KR' : 'en-US', {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-20 text-center text-slate-600 italic">
                      {t("noDeposits")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
