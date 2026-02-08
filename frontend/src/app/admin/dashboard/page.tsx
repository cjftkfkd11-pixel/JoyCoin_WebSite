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
  user: { id: number; email: string; username: string; sector_id: number | null };
  chain: string;
  expected_amount: number;
  joy_amount: number;
  actual_amount: number | null;
  status: string;
  created_at: string;
  assigned_address: string;
}

interface Sector {
  id: number;
  name: string;
  fee_percent: number;
}

interface Stats {
  total_users: number;
  total_deposits: number;
  total_approved_usdt: number;
  total_approved_joy: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  sector_stats: { sector_id: number; deposit_count: number; total_usdt: number }[];
}

interface UserItem {
  id: number;
  email: string;
  username: string;
  role: string;
  total_joy: number;
  is_banned: boolean;
  sector_id: number | null;
  created_at: string | null;
}

export default function AdminDashboard() {
  const router = useRouter();

  const [requests, setRequests] = useState<DepositRequest[]>([]);
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<'deposits' | 'sectors' | 'users' | 'products'>('deposits');
  const [users, setUsers] = useState<UserItem[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [userProcessingId, setUserProcessingId] = useState<number | null>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [editingProduct, setEditingProduct] = useState<any | null>(null);
  const [showProductForm, setShowProductForm] = useState(false);
  const [productForm, setProductForm] = useState({ name: '', joy_amount: 0, price_usdt: 0, price_krw: 0, discount_rate: 0, description: '', sort_order: 0 });
  const [referralBonus, setReferralBonus] = useState(100);
  const [joyPerUsdt, setJoyPerUsdt] = useState(5.0);
  const [joyPerUsdtInput, setJoyPerUsdtInput] = useState('5.0');
  const [stats, setStats] = useState<Stats | null>(null);
  const [sectorFilter, setSectorFilter] = useState<string>('all');

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchDeposits();
    fetchSectors();
    fetchUsers();
    fetchProducts();
    fetchSettings();
    fetchStats();
  }, []);

  const fetchDeposits = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/admin/deposits`, { credentials: 'include' });
      if (response.status === 401) { router.push('/admin/login'); return; }
      if (!response.ok) throw new Error('입금 목록을 가져올 수 없습니다.');
      setRequests(await response.json());
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSectors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/sectors`, { credentials: 'include' });
      if (response.ok) setSectors(await response.json());
    } catch (err) { console.error("섹터 로드 실패:", err); }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/settings`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setReferralBonus(data.referral_bonus_points);
        if (data.joy_per_usdt) {
          setJoyPerUsdt(data.joy_per_usdt);
          setJoyPerUsdtInput(String(data.joy_per_usdt));
        }
      }
    } catch {}
  };

  const handleReferralBonusChange = async (points: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/settings/referral-bonus`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ referral_bonus_points: points })
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      setReferralBonus(points);
      alert(`추천인 보너스가 ${points} 포인트로 변경되었습니다.`);
    } catch (err: any) { alert(err.message); }
  };

  const handleExchangeRateChange = async () => {
    const val = parseFloat(joyPerUsdtInput);
    if (isNaN(val) || val <= 0) { alert('올바른 값을 입력하세요'); return; }
    try {
      const res = await fetch(`${API_BASE_URL}/admin/settings/exchange-rate`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ joy_per_usdt: val })
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      const data = await res.json();
      setJoyPerUsdt(data.joy_per_usdt);
      setJoyPerUsdtInput(String(data.joy_per_usdt));
      alert(`JOY 시세가 변경되었습니다.\n1 USDT = ${data.joy_per_usdt} JOY\n1 JOY = ${data.joy_to_krw} KRW`);
    } catch (err: any) { alert(err.message); }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/deposits/stats`, { credentials: 'include' });
      if (res.ok) setStats(await res.json());
    } catch {}
  };

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/users`, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setUsers(data.items || []);
      }
    } catch (err) { console.error("유저 로드 실패:", err); }
  };

  const handleBan = async (userId: number, isBanned: boolean) => {
    const action = isBanned ? 'unban' : 'ban';
    const msg = isBanned ? '차단을 해제하시겠습니까?' : '이 유저를 차단하시겠습니까?';
    if (!confirm(msg)) return;
    try {
      setUserProcessingId(userId);
      const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/${action}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      fetchUsers();
    } catch (err: any) { alert(err.message); }
    finally { setUserProcessingId(null); }
  };

  const handleRoleChange = async (userId: number, currentRole: string) => {
    const action = currentRole === 'admin' ? 'demote' : 'promote';
    const msg = currentRole === 'admin' ? '일반 유저로 변경하시겠습니까?' : '관리자로 승격하시겠습니까?';
    if (!confirm(msg)) return;
    try {
      setUserProcessingId(userId);
      const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/${action}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      fetchUsers();
    } catch (err: any) { alert(err.message); }
    finally { setUserProcessingId(null); }
  };

  const fetchProducts = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/products/admin/all`, { credentials: 'include' });
      if (response.ok) setProducts(await response.json());
    } catch (err) { console.error("상품 로드 실패:", err); }
  };

  const openProductForm = (product?: any) => {
    if (product) {
      setEditingProduct(product);
      setProductForm({ name: product.name, joy_amount: product.joy_amount, price_usdt: product.price_usdt, price_krw: product.price_krw || 0, discount_rate: product.discount_rate || 0, description: product.description || '', sort_order: product.sort_order || 0 });
    } else {
      setEditingProduct(null);
      setProductForm({ name: '', joy_amount: 0, price_usdt: 0, price_krw: 0, discount_rate: 0, description: '', sort_order: 0 });
    }
    setShowProductForm(true);
  };

  const handleProductSave = async () => {
    try {
      const url = editingProduct ? `${API_BASE_URL}/products/admin/${editingProduct.id}` : `${API_BASE_URL}/products/admin`;
      const method = editingProduct ? 'PUT' : 'POST';
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(productForm) });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      setShowProductForm(false);
      fetchProducts();
    } catch (err: any) { alert(err.message); }
  };

  const handleProductToggle = async (id: number, isActive: boolean) => {
    const url = isActive ? `${API_BASE_URL}/products/admin/${id}` : `${API_BASE_URL}/products/admin/${id}/activate`;
    const method = isActive ? 'DELETE' : 'POST';
    try {
      const res = await fetch(url, { method, credentials: 'include' });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      fetchProducts();
    } catch (err: any) { alert(err.message); }
  };

  const handleApprove = async (id: number, userEmail: string) => {
    if (!confirm(`${maskEmail(userEmail)} 님의 입금 요청을 승인하시겠습니까?`)) return;
    try {
      setProcessingId(id);
      const response = await fetch(`${API_BASE_URL}/admin/deposits/${id}/approve`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ admin_notes: '승인 완료' })
      });
      if (!response.ok) { const e = await response.json(); throw new Error(e.detail || '승인 실패'); }
      alert('승인 완료. 사용자에게 JOY 코인을 전송하세요!');
      fetchDeposits();
      fetchStats();
    } catch (err: any) { alert(err.message); }
    finally { setProcessingId(null); }
  };

  const handleReject = async (id: number, userEmail: string) => {
    const reason = prompt(`${maskEmail(userEmail)} 님의 입금 요청 거절 사유:`);
    if (!reason) return;
    try {
      setProcessingId(id);
      const response = await fetch(`${API_BASE_URL}/admin/deposits/${id}/reject`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ admin_notes: reason })
      });
      if (!response.ok) { const e = await response.json(); throw new Error(e.detail || '거절 실패'); }
      alert('입금 요청이 거절되었습니다.');
      fetchDeposits();
      fetchStats();
    } catch (err: any) { alert(err.message); }
    finally { setProcessingId(null); }
  };

  const handleFeeChange = async (sectorId: number, fee: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/sectors/${sectorId}/fee`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ fee_percent: fee })
      });
      if (!response.ok) throw new Error('Fee 변경 실패');
      fetchSectors();
    } catch (err: any) { alert(err.message); }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
      router.push('/admin/login');
    } catch (err) { router.push('/admin/login'); }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      approved: "bg-green-500/10 text-green-400 border-green-500/20",
      rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    const labels: Record<string, string> = { pending: "대기중", approved: "승인완료", rejected: "거절됨" };
    return (
      <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${styles[status] || styles.pending}`}>
        {labels[status] || status}
      </span>
    );
  };

  // 검색 + 필터링 (섹터 필터 포함)
  const filteredRequests = requests.filter(req => {
    const matchesStatus = statusFilter === 'all' || req.status === statusFilter;
    const matchesSearch = !searchQuery ||
      req.user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      req.user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      req.id.toString().includes(searchQuery);
    const matchesSector = sectorFilter === 'all' || req.user?.sector_id?.toString() === sectorFilter;
    return matchesStatus && matchesSearch && matchesSector;
  });

  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6 text-center">
        <div className="p-10 rounded-[2.5rem] border border-red-500/20 max-w-md w-full bg-slate-900/40">
          <h2 className="text-red-500 font-black mb-4 uppercase tracking-widest text-xl">System Error</h2>
          <p className="text-slate-400 text-sm mb-6">{error}</p>
          <button onClick={fetchDeposits} className="w-full py-4 bg-red-600/20 text-red-500 font-black rounded-2xl hover:bg-red-600 hover:text-white transition-all">재시도</button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-[#020617] text-white flex flex-col overflow-hidden font-sans">
      {/* 헤더 - 고정 */}
      <div className="flex-shrink-0 p-6 md:px-12 md:pt-8 border-b border-white/10">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-black italic tracking-tighter text-blue-500 uppercase">
              Admin <span className="text-white">Dashboard</span>
            </h1>
            <p className="text-slate-500 text-[10px] font-bold uppercase mt-1 tracking-[0.3em]">총관리자 시스템</p>
          </div>
          <div className="flex gap-3 items-center">
            <div className="hidden md:flex bg-green-500/10 border border-green-500/20 px-4 py-2 rounded-full items-center gap-2">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-black text-green-500">ONLINE</span>
            </div>
            <button onClick={handleLogout} className="bg-red-500/10 border border-red-500/20 px-4 py-2 rounded-full text-[10px] font-black text-red-500 hover:bg-red-500/20 transition-all">
              LOGOUT
            </button>
          </div>
        </div>
      </div>

      {/* 탭 네비게이션 */}
      <div className="flex-shrink-0 px-6 md:px-12 pt-4">
        <div className="max-w-7xl mx-auto flex gap-2">
          <button
            onClick={() => setActiveTab('deposits')}
            className={`px-6 py-2 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'deposits' ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-white'}`}
          >
            입금 요청 관리
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-6 py-2 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'users' ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-white'}`}
          >
            사용자 관리
          </button>
          <button
            onClick={() => setActiveTab('products')}
            className={`px-6 py-2 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'products' ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-white'}`}
          >
            상품 관리
          </button>
          <button
            onClick={() => setActiveTab('sectors')}
            className={`px-6 py-2 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'sectors' ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-white'}`}
          >
            섹터 Fee 설정
          </button>
        </div>
      </div>

      {/* 메인 컨텐츠 - 스크롤 영역 */}
      <div className="flex-1 overflow-y-auto p-6 md:px-12 md:pb-8">
        <div className="max-w-7xl mx-auto space-y-6">

          {isLoading ? (
            <div className="py-20 text-center animate-pulse">
              <p className="text-blue-500 font-black tracking-[0.5em] text-sm uppercase italic">Loading Data...</p>
            </div>
          ) : activeTab === 'deposits' ? (
            <>
              {/* 통계 카드 - 상단 요약 */}
              <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
                <div className="p-4 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-blue-500 text-[10px] font-black uppercase tracking-widest">총 유저</p>
                  <p className="text-2xl font-black italic mt-1">{stats?.total_users ?? '-'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest">총 입금건</p>
                  <p className="text-2xl font-black italic mt-1">{stats?.total_deposits ?? '-'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-yellow-500/10 bg-yellow-500/5">
                  <p className="text-yellow-500 text-[10px] font-black uppercase tracking-widest">대기중</p>
                  <p className="text-2xl font-black italic mt-1 text-yellow-400">{stats?.pending_count ?? '-'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-green-500/10 bg-green-500/5">
                  <p className="text-green-500 text-[10px] font-black uppercase tracking-widest">승인완료</p>
                  <p className="text-2xl font-black italic mt-1 text-green-400">{stats?.approved_count ?? '-'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-cyan-400 text-[10px] font-black uppercase tracking-widest">총 USDT</p>
                  <p className="text-2xl font-black italic mt-1 text-cyan-300">${stats?.total_approved_usdt?.toLocaleString() ?? '0'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-purple-400 text-[10px] font-black uppercase tracking-widest">총 JOY</p>
                  <p className="text-2xl font-black italic mt-1 text-purple-300">{stats?.total_approved_joy?.toLocaleString() ?? '0'}</p>
                </div>
              </div>

              {/* 섹터별 통계 */}
              {stats?.sector_stats && stats.sector_stats.length > 0 && (
                <div className="grid grid-cols-5 gap-3">
                  {stats.sector_stats.map(ss => {
                    const sector = sectors.find(s => s.id === ss.sector_id);
                    return (
                      <div key={ss.sector_id} className="p-4 rounded-2xl border border-blue-500/10 bg-blue-500/5">
                        <p className="text-blue-400 text-[10px] font-black uppercase tracking-widest">섹터 {sector?.name || ss.sector_id}</p>
                        <p className="text-lg font-black italic mt-1">{ss.deposit_count}건</p>
                        <p className="text-xs text-slate-400 mt-0.5">${ss.total_usdt.toLocaleString()}</p>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* 검색 + 필터 + 섹터 필터 */}
              <div className="flex gap-3 items-center flex-wrap">
                <div className="flex-1 min-w-[200px] relative">
                  <input
                    type="text"
                    placeholder="이메일, 유저명, ID로 검색..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
                  />
                </div>
                <select
                  value={sectorFilter}
                  onChange={e => setSectorFilter(e.target.value)}
                  className="bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500/50"
                >
                  <option value="all">전체 섹터</option>
                  {sectors.map(s => (
                    <option key={s.id} value={s.id.toString()}>섹터 {s.name}</option>
                  ))}
                </select>
                <div className="flex gap-1">
                  {['all', 'pending', 'approved', 'rejected'].map(s => (
                    <button
                      key={s}
                      onClick={() => setStatusFilter(s)}
                      className={`px-3 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${statusFilter === s ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-500 hover:text-white'}`}
                    >
                      {s === 'all' ? '전체' : s === 'pending' ? '대기' : s === 'approved' ? '승인' : '거절'}
                    </button>
                  ))}
                </div>
              </div>

              {/* 입금 요청 테이블 */}
              <div className="rounded-2xl overflow-hidden border border-white/5 bg-slate-900/20">
                {filteredRequests.length === 0 ? (
                  <div className="p-16 text-center text-slate-600 font-bold uppercase tracking-widest text-sm">
                    {searchQuery ? '검색 결과가 없습니다' : '입금 요청이 없습니다'}
                  </div>
                ) : (
                  <div className="max-h-[50vh] overflow-y-auto">
                    <table className="w-full text-left">
                      <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] sticky top-0 z-10">
                        <tr>
                          <th className="p-5">ID</th>
                          <th className="p-5">유저</th>
                          <th className="p-5">섹터</th>
                          <th className="p-5">네트워크</th>
                          <th className="p-5 text-right">금액</th>
                          <th className="p-5 text-right">JOY 수량</th>
                          <th className="p-5 text-center">상태</th>
                          <th className="p-5 text-center">요청일시</th>
                          <th className="p-5 text-right">액션</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm font-bold">
                        {filteredRequests.map((req) => (
                          <tr key={req.id} className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                            <td className="p-5"><div className="font-mono text-xs text-slate-500">#{req.id}</div></td>
                            <td className="p-5">
                              <div className="font-mono text-xs text-blue-300">{maskEmail(req.user.email)}</div>
                              <div className="text-[9px] text-slate-600 mt-1">{req.user.username}</div>
                            </td>
                            <td className="p-5">
                              {req.user.sector_id ? (
                                <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-[10px] text-blue-400 font-black">
                                  {sectors.find(s => s.id === req.user.sector_id)?.name || req.user.sector_id}
                                </span>
                              ) : (
                                <span className="text-slate-600 text-[10px]">-</span>
                              )}
                            </td>
                            <td className="p-5">
                              <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-[10px] text-blue-400 font-black uppercase italic">{req.chain}</span>
                            </td>
                            <td className="p-5 text-right font-mono italic text-slate-300">{req.expected_amount.toLocaleString()} USDT</td>
                            <td className="p-5 text-right font-mono italic text-blue-400">{(req.joy_amount || 0).toLocaleString()} JOY</td>
                            <td className="p-5 text-center">{getStatusBadge(req.status)}</td>
                            <td className="p-5 text-center text-slate-500 text-xs">{new Date(req.created_at).toLocaleString('ko-KR')}</td>
                            <td className="p-5 text-right">
                              {req.status === 'pending' ? (
                                <div className="flex gap-2 justify-end">
                                  <button onClick={() => handleApprove(req.id, req.user.email)} disabled={processingId === req.id}
                                    className="px-3 py-1.5 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 text-white text-[10px] font-black rounded-lg transition-all uppercase">
                                    {processingId === req.id ? '...' : '승인'}
                                  </button>
                                  <button onClick={() => handleReject(req.id, req.user.email)} disabled={processingId === req.id}
                                    className="px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 text-white text-[10px] font-black rounded-lg transition-all uppercase">
                                    거절
                                  </button>
                                </div>
                              ) : (
                                <span className="text-slate-600 text-[10px] uppercase font-black tracking-widest">
                                  {req.status === 'approved' ? '완료' : '거절됨'}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
              <p className="text-slate-600 text-[10px] text-right">총 {filteredRequests.length}건</p>
            </>
          ) : activeTab === 'products' ? (
            /* 상품 관리 탭 */
            <>
              {showProductForm && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                  <div className="bg-slate-900 p-8 rounded-3xl w-full max-w-lg border border-blue-500/20 shadow-2xl relative">
                    <button onClick={() => setShowProductForm(false)} className="absolute top-4 right-4 text-slate-500 hover:text-white text-2xl">×</button>
                    <h2 className="text-xl font-black text-blue-400 mb-6">{editingProduct ? '상품 수정' : '새 상품 추가'}</h2>
                    <div className="space-y-4">
                      <div>
                        <label className="text-xs text-slate-400 font-bold">상품명</label>
                        <input value={productForm.name} onChange={e => setProductForm({...productForm, name: e.target.value})}
                          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs text-slate-400 font-bold">JOY 수량</label>
                          <input type="number" value={productForm.joy_amount} onChange={e => setProductForm({...productForm, joy_amount: Number(e.target.value)})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                        </div>
                        <div>
                          <label className="text-xs text-slate-400 font-bold">가격 (USDT)</label>
                          <input type="number" step="0.01" value={productForm.price_usdt} onChange={e => setProductForm({...productForm, price_usdt: Number(e.target.value)})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs text-slate-400 font-bold">가격 (KRW)</label>
                          <input type="number" value={productForm.price_krw} onChange={e => setProductForm({...productForm, price_krw: Number(e.target.value)})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                        </div>
                        <div>
                          <label className="text-xs text-slate-400 font-bold">할인율 (%)</label>
                          <input type="number" value={productForm.discount_rate} onChange={e => setProductForm({...productForm, discount_rate: Number(e.target.value)})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-slate-400 font-bold">설명</label>
                        <input value={productForm.description} onChange={e => setProductForm({...productForm, description: e.target.value})}
                          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                      </div>
                      <button onClick={handleProductSave} className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold text-lg transition-all">
                        {editingProduct ? '수정' : '추가'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
              <div className="flex justify-between items-center">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">상품 패키지 관리</h2>
                <button onClick={() => openProductForm()} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-black text-white transition-all">
                  + 새 상품
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {products.map(p => (
                  <div key={p.id} className={`p-6 rounded-2xl border bg-slate-900/40 space-y-3 ${p.is_active ? 'border-white/5' : 'border-red-500/20 opacity-60'}`}>
                    <div className="flex justify-between items-start">
                      <h3 className="text-lg font-black text-white">{p.name}</h3>
                      {!p.is_active && <span className="px-2 py-1 bg-red-500/10 text-red-400 text-[10px] font-black rounded-full">비활성</span>}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div><span className="text-slate-500 text-xs">JOY</span><p className="font-bold text-blue-400">{p.joy_amount.toLocaleString()}</p></div>
                      <div><span className="text-slate-500 text-xs">USDT</span><p className="font-bold">{p.price_usdt}</p></div>
                      <div><span className="text-slate-500 text-xs">KRW</span><p className="font-bold text-slate-300">{(p.price_krw || 0).toLocaleString()}</p></div>
                      <div><span className="text-slate-500 text-xs">할인</span><p className="font-bold text-green-400">{p.discount_rate}%</p></div>
                    </div>
                    {p.description && <p className="text-xs text-slate-500">{p.description}</p>}
                    <div className="flex gap-2 pt-2">
                      <button onClick={() => openProductForm(p)} className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-xs font-bold text-white transition-all">수정</button>
                      <button onClick={() => handleProductToggle(p.id, p.is_active)}
                        className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${p.is_active ? 'bg-red-600/20 text-red-400 hover:bg-red-600 hover:text-white' : 'bg-green-600/20 text-green-400 hover:bg-green-600 hover:text-white'}`}>
                        {p.is_active ? '비활성화' : '활성화'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : activeTab === 'users' ? (
            /* 사용자 관리 탭 */
            <>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-blue-500 text-[10px] font-black uppercase tracking-widest">전체 유저</p>
                  <p className="text-3xl font-black italic mt-2">{users.length}</p>
                </div>
                <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-yellow-500 text-[10px] font-black uppercase tracking-widest">관리자</p>
                  <p className="text-3xl font-black italic mt-2">{users.filter(u => u.role === 'admin').length}</p>
                </div>
                <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-red-500 text-[10px] font-black uppercase tracking-widest">차단됨</p>
                  <p className="text-3xl font-black italic mt-2">{users.filter(u => u.is_banned).length}</p>
                </div>
              </div>

              <div className="flex-1 relative">
                <input
                  type="text"
                  placeholder="이메일 또는 유저명으로 검색..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="w-full bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
                />
              </div>

              <div className="rounded-2xl overflow-hidden border border-white/5 bg-slate-900/20">
                <div className="max-h-[50vh] overflow-y-auto">
                  <table className="w-full text-left">
                    <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] sticky top-0 z-10">
                      <tr>
                        <th className="p-5">ID</th>
                        <th className="p-5">이메일</th>
                        <th className="p-5">유저명</th>
                        <th className="p-5 text-center">권한</th>
                        <th className="p-5 text-right">JOY</th>
                        <th className="p-5 text-center">상태</th>
                        <th className="p-5 text-center">가입일</th>
                        <th className="p-5 text-right">액션</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm font-bold">
                      {users
                        .filter(u => !userSearch ||
                          u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
                          u.username.toLowerCase().includes(userSearch.toLowerCase())
                        )
                        .map((u) => (
                        <tr key={u.id} className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                          <td className="p-5 font-mono text-xs text-slate-500">#{u.id}</td>
                          <td className="p-5 font-mono text-xs text-blue-300">{maskEmail(u.email)}</td>
                          <td className="p-5 text-xs text-slate-300">{u.username}</td>
                          <td className="p-5 text-center">
                            <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${
                              u.role === 'admin' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                              u.role === 'sector_manager' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                              'bg-slate-500/10 text-slate-400 border-slate-500/20'
                            }`}>
                              {u.role === 'admin' ? '관리자' : u.role === 'sector_manager' ? '섹터매니저' : '유저'}
                            </span>
                          </td>
                          <td className="p-5 text-right font-mono italic text-blue-400">{(u.total_joy || 0).toLocaleString()}</td>
                          <td className="p-5 text-center">
                            {u.is_banned ? (
                              <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase border bg-red-500/10 text-red-400 border-red-500/20">차단됨</span>
                            ) : (
                              <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase border bg-green-500/10 text-green-400 border-green-500/20">정상</span>
                            )}
                          </td>
                          <td className="p-5 text-center text-slate-500 text-xs">{u.created_at ? new Date(u.created_at).toLocaleDateString('ko-KR') : '-'}</td>
                          <td className="p-5 text-right">
                            <div className="flex gap-2 justify-end">
                              <button
                                onClick={() => handleBan(u.id, u.is_banned)}
                                disabled={u.role === 'admin' || userProcessingId === u.id}
                                className={`px-3 py-1.5 text-[10px] font-black rounded-lg transition-all uppercase disabled:opacity-30 ${
                                  u.is_banned ? 'bg-green-600 hover:bg-green-500 text-white' : 'bg-red-600 hover:bg-red-500 text-white'
                                }`}
                              >
                                {u.is_banned ? '해제' : '차단'}
                              </button>
                              <button
                                onClick={() => handleRoleChange(u.id, u.role)}
                                disabled={userProcessingId === u.id}
                                className={`px-3 py-1.5 text-[10px] font-black rounded-lg transition-all uppercase ${
                                  u.role === 'admin' ? 'bg-slate-600 hover:bg-slate-500 text-white' : 'bg-yellow-600 hover:bg-yellow-500 text-white'
                                }`}
                              >
                                {u.role === 'admin' ? '강등' : '승격'}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <p className="text-slate-600 text-[10px] text-right">총 {users.filter(u => !userSearch || u.email.toLowerCase().includes(userSearch.toLowerCase()) || u.username.toLowerCase().includes(userSearch.toLowerCase())).length}건</p>
            </>
          ) : (
            /* 섹터 Fee 설정 탭 */
            <div className="space-y-8">
              {/* JOY 시세 설정 */}
              <div className="space-y-4">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">JOY 시세 설정</h2>
                <div className="p-6 rounded-2xl border border-cyan-500/10 bg-cyan-500/5">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-lg font-black text-white">JOY / USDT 환율</h3>
                      <p className="text-xs text-slate-500 mt-1">1 USDT = ? JOY (거래소 상장 전까지 수동 조정)</p>
                    </div>
                    <div className="text-right">
                      <span className="text-3xl font-black italic text-cyan-400">{joyPerUsdt}</span>
                      <p className="text-xs text-slate-500 mt-1">1 JOY = ${(1 / joyPerUsdt).toFixed(4)} USDT</p>
                    </div>
                  </div>
                  <div className="flex gap-3 items-center">
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      value={joyPerUsdtInput}
                      onChange={e => setJoyPerUsdtInput(e.target.value)}
                      className="flex-1 bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-cyan-500/50"
                    />
                    <button
                      onClick={handleExchangeRateChange}
                      className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 rounded-xl text-sm font-black text-white transition-all"
                    >
                      변경
                    </button>
                  </div>
                  <div className="mt-3 grid grid-cols-4 gap-2">
                    {[3, 4, 5, 10].map(v => (
                      <button
                        key={v}
                        onClick={() => { setJoyPerUsdtInput(String(v)); }}
                        className={`py-2 rounded-lg text-xs font-black transition-all ${joyPerUsdt === v
                          ? 'bg-cyan-600 text-white'
                          : 'bg-slate-800 text-slate-500 hover:bg-slate-700 hover:text-white'
                        }`}
                      >
                        1 USDT = {v} JOY
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* 추천인 보너스 설정 */}
              <div className="space-y-4">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">추천인 보너스 설정</h2>
                <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-lg font-black text-white">추천인 보너스 포인트</h3>
                      <p className="text-xs text-slate-500 mt-1">신규 회원 가입 시 추천인에게 지급되는 포인트</p>
                    </div>
                    <span className="text-3xl font-black italic text-green-400">{referralBonus}P</span>
                  </div>
                  <div className="grid grid-cols-5 gap-2">
                    {[50, 100, 150, 200, 500].map(pts => (
                      <button
                        key={pts}
                        onClick={() => handleReferralBonusChange(pts)}
                        className={`py-3 rounded-xl text-sm font-black transition-all ${referralBonus === pts
                          ? 'bg-green-600 text-white'
                          : 'bg-slate-800 text-slate-500 hover:bg-slate-700 hover:text-white'
                        }`}
                      >
                        {pts}P
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* 섹터별 Fee */}
              <div className="space-y-4">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">섹터별 Fee 설정</h2>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  {sectors.map(sector => (
                    <div key={sector.id} className="p-6 rounded-2xl border border-white/5 bg-slate-900/40 space-y-4">
                      <div className="flex justify-between items-center">
                        <h3 className="text-2xl font-black italic text-blue-400">Sector {sector.name}</h3>
                        <span className="text-xl font-black text-green-400">{sector.fee_percent}%</span>
                      </div>
                      <div className="grid grid-cols-4 gap-1">
                        {[5, 10, 15, 20].map(fee => (
                          <button
                            key={fee}
                            onClick={() => handleFeeChange(sector.id, fee)}
                            className={`py-2 rounded-lg text-xs font-black transition-all ${sector.fee_percent === fee
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-800 text-slate-500 hover:bg-slate-700 hover:text-white'
                            }`}
                          >
                            {fee}%
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
