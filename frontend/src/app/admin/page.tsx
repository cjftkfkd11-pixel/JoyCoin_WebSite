"use client";

import React, { useState } from 'react';
import { useLanguage } from '@/lib/LanguageContext';

export default function FullAdminDashboard() {
  const { t } = useLanguage();
  // 1. 섹터별 설정 및 통계 (A~D)
  const [sectorData, setSectorData] = useState({
    "Sector A": { rate: 10, members: 124, totalSync: 45000 },
    "Sector B": { rate: 15, members: 89, totalSync: 32000 },
    "Sector C": { rate: 5, members: 210, totalSync: 67000 },
    "Sector D": { rate: 20, members: 45, totalSync: 15000 },
  });

  // 2. 추천인 데이터 (E, F, G, H)
  const [referrers] = useState([
    { email: "referrer_E@joy.com", sector: "Sector A", invites: 12, rewards: 1200 },
    { email: "referrer_F@joy.com", sector: "Sector B", invites: 8, rewards: 950 },
    { email: "referrer_G@joy.com", sector: "Sector C", invites: 25, rewards: 3100 },
    { email: "referrer_H@joy.com", sector: "Sector D", invites: 4, rewards: 400 },
  ]);

  // 3. 실시간 활성화 요청 목록
  const [requests, setRequests] = useState([
    { id: 1, user: "user01@test.com", sector: "Sector A", referrer: "E", power: 1000, status: "pending" },
    { id: 2, user: "test99@joy.com", sector: "Sector B", referrer: "F", power: 500, status: "pending" },
  ]);

  const rates = [5, 10, 15, 20, 25];

  // 기여분율 변경 함수
  const changeRate = (sector: string, newRate: number) => {
    setSectorData(prev => ({
      ...prev,
      [sector]: { ...prev[sector as keyof typeof prev], rate: newRate }
    }));
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white p-4 md:p-10 font-sans">
      <div className="max-w-7xl mx-auto space-y-12">
        
        {/* 상단 타이틀 */}
        <div className="flex justify-between items-end border-b border-white/10 pb-6">
          <div>
            <h1 className="text-4xl font-black italic tracking-tighter text-blue-500">{t("adminSystemControl")}</h1>
            <p className="text-slate-500 text-xs font-bold uppercase tracking-widest mt-1">{t("adminGlobalNodeReferrer")}</p>
          </div>
        </div>

        {/* [섹션 1] 섹터별 기여분 및 통계 (A~D) */}
        <div className="space-y-4">
          <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] pl-2">{t("sectorConfiguration")}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Object.entries(sectorData).map(([name, data]) => (
              <div key={name} className="glass p-6 rounded-[2.5rem] border-white/5 space-y-4 relative overflow-hidden bg-slate-900/40">
                <div className="flex justify-between items-center">
                  <span className="text-blue-500 font-black italic">{name}</span>
                  <span className="text-[10px] text-green-400 font-bold bg-green-400/10 px-2 py-1 rounded">{t("online").toUpperCase()}</span>
                </div>
                
                <div className="grid grid-cols-2 gap-4 border-y border-white/5 py-3">
                  <div>
                    <p className="text-slate-500 text-[9px] uppercase font-bold">{t("members")}</p>
                    <p className="text-xl font-black">{data.members} <span className="text-[10px] font-normal">{t("peopleUnit")}</span></p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-[9px] uppercase font-bold">{t("totalSync")}</p>
                    <p className="text-xl font-black">{data.totalSync.toLocaleString()} <span className="text-[10px] font-normal text-blue-400">U</span></p>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-slate-500 text-[9px] uppercase font-bold text-center">{t("contribution")}: {data.rate}%</p>
                  <div className="flex justify-between gap-1">
                    {rates.map(r => (
                      <button 
                        key={r}
                        onClick={() => changeRate(name, r)}
                        className={`flex-1 py-2 text-[10px] font-black rounded-lg transition-all ${data.rate === r ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' : 'bg-white/5 text-slate-500 hover:bg-white/10'}`}
                      >
                        {r}%
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* [섹션 2] 추천인 관리 (E, F, G, H) */}
        <div className="space-y-4">
          <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] pl-2">{t("referrerNetwork")}</h2>
          <div className="glass rounded-[2rem] overflow-hidden border-white/5 bg-slate-900/40">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-widest">
                <tr>
                  <th className="p-5">{t("referrerId")}</th>
                  <th className="p-5">Sector</th>
                  <th className="p-5 text-center">{t("invites")}</th>
                  <th className="p-5 text-right">{t("totalRewardsU")}</th>
                </tr>
              </thead>
              <tbody>
                {referrers.map((ref, idx) => (
                  <tr key={idx} className="border-t border-white/5 hover:bg-white/[0.02]">
                    <td className="p-5 font-mono text-xs">{ref.email}</td>
                    <td className="p-5 font-black text-blue-400">{ref.sector}</td>
                    <td className="p-5 text-center font-bold">{ref.invites} {t("peopleUnit")}</td>
                    <td className="p-5 text-right font-black text-green-400">{ref.rewards.toLocaleString()} U</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* [섹션 3] 실시간 활성화 요청 목록 */}
        <div className="space-y-4">
          <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] pl-2">{t("activationRequests")}</h2>
          <div className="glass rounded-[2rem] overflow-hidden border-white/5 bg-slate-900/40 shadow-2xl">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-widest">
                <tr>
                  <th className="p-6">{t("userDate")}</th>
                  <th className="p-6">{t("agent")}</th>
                  <th className="p-6 text-right">{t("uPower")}</th>
                  <th className="p-6 text-center text-blue-400 font-black">{t("expectedContribution")}</th>
                  <th className="p-6 text-right">{t("actions")}</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((req) => {
                  const currentRate = sectorData[req.sector as keyof typeof sectorData].rate;
                  const fee = (req.power * currentRate) / 100;
                  return (
                    <tr key={req.id} className="border-t border-white/5 hover:bg-white/[0.02]">
                      <td className="p-6">
                        <div className="font-bold">{req.user}</div>
                        <div className="text-[10px] text-slate-500 uppercase mt-1">{req.sector}</div>
                      </td>
                      <td className="p-6">
                        <span className="bg-white/5 px-3 py-1 rounded-full text-[10px] text-slate-400">{t("agent")} {req.referrer}</span>
                      </td>
                      <td className="p-6 text-right font-mono font-bold">{req.power.toLocaleString()} U</td>
                      <td className="p-6 text-center text-blue-400 font-black">+{fee.toFixed(2)} U <br/><span className="text-[9px] text-slate-600">at {currentRate}%</span></td>
                      <td className="p-6 text-right">
                        <button className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-black rounded-xl transition-all shadow-lg shadow-blue-500/20 active:scale-95">
                          APPROVE & SYNC
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
