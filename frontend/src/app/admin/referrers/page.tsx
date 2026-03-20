"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getApiBaseUrl } from '@/lib/apiBase';

interface Referrer {
  id: number;
  email: string;
  username: string;
  sector: string;
  invite_count: number;
  total_points: number;
  referral_reward_remaining: number;
}

export default function ReferrerManagement() {
  const router = useRouter();
  const API = getApiBaseUrl();
  const [referrers, setReferrers] = useState<Referrer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/admin/users/referrers`, { credentials: 'include' })
      .then(r => {
        if (r.status === 401 || r.status === 403) { router.push('/admin/login'); return null; }
        return r.json();
      })
      .then(data => { if (data) setReferrers(data); })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-[#020617] text-white p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push('/admin/dashboard')} className="text-slate-500 hover:text-white text-xl">←</button>
          <h1 className="text-3xl font-black italic text-green-500">REFERRER MANAGEMENT</h1>
          <span className="text-xs text-slate-500 font-mono">{referrers.length}명</span>
        </div>

        {loading ? (
          <div className="py-20 text-center text-blue-500 font-black animate-pulse tracking-widest">LOADING...</div>
        ) : referrers.length === 0 ? (
          <div className="py-20 text-center text-slate-600 font-bold uppercase tracking-widest">추천인 내역 없음</div>
        ) : (
          <div className="rounded-2xl overflow-hidden border border-white/5 bg-slate-900/20">
            <table className="w-full text-left">
              <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">
                <tr>
                  <th className="p-5">추천인</th>
                  <th className="p-5">섹터</th>
                  <th className="p-5 text-center">초대 수</th>
                  <th className="p-5 text-right">포인트</th>
                  <th className="p-5 text-center">남은 보상</th>
                </tr>
              </thead>
              <tbody className="text-sm font-bold divide-y divide-white/5">
                {referrers.map(ref => (
                  <tr key={ref.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="p-5">
                      <p className="font-mono text-xs text-blue-300">{ref.email}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">{ref.username}</p>
                    </td>
                    <td className="p-5">
                      <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-[10px] text-blue-400 font-black">
                        Sector {ref.sector}
                      </span>
                    </td>
                    <td className="p-5 text-center">
                      <span className="text-lg font-black text-white">{ref.invite_count}</span>
                      <span className="text-xs text-slate-500 ml-1">명</span>
                    </td>
                    <td className="p-5 text-right font-mono italic text-green-400">
                      {ref.total_points.toLocaleString()} P
                    </td>
                    <td className="p-5 text-center">
                      {ref.referral_reward_remaining > 0 ? (
                        <span className="px-2 py-1 bg-yellow-500/10 border border-yellow-500/20 rounded-full text-[10px] text-yellow-400 font-black">
                          {ref.referral_reward_remaining}회 남음
                        </span>
                      ) : (
                        <span className="text-slate-600 text-[10px]">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
