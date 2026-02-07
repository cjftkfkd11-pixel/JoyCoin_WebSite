"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLanguage } from '@/lib/LanguageContext';
import { useAuth } from '@/lib/AuthContext';

export default function MyPage() {
  const router = useRouter();
  const { t, locale } = useLanguage();
  const { user, isLoggedIn, isLoading: authLoading, logout } = useAuth();

  const [deposits, setDeposits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

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
          setDeposits(depositData.items || depositData);
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
    router.push('/auth/login');
  };

  if (authLoading || loading) return <div className="min-h-screen bg-[#020617] flex items-center justify-center text-white font-black italic">{t("loading").toUpperCase()}</div>;

  return (
    <div className="min-h-screen bg-[#020617] text-white p-8 font-sans">
      <div className="max-w-4xl mx-auto">

        {/* 헤더 */}
        <div className="flex justify-between items-center mb-12">
          <h1 className="text-4xl font-black italic text-blue-500 uppercase tracking-tighter">{t("myPage")}</h1>
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <div className="glass p-8 rounded-[2rem] border border-blue-500/10 shadow-xl bg-slate-900/40">
            <h2 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] mb-4">{t("myInfo")}</h2>
            <p className="text-2xl font-black mb-2">{user?.username || 'User'}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
            {user?.referral_code && (
              <p className="text-xs text-slate-600 mt-2">{t("myReferralCode")}: {user.referral_code}</p>
            )}
          </div>

          <div className="glass p-8 rounded-[2rem] border border-blue-500/10 shadow-xl bg-gradient-to-br from-blue-600/20 to-transparent">
            <h2 className="text-[10px] font-bold text-slate-300 uppercase tracking-[0.3em] mb-4">{t("totalJoy")}</h2>
            <p className="text-4xl font-black text-blue-400 mb-6">{user?.total_joy?.toLocaleString() || '0'} <span className="text-xs">JOY</span></p>
            <button
              onClick={() => router.push('/buy')}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-black text-sm transition-all shadow-lg shadow-blue-900/30"
            >
              {locale === 'ko' ? 'JOY 충전하기' : 'CHARGE JOY'}
            </button>
          </div>
        </div>

        {/* 입금 내역 목록 */}
        <div className="glass p-8 rounded-[2.5rem] border border-slate-800/50 bg-slate-900/20 shadow-2xl">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-[0.2em] mb-8">{t("depositHistory")}</h2>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] text-slate-600 uppercase border-b border-slate-800">
                  <th className="pb-4 font-black">ID</th>
                  <th className="pb-4 font-black">{t("amount")}</th>
                  <th className="pb-4 font-black">JOY</th>
                  <th className="pb-4 font-black">{t("chain")}</th>
                  <th className="pb-4 font-black">{t("status")}</th>
                  <th className="pb-4 font-black text-right">{t("requestTime")}</th>
                </tr>
              </thead>
              <tbody className="text-xs">
                {deposits.length > 0 ? (
                  deposits.map((dep) => (
                    <tr key={dep.id} className="border-b border-slate-800/30 hover:bg-white/5 transition-colors">
                      <td className="py-4 font-mono text-slate-500">{dep.id.toString().slice(0, 8)}</td>
                      <td className="py-4 font-black">{dep.expected_amount} USDT</td>
                      <td className="py-4 font-black text-blue-400">{(dep.joy_amount || 0).toLocaleString()} JOY</td>
                      <td className="py-4 text-slate-400">{dep.chain}</td>
                      <td className="py-4">{getStatusBadge(dep.status)}</td>
                      <td className="py-4 text-right text-slate-500">
                        {new Date(dep.created_at).toLocaleDateString()}
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
