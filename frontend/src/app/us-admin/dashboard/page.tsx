"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getApiBaseUrl } from '@/lib/apiBase';

interface DepositRequest {
  id: number;
  user: { id: number; email: string; username: string; sector_id: number | null };
  chain: string;
  expected_amount: number;
  joy_amount: number;
  actual_amount: number | null;
  detected_tx_hash: string | null;
  status: string;
  created_at: string;
}

interface UsdtStats {
  total_received_usdt: number;
  total_withdrawn_usdt: number;
  pending_withdrawal_usdt: number;
  available_usdt: number;
}

interface WithdrawalRequest {
  id: number;
  amount: number;
  note: string | null;
  status: string;
  requester_email: string | null;
  created_at: string;
  confirmed_at: string | null;
}

export default function UsAdminDashboard() {
  const router = useRouter();
  const API = getApiBaseUrl();

  const [deposits, setDeposits] = useState<DepositRequest[]>([]);
  const [usdtStats, setUsdtStats] = useState<UsdtStats | null>(null);
  const [withdrawals, setWithdrawals] = useState<WithdrawalRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'deposits' | 'withdrawals'>('overview');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // 출금 신청 모달
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawNote, setWithdrawNote] = useState('');
  const [withdrawing, setWithdrawing] = useState(false);
  const [withdrawError, setWithdrawError] = useState('');

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const meRes = await fetch(`${API}/auth/me`, { credentials: 'include' });
      if (!meRes.ok) { router.push('/us-admin/login'); return; }
      const me = await meRes.json();
      if (me.role !== 'us_admin' && me.role !== 'admin') {
        router.push('/us-admin/login'); return;
      }
      loadData();
    } catch {
      router.push('/us-admin/login');
    }
  };

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [depositsRes, statsRes, withdrawalsRes] = await Promise.all([
        fetch(`${API}/admin/deposits`, { credentials: 'include' }),
        fetch(`${API}/us-admin/stats`, { credentials: 'include' }),
        fetch(`${API}/us-admin/withdraw-requests`, { credentials: 'include' }),
      ]);

      if (depositsRes.ok) setDeposits(await depositsRes.json());
      if (statsRes.ok) setUsdtStats(await statsRes.json());
      if (withdrawalsRes.ok) setWithdrawals(await withdrawalsRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWithdrawRequest = async () => {
    const amount = parseFloat(withdrawAmount);
    if (!amount || amount <= 0) { setWithdrawError('유효한 금액을 입력해주세요.'); return; }
    if (usdtStats && amount > usdtStats.available_usdt) {
      setWithdrawError(`가용 USDT(${usdtStats.available_usdt.toFixed(2)})가 부족합니다.`);
      return;
    }

    setWithdrawing(true);
    setWithdrawError('');
    try {
      const res = await fetch(`${API}/us-admin/withdraw-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ amount, note: withdrawNote || null }),
      });
      if (res.ok) {
        setShowWithdrawModal(false);
        setWithdrawAmount('');
        setWithdrawNote('');
        loadData();
        alert('수령 신청이 완료되었습니다. 슈퍼관리자 확정 후 처리됩니다.');
      } else {
        const data = await res.json();
        setWithdrawError(data.detail || '수령 신청에 실패했습니다.');
      }
    } catch {
      setWithdrawError('서버 오류가 발생했습니다.');
    } finally {
      setWithdrawing(false);
    }
  };

  const handleLogout = async () => {
    await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' });
    router.push('/us-admin/login');
  };

  const filteredDeposits = deposits.filter(d => {
    const matchStatus = statusFilter === 'all' || d.status === statusFilter;
    const matchSearch = !searchQuery ||
      d.user.email.includes(searchQuery) ||
      d.user.username.includes(searchQuery) ||
      String(d.id).includes(searchQuery);
    return matchStatus && matchSearch;
  });

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400',
      approved: 'bg-green-500/20 text-green-400',
      rejected: 'bg-red-500/20 text-red-400',
      confirmed: 'bg-blue-500/20 text-blue-400',
    };
    return map[status] || 'bg-slate-700 text-slate-400';
  };

  const statusLabel = (status: string) => {
    const map: Record<string, string> = {
      pending: '확인 중',
      approved: '확인 완료',
      rejected: '반려',
      confirmed: '확정',
    };
    return map[status] || status;
  };

  if (isLoading) return (
    <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
      <p className="text-slate-400">로딩 중...</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      {/* USDT 출금 신청 모달 */}
      {showWithdrawModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 p-6 rounded-2xl w-full max-w-md border border-blue-500/20">
            <h3 className="text-lg font-bold text-blue-400 mb-4">USDT 수령 신청</h3>
            <div className="mb-2 p-3 bg-slate-800 rounded-xl text-sm">
              <span className="text-slate-400">가용 USDT: </span>
              <span className="text-green-400 font-bold">{usdtStats?.available_usdt.toFixed(2)} USDT</span>
            </div>
            <input
              type="number"
              placeholder="수령 금액 (USDT)"
              value={withdrawAmount}
              onChange={e => setWithdrawAmount(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 p-3 rounded-xl mb-3 text-white outline-none focus:border-blue-500"
            />
            <input
              type="text"
              placeholder="메모 (선택)"
              value={withdrawNote}
              onChange={e => setWithdrawNote(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 p-3 rounded-xl mb-3 text-white outline-none focus:border-blue-500"
            />
            {withdrawError && <p className="text-red-400 text-sm mb-3">{withdrawError}</p>}
            <div className="flex gap-3">
              <button
                onClick={() => { setShowWithdrawModal(false); setWithdrawError(''); }}
                className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl font-bold transition-all"
              >
                취소
              </button>
              <button
                onClick={handleWithdrawRequest}
                disabled={withdrawing}
                className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 rounded-xl font-bold transition-all"
              >
                {withdrawing ? '처리 중...' : '신청하기'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 헤더 */}
      <div className="bg-slate-900/50 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-blue-400">미국 관리자 대시보드</h1>
          <p className="text-xs text-slate-500 mt-0.5">조회 전용 · USDT 수령 신청 가능</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowWithdrawModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-bold transition-all"
          >
            💰 USDT 수령 신청
          </button>
          <button onClick={loadData} className="px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-sm transition-all">
            새로고침
          </button>
          <button onClick={handleLogout} className="px-3 py-2 bg-red-900/50 hover:bg-red-800/50 rounded-xl text-sm text-red-400 transition-all">
            로그아웃
          </button>
        </div>
      </div>

      <div className="p-6 max-w-7xl mx-auto">
        {/* USDT 잔액 카드 */}
        {usdtStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-900/50 border border-green-500/20 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-1">총 수령 USDT</p>
              <p className="text-2xl font-bold text-green-400">{usdtStats.total_received_usdt.toFixed(2)}</p>
            </div>
            <div className="bg-slate-900/50 border border-red-500/20 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-1">확정 수령</p>
              <p className="text-2xl font-bold text-red-400">{usdtStats.total_withdrawn_usdt.toFixed(2)}</p>
            </div>
            <div className="bg-slate-900/50 border border-yellow-500/20 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-1">대기 중 수령</p>
              <p className="text-2xl font-bold text-yellow-400">{usdtStats.pending_withdrawal_usdt.toFixed(2)}</p>
            </div>
            <div className="bg-slate-900/50 border border-blue-500/20 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-1">가용 USDT</p>
              <p className="text-2xl font-bold text-blue-400">{usdtStats.available_usdt.toFixed(2)}</p>
            </div>
          </div>
        )}

        {/* 탭 */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'overview', label: '구매 현황' },
            { id: 'withdrawals', label: '수령 내역' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${
                activeTab === tab.id ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 입금 현황 탭 */}
        {activeTab === 'overview' && (
          <div>
            <div className="flex gap-3 mb-4">
              <input
                type="text"
                placeholder="이메일/닉네임/ID 검색"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="flex-1 bg-slate-900/50 border border-slate-800 p-2.5 rounded-xl text-sm outline-none focus:border-blue-500 text-white"
              />
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="bg-slate-900/50 border border-slate-800 p-2.5 rounded-xl text-sm text-white outline-none"
              >
                <option value="all">전체</option>
                <option value="pending">대기</option>
                <option value="approved">승인</option>
                <option value="rejected">반려</option>
              </select>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
              <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-800/50 sticky top-0">
                    <tr>
                      <th className="p-3 text-left text-slate-400 font-semibold">ID</th>
                      <th className="p-3 text-left text-slate-400 font-semibold">이메일</th>
                      <th className="p-3 text-left text-slate-400 font-semibold">체인</th>
                      <th className="p-3 text-right text-slate-400 font-semibold">예상금액</th>
                      <th className="p-3 text-right text-slate-400 font-semibold">JOY</th>
                      <th className="p-3 text-center text-slate-400 font-semibold">상태</th>
                      <th className="p-3 text-left text-slate-400 font-semibold">날짜</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDeposits.map(d => (
                      <tr key={d.id} className="border-t border-slate-800/50 hover:bg-slate-800/30">
                        <td className="p-3 text-slate-500">#{d.id}</td>
                        <td className="p-3">
                          <p className="text-white">{d.user.email}</p>
                          <p className="text-xs text-slate-500">{d.user.username}</p>
                        </td>
                        <td className="p-3 text-slate-300">{d.chain}</td>
                        <td className="p-3 text-right font-mono">{d.expected_amount} USDT</td>
                        <td className="p-3 text-right text-blue-400">{d.joy_amount.toLocaleString()}</td>
                        <td className="p-3 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs font-bold ${statusBadge(d.status)}`}>
                            {statusLabel(d.status)}
                          </span>
                        </td>
                        <td className="p-3 text-slate-500 text-xs">{new Date(d.created_at).toLocaleDateString('ko-KR')}</td>
                      </tr>
                    ))}
                    {filteredDeposits.length === 0 && (
                      <tr><td colSpan={7} className="p-8 text-center text-slate-500">데이터 없음</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 출금 내역 탭 */}
        {activeTab === 'withdrawals' && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-800/50 sticky top-0">
                  <tr>
                    <th className="p-3 text-left text-slate-400">ID</th>
                    <th className="p-3 text-left text-slate-400">신청자</th>
                    <th className="p-3 text-right text-slate-400">금액</th>
                    <th className="p-3 text-left text-slate-400">메모</th>
                    <th className="p-3 text-center text-slate-400">상태</th>
                    <th className="p-3 text-left text-slate-400">신청일</th>
                    <th className="p-3 text-left text-slate-400">확정일</th>
                  </tr>
                </thead>
                <tbody>
                  {withdrawals.map(w => (
                    <tr key={w.id} className="border-t border-slate-800/50 hover:bg-slate-800/30">
                      <td className="p-3 text-slate-500">#{w.id}</td>
                      <td className="p-3 text-white">{w.requester_email || '-'}</td>
                      <td className="p-3 text-right font-mono text-green-400">{w.amount.toFixed(2)} USDT</td>
                      <td className="p-3 text-slate-400 text-xs">{w.note || '-'}</td>
                      <td className="p-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${statusBadge(w.status)}`}>
                          {statusLabel(w.status)}
                        </span>
                      </td>
                      <td className="p-3 text-slate-500 text-xs">{new Date(w.created_at).toLocaleDateString('ko-KR')}</td>
                      <td className="p-3 text-slate-500 text-xs">{w.confirmed_at ? new Date(w.confirmed_at).toLocaleDateString('ko-KR') : '-'}</td>
                    </tr>
                  ))}
                  {withdrawals.length === 0 && (
                    <tr><td colSpan={7} className="p-8 text-center text-slate-500">수령 내역 없음</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
