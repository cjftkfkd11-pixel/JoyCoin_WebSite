"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getApiBaseUrl } from '@/lib/apiBase';
import { useLanguage } from '@/lib/LanguageContext';

const maskEmail = (email: string) => {
  const [name, domain] = email.split('@');
  if (name.length <= 2) return `${name}***@${domain}`;
  return `${name.substring(0, 2)}***@${domain}`;
};

interface SectorStats {
  sector: { id: number; name: string; fee_percent: number };
  stats: {
    total_users: number;
    total_approved_deposits: number;
    fee_amount: number;
    approved_count: number;
    pending_count: number;
  };
}

interface DepositItem {
  id: number;
  user_email: string;
  user_username: string;
  chain: string;
  expected_amount: number;
  actual_amount: number | null;
  status: string;
  created_at: string;
}

export default function SectorDashboard() {
  const router = useRouter();
  const { t } = useLanguage();

  const [data, setData] = useState<SectorStats | null>(null);
  const [deposits, setDeposits] = useState<DepositItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const API_BASE_URL = getApiBaseUrl();

  useEffect(() => {
    fetchDashboard();
    fetchDeposits();
  }, []);

  const fetchDashboard = async () => {
    try {
      setIsLoading(true);
      const res = await fetch(`${API_BASE_URL}/sector/dashboard`, { credentials: 'include' });
      if (res.status === 401 || res.status === 403) { router.push('/sector/login'); return; }
      if (res.ok) setData(await res.json());
    } catch (err) { console.error(err); }
    finally { setIsLoading(false); }
  };

  const fetchDeposits = async (search?: string) => {
    try {
      const url = search
        ? `${API_BASE_URL}/sector/deposits?search=${encodeURIComponent(search)}`
        : `${API_BASE_URL}/sector/deposits`;
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) {
        const json = await res.json();
        setDeposits(json.items || []);
      }
    } catch (err) { console.error(err); }
  };

  const handleSearch = () => {
    fetchDeposits(searchQuery);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
      router.push('/sector/login');
    } catch (err) { router.push('/sector/login'); }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      approved: "bg-green-500/10 text-green-400 border-green-500/20",
      rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    return (
      <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${styles[status] || styles.pending}`}>
        {t(status as any) || status}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <p className="text-blue-500 font-black tracking-[0.5em] text-sm uppercase italic animate-pulse">{t("loading")}</p>
      </div>
    );
  }

  return (
    <div className="h-screen bg-[#020617] text-white flex flex-col overflow-hidden font-sans">
      {/* 헤더 */}
      <div className="flex-shrink-0 p-6 md:px-12 md:pt-8 border-b border-white/10">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-black italic tracking-tighter">
              <span className="text-blue-500">{t("sector")} {data?.sector.name}</span> {t("sectorDashboard")}
            </h1>
            <p className="text-slate-500 text-[10px] font-bold uppercase mt-1 tracking-[0.3em]">{t("sectorManager")}</p>
          </div>
          <button onClick={handleLogout} className="bg-red-500/10 border border-red-500/20 px-4 py-2 rounded-full text-[10px] font-black text-red-500 hover:bg-red-500/20 transition-all">
            {t("logout").toUpperCase()}
          </button>
        </div>
      </div>

      {/* 메인 컨텐츠 */}
      <div className="flex-1 overflow-y-auto p-6 md:px-12 md:pb-8">
        <div className="max-w-6xl mx-auto space-y-6">

          {/* 통계 카드 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
              <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest">{t("fee")}</p>
              <p className="text-3xl font-black italic text-blue-400 mt-2">{data?.sector.fee_percent}%</p>
            </div>
            <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
              <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest">{t("totalDeposits")}</p>
              <p className="text-3xl font-black italic text-green-400 mt-2">{data?.stats.total_approved_deposits?.toLocaleString()} <span className="text-xs">USDT</span></p>
            </div>
            <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
              <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest">{t("feeAmount")}</p>
              <p className="text-3xl font-black italic text-yellow-400 mt-2">{data?.stats.fee_amount?.toLocaleString()} <span className="text-xs">USDT</span></p>
            </div>
            <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
              <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest">{t("totalUsers")}</p>
              <p className="text-3xl font-black italic mt-2">{data?.stats.total_users}</p>
            </div>
          </div>

          {/* 검색 */}
          <div className="flex gap-3">
            <input
              type="text"
              placeholder={t("searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1 bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
            />
            <button
              onClick={handleSearch}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-black uppercase transition-all"
            >
              검색
            </button>
          </div>

          {/* 입금 내역 테이블 */}
          <div className="rounded-2xl overflow-hidden border border-white/5 bg-slate-900/20">
            {deposits.length === 0 ? (
              <div className="p-16 text-center text-slate-600 font-bold uppercase tracking-widest text-sm">
                입금 내역이 없습니다
              </div>
            ) : (
              <div className="max-h-[50vh] overflow-y-auto">
                <table className="w-full text-left">
                  <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] sticky top-0 z-10">
                    <tr>
                      <th className="p-5">ID</th>
                      <th className="p-5">유저</th>
                      <th className="p-5">네트워크</th>
                      <th className="p-5 text-right">금액</th>
                      <th className="p-5 text-center">상태</th>
                      <th className="p-5 text-right">요청일시</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm font-bold">
                    {deposits.map((dep) => (
                      <tr key={dep.id} className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                        <td className="p-5"><div className="font-mono text-xs text-slate-500">#{dep.id}</div></td>
                        <td className="p-5">
                          <div className="font-mono text-xs text-blue-300">{maskEmail(dep.user_email)}</div>
                          <div className="text-[9px] text-slate-600 mt-1">{dep.user_username}</div>
                        </td>
                        <td className="p-5">
                          <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-[10px] text-blue-400 font-black uppercase italic">{dep.chain}</span>
                        </td>
                        <td className="p-5 text-right font-mono italic text-slate-300">
                          {(dep.actual_amount || dep.expected_amount).toLocaleString()} USDT
                        </td>
                        <td className="p-5 text-center">{getStatusBadge(dep.status)}</td>
                        <td className="p-5 text-right text-slate-500 text-xs">{new Date(dep.created_at).toLocaleString('ko-KR')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <p className="text-slate-600 text-[10px] text-right">총 {deposits.length}건</p>
        </div>
      </div>
    </div>
  );
}
