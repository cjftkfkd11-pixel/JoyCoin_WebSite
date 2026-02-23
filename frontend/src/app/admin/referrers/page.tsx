"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLanguage } from '@/lib/LanguageContext';

export default function ReferrerManagement() {
  const router = useRouter();
  const { t } = useLanguage();

  // 테스트용 추천인 데이터
  const [referrers] = useState([
    { email: "top_leader@gmail.com", sector: "Sector_A", invited_count: 12, total_points: 1250 },
    { email: "joy_master@naver.com", sector: "Sector_B", invited_count: 5, total_points: 450 },
  ]);

  return (
    <div className="min-h-screen bg-[#020617] text-white p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center gap-4">
          <button onClick={() => router.back()} className="text-slate-500 hover:text-white">←</button>
          <h1 className="text-3xl font-black italic text-green-500">{t("referrerList").toUpperCase()}</h1>
        </div>

        <div className="glass rounded-[2rem] overflow-hidden border-white/5">
          <table className="w-full text-left">
            <thead className="bg-white/5 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              <tr>
                <th className="p-6">{t("email")}</th>
                <th className="p-6">{t("sector")}</th>
                <th className="p-6">{t("invitedUsers")}</th>
                <th className="p-6">{t("totalPointsU")}</th>
                <th className="p-6">{t("status")}</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {referrers.map((ref, idx) => (
                <tr key={idx} className="border-t border-white/5 hover:bg-white/[0.02]">
                  <td className="p-6 font-mono">{ref.email}</td>
                  <td className="p-6 text-blue-400 font-bold">{ref.sector}</td>
                  <td className="p-6">{ref.invited_count}</td>
                  <td className="p-6 text-green-400 font-black">{ref.total_points.toLocaleString()} U</td>
                  <td className="p-6">
                    <span className="px-3 py-1 bg-green-500/10 text-green-500 border border-green-500/20 rounded-full text-[9px] font-black uppercase">
                      {t("active")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}