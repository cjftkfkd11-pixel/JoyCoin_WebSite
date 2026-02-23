"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/Toast';
import { getApiBaseUrl } from '@/lib/apiBase';
import { useLanguage } from '@/lib/LanguageContext';

// --- [Types] ---
interface DepositRequest {
  id: number;
  user: { id: number; email: string; username: string; wallet_address?: string | null; sector_id: number | null };
  chain: string;
  expected_amount: number;
  joy_amount: number;
  actual_amount: number | null;
  detected_tx_hash: string | null;
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
  const { toast } = useToast();
  const { t } = useLanguage();

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
  const [referralBonus, setReferralBonus] = useState(10);
  const [joyPerUsdt, setJoyPerUsdt] = useState(5.0);
  const [joyPerUsdtInput, setJoyPerUsdtInput] = useState('5.0');
  const [stats, setStats] = useState<Stats | null>(null);
  const [sectorFilter, setSectorFilter] = useState<string>('all');

  const API_BASE_URL = getApiBaseUrl();

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
      if (!response.ok) throw new Error(t("systemError"));
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
    } catch (err) { console.error("Sector load failed:", err); }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/settings`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setReferralBonus(data.referral_bonus_percent);
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
        body: JSON.stringify({ referral_bonus_percent: points })
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      setReferralBonus(points);
      toast(t("referralBonusUpdated").replace('{points}', String(points)), "success");
    } catch (err: any) { toast(err.message, "error"); }
  };

  const handleExchangeRateChange = async () => {
    const val = parseFloat(joyPerUsdtInput);
    if (isNaN(val) || val <= 0) { toast(t("systemError"), 'warning'); return; }
    try {
      const res = await fetch(`${API_BASE_URL}/admin/settings/exchange-rate`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ joy_per_usdt: val })
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      const data = await res.json();
      setJoyPerUsdt(data.joy_per_usdt);
      setJoyPerUsdtInput(String(data.joy_per_usdt));
      toast(t("exchangeRateChanged").replace('{joy}', String(data.joy_per_usdt)).replace('{krw}', String(data.joy_to_krw)), "success");
    } catch (err: any) { toast(err.message, "error"); }
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
    } catch (err) { console.error("User load failed:", err); }
  };

  const handleBan = async (userId: number, isBanned: boolean) => {
    const action = isBanned ? 'unban' : 'ban';
    const msg = isBanned ? t("unbanConfirm") : t("banConfirm");
    if (!confirm(msg)) return;
    try {
      setUserProcessingId(userId);
      const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/${action}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      fetchUsers();
    } catch (err: any) { toast(err.message, "error"); }
    finally { setUserProcessingId(null); }
  };

  const handleRoleChange = async (userId: number, currentRole: string) => {
    const action = currentRole === 'admin' ? 'demote' : 'promote';
    const msg = currentRole === 'admin' ? t("demoteConfirm") : t("promoteConfirm");
    if (!confirm(msg)) return;
    try {
      setUserProcessingId(userId);
      const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/${action}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      fetchUsers();
    } catch (err: any) { toast(err.message, "error"); }
    finally { setUserProcessingId(null); }
  };

  const fetchProducts = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/products/admin/all`, { credentials: 'include' });
      if (response.ok) setProducts(await response.json());
    } catch (err) { console.error("Product load failed:", err); }
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
    } catch (err: any) { toast(err.message, "error"); }
  };

  const handleProductToggle = async (id: number, isActive: boolean) => {
    const url = isActive ? `${API_BASE_URL}/products/admin/${id}` : `${API_BASE_URL}/products/admin/${id}/activate`;
    const method = isActive ? 'DELETE' : 'POST';
    try {
      const res = await fetch(url, { method, credentials: 'include' });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      fetchProducts();
    } catch (err: any) { toast(err.message, "error"); }
  };

  const handleApprove = async (id: number, userEmail: string, actualAmount?: number | null) => {
    if (!confirm(t("approveDepositConfirm").replace('{user}', userEmail))) return;
    try {
      setProcessingId(id);
      const response = await fetch(`${API_BASE_URL}/admin/deposits/${id}/approve`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ admin_notes: t("approved"), actual_amount: actualAmount ?? null })
      });
      if (!response.ok) { const e = await response.json(); throw new Error(e.detail || t("approveFailed")); }
      toast(t("depositApprovedToast"), 'success');
      fetchDeposits();
      fetchStats();
    } catch (err: any) { toast(err.message, "error"); }
    finally { setProcessingId(null); }
  };

  const handleReject = async (id: number, userEmail: string) => {
    const reason = prompt(t("rejectDepositPrompt").replace('{user}', userEmail));
    if (!reason) return;
    try {
      setProcessingId(id);
      const response = await fetch(`${API_BASE_URL}/admin/deposits/${id}/reject`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ admin_notes: reason })
      });
      if (!response.ok) { const e = await response.json(); throw new Error(e.detail || t("rejectFailed")); }
      toast(t("depositRejectedToast"), 'info');
      fetchDeposits();
      fetchStats();
    } catch (err: any) { toast(err.message, "error"); }
    finally { setProcessingId(null); }
  };

  const handleFeeChange = async (sectorId: number, fee: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/sectors/${sectorId}/fee`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ fee_percent: fee })
      });
      if (!response.ok) throw new Error(t("sectorFeeUpdateFailed"));
      fetchSectors();
    } catch (err: any) { toast(err.message, "error"); }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
      router.push('/admin/login');
    } catch (err) { router.push('/admin/login'); }
  };

  const copyToClipboard = async (value: string, successMessage: string) => {
    if (!value) {
      toast(t("copyMissing"), 'warning');
      return;
    }
    try {
      await navigator.clipboard.writeText(value);
      toast(successMessage, 'success');
    } catch {
      toast(t("copyFailed"), 'error');
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      approved: "bg-green-500/10 text-green-400 border-green-500/20",
      rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    const labels: Record<string, string> = { pending: t("pending"), approved: t("approved"), rejected: t("rejected") };
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
          <h2 className="text-red-500 font-black mb-4 uppercase tracking-widest text-xl">{t("systemError")}</h2>
          <p className="text-slate-400 text-sm mb-6">{error}</p>
          <button onClick={fetchDeposits} className="w-full py-4 bg-red-600/20 text-red-500 font-black rounded-2xl hover:bg-red-600 hover:text-white transition-all">{t("retry")}</button>
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
            <p className="text-slate-500 text-[10px] font-bold uppercase mt-1 tracking-[0.3em]">{t("superAdmin")}</p>
          </div>
          <div className="flex gap-3 items-center">
            <div className="hidden md:flex bg-green-500/10 border border-green-500/20 px-4 py-2 rounded-full items-center gap-2">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-black text-green-500">{t("online").toUpperCase()}</span>
            </div>
            <button onClick={handleLogout} className="bg-red-500/10 border border-red-500/20 px-4 py-2 rounded-full text-[10px] font-black text-red-500 hover:bg-red-500/20 transition-all">
              {t("logout").toUpperCase()}
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
            {t("depositRequestsTab")}
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-6 py-2 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'users' ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-white'}`}
          >
            {t("usersTab")}
          </button>
          <button
            onClick={() => setActiveTab('products')}
            className={`px-6 py-2 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'products' ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-white'}`}
          >
            {t("productsTab")}
          </button>
          <button
            onClick={() => setActiveTab('sectors')}
            className={`px-6 py-2 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'sectors' ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-white'}`}
          >
            {t("sectorSettingsTab")}
          </button>
        </div>
      </div>

      {/* 메인 컨텐츠 - 스크롤 영역 */}
      <div className="flex-1 overflow-y-auto p-6 md:px-12 md:pb-8">
        <div className="max-w-7xl mx-auto space-y-6">

          {isLoading ? (
            <div className="py-20 text-center animate-pulse">
              <p className="text-blue-500 font-black tracking-[0.5em] text-sm uppercase italic">{t("loadingData")}</p>
            </div>
          ) : activeTab === 'deposits' ? (
            <>
              {/* 통계 카드 - 상단 요약 */}
              <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
                <div className="p-4 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-blue-500 text-[10px] font-black uppercase tracking-widest">{t("totalUsers")}</p>
                  <p className="text-2xl font-black italic mt-1">{stats?.total_users ?? '-'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest">{t("totalDepositsCount")}</p>
                  <p className="text-2xl font-black italic mt-1">{stats?.total_deposits ?? '-'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-yellow-500/10 bg-yellow-500/5">
                  <p className="text-yellow-500 text-[10px] font-black uppercase tracking-widest">{t("pendingCount")}</p>
                  <p className="text-2xl font-black italic mt-1 text-yellow-400">{stats?.pending_count ?? '-'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-green-500/10 bg-green-500/5">
                  <p className="text-green-500 text-[10px] font-black uppercase tracking-widest">{t("approvedCount")}</p>
                  <p className="text-2xl font-black italic mt-1 text-green-400">{stats?.approved_count ?? '-'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-cyan-400 text-[10px] font-black uppercase tracking-widest">{t("totalUSDT")}</p>
                  <p className="text-2xl font-black italic mt-1 text-cyan-300">${stats?.total_approved_usdt?.toLocaleString() ?? '0'}</p>
                </div>
                <div className="p-4 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-purple-400 text-[10px] font-black uppercase tracking-widest">{t("totalJOY")}</p>
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
                        <p className="text-blue-400 text-[10px] font-black uppercase tracking-widest">{t("sectorName")} {sector?.name || ss.sector_id}</p>
                        <p className="text-lg font-black italic mt-1">{ss.deposit_count}{t("items")}</p>
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
                    placeholder={t("searchPlaceholder")}
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
                  <option value="all">{t("allSectors")}</option>
                  {sectors.map(s => (
                    <option key={s.id} value={s.id.toString()}>{t("sectorName")} {s.name}</option>
                  ))}
                </select>
                <div className="flex gap-1">
                  {['all', 'pending', 'approved', 'rejected'].map(s => (
                    <button
                      key={s}
                      onClick={() => setStatusFilter(s)}
                      className={`px-3 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${statusFilter === s ? 'bg-blue-600 text-white' : 'bg-slate-800/50 text-slate-500 hover:text-white'}`}
                    >
                      {s === 'all' ? t("all") : s === 'pending' ? t("pending") : s === 'approved' ? t("approved") : t("rejected")}
                    </button>
                  ))}
                </div>
              </div>

              {/* 입금 요청 테이블 */}
              <div className="rounded-2xl overflow-hidden border border-white/5 bg-slate-900/20">
                {filteredRequests.length === 0 ? (
                  <div className="p-16 text-center text-slate-600 font-bold uppercase tracking-widest text-sm">
                    {searchQuery ? t("noResults") : t("noRequests")}
                  </div>
                ) : (
                  <div className="max-h-[50vh] overflow-y-auto">
                    <table className="w-full text-left">
                      <thead className="bg-white/5 text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] sticky top-0 z-10">
                        <tr>
                          <th className="p-5">{t("id")}</th>
                          <th className="p-5">{t("user")}</th>
                          <th className="p-5">{t("sector")}</th>
                          <th className="p-5">{t("network")}</th>
                          <th className="p-5 text-right">{t("amount")}</th>
                          <th className="p-5 text-right">{t("joyQuantity")}</th>
                          <th className="p-5 text-center">{t("status")}</th>
                          <th className="p-5 text-center">{t("requestDate")}</th>
                          <th className="p-5 text-right">{t("actions")}</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm font-bold">
                        {filteredRequests.map((req) => (
                          <tr key={req.id} className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                            <td className="p-5"><div className="font-mono text-xs text-slate-500">#{req.id}</div></td>
                            <td className="p-5">
                              <div className="font-mono text-xs text-blue-300">{req.user.email}</div>
                              <div className="text-[9px] text-slate-600 mt-1">{req.user.username}</div>
                              <div className="mt-2 flex items-center gap-2">
                                <code className="text-[10px] text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 rounded px-2 py-1 max-w-[210px] truncate">
                                  {req.user.wallet_address || '-'}
                                </code>
                                <button
                                  type="button"
                                  onClick={() => copyToClipboard(req.user.wallet_address || '', t("copiedWallet"))}
                                  className="px-2 py-1 text-[10px] font-black rounded border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 transition-all"
                                >
                                  {t("copy")}
                                </button>
                              </div>
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
                            <td className="p-5 text-right font-mono italic text-slate-300">
                              {req.expected_amount.toLocaleString()} USDT
                              {req.actual_amount != null && req.actual_amount !== req.expected_amount && (
                                <div className={`text-[9px] mt-0.5 ${Math.floor(req.actual_amount) < Math.floor(req.expected_amount) ? 'text-yellow-400' : 'text-green-400'}`}>
                                  {t("actual")}: {req.actual_amount} USDT
                                </div>
                              )}
                            </td>
                            <td className="p-5 text-right font-mono italic text-blue-400">{(req.joy_amount || 0).toLocaleString()} JOY</td>
                            <td className="p-5 text-center">
                              {getStatusBadge(req.status)}
                              {req.detected_tx_hash && (
                                <div className="mt-1">
                                  <a
                                    href={
                                      req.chain === 'TRON'
                                        ? `https://tronscan.org/#/transaction/${req.detected_tx_hash}`
                                        : req.chain === 'Ethereum'
                                        ? `https://etherscan.io/tx/${req.detected_tx_hash}`
                                        : `https://polygonscan.com/tx/${req.detected_tx_hash}`
                                    }
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[9px] text-cyan-400 hover:text-cyan-300 underline"
                                  >
                                    TX: {req.detected_tx_hash.slice(0, 10)}...
                                  </a>
                                </div>
                              )}
                            </td>
                            <td className="p-5 text-center text-slate-500 text-xs">{new Date(req.created_at).toLocaleString('ko-KR')}</td>
                            <td className="p-5 text-right">
                              {req.status === 'pending' ? (
                                <div className="flex gap-2 justify-end">
                                  <button onClick={() => handleApprove(req.id, req.user.email, req.actual_amount)} disabled={processingId === req.id}
                                    className="px-3 py-1.5 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 text-white text-[10px] font-black rounded-lg transition-all uppercase">
                                    {processingId === req.id ? '...' : t("approve")}
                                  </button>
                                  <button onClick={() => handleReject(req.id, req.user.email)} disabled={processingId === req.id}
                                    className="px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 text-white text-[10px] font-black rounded-lg transition-all uppercase">
                                    {t("reject")}
                                  </button>
                                </div>
                              ) : (
                                <span className="text-slate-600 text-[10px] uppercase font-black tracking-widest">
                                  {req.status === 'approved' ? t("completed") : t("rejected")}
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
              <p className="text-slate-600 text-[10px] text-right">{t("totalCount")} {filteredRequests.length} {t("items")}</p>
            </>
          ) : activeTab === 'products' ? (
            /* 상품 관리 탭 */
            <>
              {showProductForm && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                  <div className="bg-slate-900 p-8 rounded-3xl w-full max-w-lg border border-blue-500/20 shadow-2xl relative">
                    <button onClick={() => setShowProductForm(false)} className="absolute top-4 right-4 text-slate-500 hover:text-white text-2xl">×</button>
                    <h2 className="text-xl font-black text-blue-400 mb-6">{editingProduct ? t("editProduct") : t("newProduct")}</h2>
                    <div className="space-y-4">
                      <div>
                        <label className="text-xs text-slate-400 font-bold">{t("productName")}</label>
                        <input value={productForm.name} onChange={e => setProductForm({...productForm, name: e.target.value})}
                          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs text-slate-400 font-bold">{t("joyAmount")}</label>
                          <input type="number" value={productForm.joy_amount} onChange={e => setProductForm({...productForm, joy_amount: Number(e.target.value)})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                        </div>
                        <div>
                          <label className="text-xs text-slate-400 font-bold">{t("priceUSDT")}</label>
                          <input type="number" step="0.01" value={productForm.price_usdt} onChange={e => setProductForm({...productForm, price_usdt: Number(e.target.value)})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs text-slate-400 font-bold">{t("priceKRW")}</label>
                          <input type="number" value={productForm.price_krw} onChange={e => setProductForm({...productForm, price_krw: Number(e.target.value)})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                        </div>
                        <div>
                          <label className="text-xs text-slate-400 font-bold">{t("discountRate")} (%)</label>
                          <input type="number" value={productForm.discount_rate} onChange={e => setProductForm({...productForm, discount_rate: Number(e.target.value)})}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-slate-400 font-bold">{t("description")}</label>
                        <input value={productForm.description} onChange={e => setProductForm({...productForm, description: e.target.value})}
                          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white mt-1" />
                      </div>
                      <button onClick={handleProductSave} className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold text-lg transition-all">
                        {editingProduct ? t("edit") : t("addProduct")}
                      </button>
                    </div>
                  </div>
                </div>
              )}
              <div className="flex justify-between items-center">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">{t("productManagementTitle")}</h2>
                <button onClick={() => openProductForm()} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-black text-white transition-all">
                  + {t("addProduct")}
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {products.map(p => (
                  <div key={p.id} className={`p-6 rounded-2xl border bg-slate-900/40 space-y-3 ${p.is_active ? 'border-white/5' : 'border-red-500/20 opacity-60'}`}>
                    <div className="flex justify-between items-start">
                      <h3 className="text-lg font-black text-white">{p.name}</h3>
                      {!p.is_active && <span className="px-2 py-1 bg-red-500/10 text-red-400 text-[10px] font-black rounded-full">{t("inactive")}</span>}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div><span className="text-slate-500 text-xs">JOY</span><p className="font-bold text-blue-400">{p.joy_amount.toLocaleString()}</p></div>
                      <div><span className="text-slate-500 text-xs">USDT</span><p className="font-bold">{p.price_usdt}</p></div>
                      <div><span className="text-slate-500 text-xs">KRW</span><p className="font-bold text-slate-300">{(p.price_krw || 0).toLocaleString()}</p></div>
                      <div><span className="text-slate-500 text-xs">{t("discountRate")}</span><p className="font-bold text-green-400">{p.discount_rate}%</p></div>
                    </div>
                    {p.description && <p className="text-xs text-slate-500">{p.description}</p>}
                    <div className="flex gap-2 pt-2">
                      <button onClick={() => openProductForm(p)} className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-xs font-bold text-white transition-all">{t("edit")}</button>
                      <button onClick={() => handleProductToggle(p.id, p.is_active)}
                        className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${p.is_active ? 'bg-red-600/20 text-red-400 hover:bg-red-600 hover:text-white' : 'bg-green-600/20 text-green-400 hover:bg-green-600 hover:text-white'}`}>
                        {p.is_active ? t("deactivate") : t("activate")}
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
                  <p className="text-blue-500 text-[10px] font-black uppercase tracking-widest">{t("allUsers")}</p>
                  <p className="text-3xl font-black italic mt-2">{users.length}</p>
                </div>
                <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-yellow-500 text-[10px] font-black uppercase tracking-widest">{t("admins")}</p>
                  <p className="text-3xl font-black italic mt-2">{users.filter(u => u.role === 'admin').length}</p>
                </div>
                <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
                  <p className="text-red-500 text-[10px] font-black uppercase tracking-widest">{t("banned")}</p>
                  <p className="text-3xl font-black italic mt-2">{users.filter(u => u.is_banned).length}</p>
                </div>
              </div>

              <div className="flex-1 relative">
                <input
                  type="text"
                  placeholder={t("searchUsers")}
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
                        <th className="p-5">{t("id")}</th>
                        <th className="p-5">{t("email")}</th>
                        <th className="p-5">{t("username")}</th>
                        <th className="p-5 text-center">{t("role")}</th>
                        <th className="p-5 text-right">{t("joy")}</th>
                        <th className="p-5 text-center">{t("status")}</th>
                        <th className="p-5 text-center">{t("joinDate")}</th>
                        <th className="p-5 text-right">{t("actions")}</th>
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
                          <td className="p-5 font-mono text-xs text-blue-300">{u.email}</td>
                          <td className="p-5 text-xs text-slate-300">{u.username}</td>
                          <td className="p-5 text-center">
                            <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${
                              u.role === 'admin' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                              u.role === 'sector_manager' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                              'bg-slate-500/10 text-slate-400 border-slate-500/20'
                            }`}>
                              {u.role === 'admin' ? t("admin") : u.role === 'sector_manager' ? t("sectorManager") : t("user")}
                            </span>
                          </td>
                          <td className="p-5 text-right font-mono italic text-blue-400">{(u.total_joy || 0).toLocaleString()}</td>
                          <td className="p-5 text-center">
                            {u.is_banned ? (
                              <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase border bg-red-500/10 text-red-400 border-red-500/20">{t("banned")}</span>
                            ) : (
                              <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase border bg-green-500/10 text-green-400 border-green-500/20">{t("normal")}</span>
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
                                {u.is_banned ? t("unban") : t("ban")}
                              </button>
                              <button
                                onClick={() => handleRoleChange(u.id, u.role)}
                                disabled={userProcessingId === u.id}
                                className={`px-3 py-1.5 text-[10px] font-black rounded-lg transition-all uppercase ${
                                  u.role === 'admin' ? 'bg-slate-600 hover:bg-slate-500 text-white' : 'bg-yellow-600 hover:bg-yellow-500 text-white'
                                }`}
                              >
                                {u.role === 'admin' ? t("demote") : t("promote")}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <p className="text-slate-600 text-[10px] text-right">{t("totalCount")} {users.filter(u => !userSearch || u.email.toLowerCase().includes(userSearch.toLowerCase()) || u.username.toLowerCase().includes(userSearch.toLowerCase())).length} {t("items")}</p>
            </>
          ) : (
            /* 섹터 기여분 설정 탭 */
            <div className="space-y-8">
              {/* JOY 시세 설정 */}
              <div className="space-y-4">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">{t("joyExchangeRate")}</h2>
                <div className="p-6 rounded-2xl border border-cyan-500/10 bg-cyan-500/5">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-lg font-black text-white">{t("joyExchangeRate")}</h3>
                      <p className="text-xs text-slate-500 mt-1">{t("joyExchangeDesc")}</p>
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
                      {t("change")}
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
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">{t("referralBonusSettings")}</h2>
                <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/40">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-lg font-black text-white">{t("referralBonusPercent")}</h3>
                      <p className="text-xs text-slate-500 mt-1">{t("referralBonusDesc")}</p>
                    </div>
                    <span className="text-3xl font-black italic text-green-400">{referralBonus}%</span>
                  </div>
                  <div className="grid grid-cols-5 gap-2">
                    {[5, 10, 15, 20, 30].map(pct => (
                      <button
                        key={pct}
                        onClick={() => handleReferralBonusChange(pct)}
                        className={`py-3 rounded-xl text-sm font-black transition-all ${referralBonus === pct
                          ? 'bg-green-600 text-white'
                          : 'bg-slate-800 text-slate-500 hover:bg-slate-700 hover:text-white'
                        }`}
                      >
                        {pct}%
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* 섹터별 기여분 */}
              <div className="space-y-4">
                <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">{t("sectorContribution")}</h2>
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

        {/* Legal Disclaimer */}
        <div className="mt-6 p-3 border-t border-slate-800">
          <p className="text-[10px] text-slate-600 text-center italic">
            {t("legalDisclaimer")}
          </p>
        </div>
      </div>
    </div>
  );
}
