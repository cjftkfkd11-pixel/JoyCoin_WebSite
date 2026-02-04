"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// --- [Helper Functions] ---
const maskEmail = (email: string) => {
  const [name, domain] = email.split('@');
  if (name.length <= 2) return `${name}***@${domain}`;
  return `${name.substring(0, 2)}***@${domain}`;
};

// --- [Types] ---
interface DepositRequest {
  id: number;
  user: {
    id: number;
    email: string;
    username: string;
  };
  chain: string;
  expected_amount: number;
  actual_amount: number | null;
  status: string;
  created_at: string;
  assigned_address: string;
}

export default function AdminDashboard() {
  const router = useRouter();

  // --- [States] ---
  const [requests, setRequests] = useState<DepositRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<number | null>(null);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

  // --- [Data Fetching] ---
  useEffect(() => {
    fetchDeposits();
  }, []);

  const fetchDeposits = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/admin/deposits`, {
        credentials: 'include'
      });

      if (response.status === 401) {
        router.push('/admin/login');
        return;
      }

      if (!response.ok) throw new Error('입금 목록을 가져올 수 없습니다.');

      const data = await response.json();
      setRequests(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async (id: number, userEmail: string) => {
    if (!confirm(`${maskEmail(userEmail)} 님의 입금 요청을 승인하시겠습니까?`)) return;

    try {
      setProcessingId(id);
      const response = await fetch(`${API_BASE_URL}/admin/deposits/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          admin_notes: '승인 완료'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '승인 처리 중 오류가 발생했습니다.');
      }

      alert('승인이 완료되었습니다. 유저 잔액이 충전되었습니다.');
      fetchDeposits(); // 목록 새로고침
    } catch (err: any) {
      alert(err.message);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (id: number, userEmail: string) => {
    const reason = prompt(`${maskEmail(userEmail)} 님의 입금 요청을 거절하시겠습니까?\n거절 사유를 입력해주세요:`);
    if (!reason) return;

    try {
      setProcessingId(id);
      const response = await fetch(`${API_BASE_URL}/admin/deposits/${id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          admin_notes: reason
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '거절 처리 중 오류가 발생했습니다.');
      }

      alert('입금 요청이 거절되었습니다.');
      fetchDeposits();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setProcessingId(null);
    }
  };

  const handleLogout = async () => {
    try {
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

  // --- [Status Badge] ---
  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      approved: "bg-green-500/10 text-green-400 border-green-500/20",
      rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    const labels: Record<string, string> = {
      pending: "대기중",
      approved: "승인완료",
      rejected: "거절됨",
    };

    return (
      <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${styles[status] || styles.pending}`}>
        {labels[status] || status}
      </span>
    );
  };

  // --- [Render Conditions] ---
  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6 text-center">
        <div className="glass p-10 rounded-[2.5rem] border-red-500/20 max-w-md w-full">
          <h2 className="text-red-500 font-black mb-4 uppercase tracking-widest text-xl">System Error</h2>
          <p className="text-slate-400 text-sm mb-6">{error}</p>
          <button onClick={() => fetchDeposits()} className="w-full py-4 bg-red-600/20 text-red-500 font-black rounded-2xl hover:bg-red-600 hover:text-white transition-all">
            재시도
          </button>
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
              Admin <span className="text-white">Dashboard</span>
            </h1>
            <p className="text-slate-500 text-[10px] font-bold uppercase mt-2 tracking-[0.3em]">입금 요청 관리 시스템</p>
          </div>
          <div className="flex gap-3">
            <div className="hidden md:flex bg-green-500/10 border border-green-500/20 px-4 py-2 rounded-full items-center gap-2">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-black text-green-500">ONLINE</span>
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
            <p className="text-blue-500 font-black tracking-[0.5em] text-sm uppercase italic">Loading Data...</p>
          </div>
        ) : (
          <>
            {/* 통계 카드 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="glass p-8 rounded-[2.5rem] border-white/5 space-y-4 bg-slate-900/40">
                <p className="text-yellow-500 text-xs font-black uppercase tracking-widest">대기중</p>
                <p className="text-4xl font-black italic">{requests.filter(r => r.status === 'pending').length}</p>
              </div>
              <div className="glass p-8 rounded-[2.5rem] border-white/5 space-y-4 bg-slate-900/40">
                <p className="text-green-500 text-xs font-black uppercase tracking-widest">승인완료</p>
                <p className="text-4xl font-black italic">{requests.filter(r => r.status === 'approved').length}</p>
              </div>
              <div className="glass p-8 rounded-[2.5rem] border-white/5 space-y-4 bg-slate-900/40">
                <p className="text-red-500 text-xs font-black uppercase tracking-widest">거절됨</p>
                <p className="text-4xl font-black italic">{requests.filter(r => r.status === 'rejected').length}</p>
              </div>
            </div>

            {/* 입금 요청 목록 */}
            <div className="space-y-4">
              <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] pl-4 italic">입금 요청 목록</h2>
              <div className="glass rounded-[2.5rem] overflow-hidden border-white/5 bg-slate-900/20 shadow-2xl">
                {requests.length === 0 ? (
                  <div className="p-20 text-center text-slate-600 font-bold uppercase tracking-widest">입금 요청이 없습니다</div>
                ) : (
                  <table className="w-full text-left">
                    <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">
                      <tr>
                        <th className="p-7">ID</th>
                        <th className="p-7">유저</th>
                        <th className="p-7">네트워크</th>
                        <th className="p-7 text-right">금액 (USDT)</th>
                        <th className="p-7 text-center">상태</th>
                        <th className="p-7 text-center">요청일시</th>
                        <th className="p-7 text-right">액션</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm font-bold">
                      {requests.map((req) => (
                        <tr key={req.id} className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                          <td className="p-7">
                            <div className="font-mono text-xs text-slate-500">#{req.id}</div>
                          </td>
                          <td className="p-7">
                            <div className="font-mono text-xs text-blue-300">{maskEmail(req.user.email)}</div>
                            <div className="text-[9px] text-slate-600 mt-1">{req.user.username}</div>
                          </td>
                          <td className="p-7">
                            <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-[10px] text-blue-400 font-black uppercase italic">
                              {req.chain}
                            </span>
                          </td>
                          <td className="p-7 text-right font-mono italic text-slate-300 text-lg">
                            {req.expected_amount.toLocaleString()}
                          </td>
                          <td className="p-7 text-center">
                            {getStatusBadge(req.status)}
                          </td>
                          <td className="p-7 text-center text-slate-500 text-xs">
                            {new Date(req.created_at).toLocaleString('ko-KR')}
                          </td>
                          <td className="p-7 text-right">
                            {req.status === 'pending' ? (
                              <div className="flex gap-2 justify-end">
                                <button
                                  onClick={() => handleApprove(req.id, req.user.email)}
                                  disabled={processingId === req.id}
                                  className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 text-white text-[10px] font-black rounded-xl transition-all shadow-lg uppercase"
                                >
                                  {processingId === req.id ? '처리중...' : '승인'}
                                </button>
                                <button
                                  onClick={() => handleReject(req.id, req.user.email)}
                                  disabled={processingId === req.id}
                                  className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 text-white text-[10px] font-black rounded-xl transition-all shadow-lg uppercase"
                                >
                                  거절
                                </button>
                              </div>
                            ) : (
                              <span className="text-slate-600 text-[10px] uppercase font-black tracking-widest px-4">
                                {req.status === 'approved' ? '처리완료' : '거절됨'}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </>
        )}
        <div className="h-20"></div>
      </div>
    </div>
  );
}
