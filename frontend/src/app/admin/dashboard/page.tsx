"use client";

import React, { useState, useMemo, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// --- [Helper Functions] ---
const maskEmail = (email: string) => {
  const [name, domain] = email.split('@');
  if (name.length <= 2) return `${name}***@${domain}`;
  return `${name.substring(0, 2)}***@${domain}`;
};

// HttpOnly 쿠키를 사용하므로 getCookie, deleteCookie 함수는 불필요

export default function AdminDashboard() {
  const router = useRouter();

  // --- [States] ---
  const [sectorRates, setSectorRates] = useState<Record<string, number>>({
    "Sector A": 10, "Sector B": 15, "Sector C": 5, "Sector D": 20
  });
  
  const [requests, setRequests] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [securityLogs, setSecurityLogs] = useState([
    { id: 1, action: "Admin System Initialized", time: new Date().toLocaleTimeString(), status: "Success" },
  ]);

  const sectors = ["Sector A", "Sector B", "Sector C", "Sector D"];
  const rateOptions = [5, 10, 15, 20, 25];

  // --- [Data Fetching] ---
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE_URL}/admin/requests`, {
          credentials: 'include'
        });

        if (!response.ok) throw new Error('서버 데이터를 가져올 수 없습니다.');

        const data = await response.json();
        setRequests(data);
      } catch (err: any) {
        setError(err.message);
        // 개발 중 테스트를 위해 데이터가 없을 때 가짜 데이터를 유지하고 싶다면 아래 주석을 해제하세요.
        // setRequests([...가짜데이터]); 
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // --- [Logic] ---
  const sectorStats = useMemo(() => {
    return sectors.map(name => {
      const filtered = requests.filter(r => r.sector === name);
      const totalPower = filtered.reduce((sum, current) => sum + current.power, 0);
      const memberCount = filtered.length;
      const currentRate = sectorRates[name];
      const totalFee = (totalPower * currentRate) / 100;

      return { name, totalPower, totalFee, currentRate, memberCount };
    });
  }, [sectorRates, requests]);

  const handleApprove = async (id: number, user: string) => {
    if(!confirm(`${maskEmail(user)} 요청을 승인하시겠습니까?`)) return;

    try {
      // 실제 API 연동 시: await fetch(`.../approve/${id}`, { method: 'POST' })
      setRequests(prev => prev.map(r => r.id === id ? { ...r, status: "active" } : r));
      setSecurityLogs(prev => [
        { id: Date.now(), action: `Approved: ${maskEmail(user)}`, time: new Date().toLocaleTimeString(), status: "Verified" },
        ...prev
      ]);
    } catch (err) {
      alert("승인 처리 중 오류가 발생했습니다.");
    }
  };

  const handleLogout = async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      alert("로그아웃 되었습니다.");
      router.push('/admin/login');
    } catch (err) {
      console.error("로그아웃 실패:", err);
      router.push('/admin/login');
    }
  };

  // --- [Render Conditions] ---
  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6 text-center">
        <div className="glass p-10 rounded-[2.5rem] border-red-500/20 max-w-md w-full">
          <h2 className="text-red-500 font-black mb-4 uppercase tracking-widest text-xl">System Error</h2>
          <p className="text-slate-400 text-sm mb-6">{error}</p>
          <button onClick={() => window.location.reload()} className="w-full py-4 bg-red-600/20 text-red-500 font-black rounded-2xl hover:bg-red-600 hover:text-white transition-all">RETRY CONNECTION</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white p-6 md:p-12 overflow-y-auto font-sans">
      <div className="max-w-7xl mx-auto space-y-12">
        
        {/* 헤더 */}
        <div className="border-b border-white/10 pb-8 flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-black italic tracking-tighter text-blue-500 uppercase">
              Sector <span className="text-white">Management</span>
            </h1>
            <p className="text-slate-500 text-[10px] font-bold uppercase mt-2 tracking-[0.3em]">실시간 섹터별 활성화 및 보안 감시 시스템</p>
          </div>
          <div className="flex gap-3">
            <div className="hidden md:flex bg-green-500/10 border border-green-500/20 px-4 py-2 rounded-full items-center gap-2">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-black text-green-500">SECURE_ACCESS</span>
            </div>
            <button 
              onClick={handleLogout}
              className="bg-red-500/10 border border-red-500/20 px-4 py-2 rounded-full text-[10px] font-black text-red-500 hover:bg-red-500/20 transition-all"
            >
              LOGOUT
            </button>
          </div>
        </div>

        {/* 로딩 상태 표시 */}
        {isLoading ? (
          <div className="py-20 text-center animate-pulse">
            <p className="text-blue-500 font-black tracking-[0.5em] text-sm uppercase italic">Synchronizing Data...</p>
          </div>
        ) : (
          <>
            {/* 통계 카드 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {sectorStats.map((stat) => (
                <div key={stat.name} className="glass p-8 rounded-[2.5rem] border-white/5 space-y-6 bg-slate-900/40 relative overflow-hidden group hover:border-blue-500/30 transition-all">
                  <div className="flex justify-between items-center">
                    <p className="text-blue-500 text-xs font-black uppercase tracking-widest">{stat.name}</p>
                    <span className="text-[10px] text-slate-500 font-bold">{stat.memberCount} Members</span>
                  </div>
                  <div className="space-y-1">
                    <p className="text-slate-500 text-[10px] font-bold uppercase tracking-tighter">Total Deposits</p>
                    <p className="text-3xl font-black italic">{stat.totalPower.toLocaleString()} <span className="text-sm font-normal text-slate-500 italic">U</span></p>
                  </div>
                  <div className="space-y-4 pt-4 border-t border-white/5">
                    <div className="flex justify-between items-end">
                      <p className="text-slate-500 text-[10px] font-bold uppercase">Accrued Fee ({stat.currentRate}%)</p>
                      <p className="text-xl font-black text-blue-400">+{stat.totalFee.toLocaleString()} U</p>
                    </div>
                    <div className="grid grid-cols-5 gap-1">
                      {rateOptions.map(rate => (
                        <button
                          key={rate}
                          onClick={() => setSectorRates(prev => ({ ...prev, [stat.name]: rate }))}
                          className={`py-2 text-[9px] font-black rounded-lg transition-all ${
                            stat.currentRate === rate 
                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/40' 
                            : 'bg-white/5 text-slate-600 hover:bg-white/10'
                          }`}
                        >
                          {rate}%
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 하단 리스트 & 로그 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2 space-y-4">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] pl-4 italic">Activation Queue Logs</h2>
                <div className="glass rounded-[2.5rem] overflow-hidden border-white/5 bg-slate-900/20 shadow-2xl">
                  {requests.length === 0 ? (
                    <div className="p-20 text-center text-slate-600 font-bold uppercase tracking-widest">No Requests Pending</div>
                  ) : (
                    <table className="w-full text-left">
                      <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">
                        <tr>
                          <th className="p-7">User (Masked)</th>
                          <th className="p-7">Target Sector</th>
                          <th className="p-7 text-right">Power (U)</th>
                          <th className="p-7 text-center">Live Fee</th>
                          <th className="p-7 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm font-bold">
                        {requests.map((req) => {
                          const currentRate = sectorRates[req.sector];
                          const liveFee = (req.power * currentRate) / 100;
                          return (
                            <tr key={req.id} className="border-t border-white/5 hover:bg-white/[0.02] transition-colors group">
                              <td className="p-7">
                                <div className="font-mono text-xs text-blue-300">{maskEmail(req.user)}</div>
                                <div className="text-[9px] text-slate-600 mt-1">{req.time}</div>
                              </td>
                              <td className="p-7">
                                <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-[10px] text-blue-400 font-black uppercase italic">{req.sector}</span>
                              </td>
                              <td className="p-7 text-right font-mono italic text-slate-300">{req.power.toLocaleString()}</td>
                              <td className="p-7 text-center">
                                <div className="text-blue-400 font-black text-lg">+{liveFee.toFixed(2)} U</div>
                              </td>
                              <td className="p-7 text-right">
                                {req.status === 'pending' ? (
                                  <button onClick={() => handleApprove(req.id, req.user)} className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-black rounded-xl transition-all shadow-lg shadow-blue-500/20 uppercase">Approve</button>
                                ) : (
                                  <span className="text-green-500 text-[10px] uppercase font-black tracking-widest px-4">Success</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] pl-4 italic">Security Events</h2>
                <div className="glass rounded-[2.5rem] p-6 border-white/5 bg-slate-900/40 h-[480px] overflow-y-auto space-y-4">
                  {securityLogs.map(log => (
                    <div key={log.id} className="border-l-2 border-blue-500/50 pl-4 py-1">
                      <p className="text-[11px] font-bold text-slate-200">{log.action}</p>
                      <div className="flex justify-between text-[9px] font-mono text-slate-500 mt-1">
                        <span>{log.time}</span>
                        <span className="text-blue-500 uppercase">{log.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
        <div className="h-20"></div>
      </div>
    </div>
  );
}