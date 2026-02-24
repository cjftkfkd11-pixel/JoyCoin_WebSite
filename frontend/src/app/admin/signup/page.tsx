"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/Toast';
import { getApiBaseUrl } from '@/lib/apiBase';
import { useLanguage } from '@/lib/LanguageContext';

export default function AdminUserCreatePage() {
  const router = useRouter();
  const { toast } = useToast();
  const { t, locale } = useLanguage();

  const [authChecked, setAuthChecked] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [walletAddress, setWalletAddress] = useState('');
  const [referrer, setReferrer] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sectors, setSectors] = useState<{ id: number; name: string }[]>([]);
  const [selectedSectorId, setSelectedSectorId] = useState<string>('');

  const API_BASE_URL = getApiBaseUrl();

  // 관리자 인증 확인
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/me`, { credentials: 'include' });
        if (res.ok) {
          const me = await res.json();
          if (me.role === 'admin') {
            setIsAdmin(true);
            // 섹터 목록 로드
            const sectorRes = await fetch(`${API_BASE_URL}/sectors`);
            if (sectorRes.ok) {
              const data = await sectorRes.json();
              if (Array.isArray(data)) setSectors(data);
            }
          }
        }
      } catch {}
      setAuthChecked(true);
    };
    checkAuth();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      toast(locale === 'ko' ? '닉네임을 입력하세요.' : 'Please enter a username.', 'error');
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          username: username.trim(),
          wallet_address: walletAddress.trim(),
          sector_id: selectedSectorId ? Number(selectedSectorId) : null,
          referral_code: referrer || null,
          terms_accepted: true,
          risk_accepted: true,
          privacy_accepted: true,
          legal_version: '2026-02-10',
          locale,
        }),
      });

      if (response.ok) {
        toast(locale === 'ko' ? '계정 생성 완료!' : 'Account created!', 'success');
        setEmail(''); setPassword(''); setUsername(''); setWalletAddress(''); setReferrer(''); setSelectedSectorId('');
      } else {
        const errorData = await response.json();
        const detail = typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : errorData.detail;
        toast(`${locale === 'ko' ? '생성 실패' : 'Creation failed'}: ${detail}`, 'error');
      }
    } catch {
      toast(t('serverError'), 'error');
    } finally {
      setIsLoading(false);
    }
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#020617] text-blue-500 font-black">
        {t('loading').toUpperCase()}
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6 text-white font-sans">
        <div className="text-center space-y-6">
          <p className="text-red-400 font-black text-lg">{locale === 'ko' ? '관리자 권한이 필요합니다.' : 'Admin access required.'}</p>
          <button onClick={() => router.push('/admin/login')}
            className="px-6 py-3 bg-red-600 hover:bg-red-500 rounded-xl font-black text-sm transition-all">
            {locale === 'ko' ? '관리자 로그인' : 'Admin Login'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6 text-white font-sans">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-blue-500/10 shadow-2xl relative">
        <div className="text-center mb-8">
          <h2 className="text-blue-500 text-xs font-black uppercase tracking-[0.4em] mb-2">
            {locale === 'ko' ? '관리자 전용' : 'Admin Only'}
          </h2>
          <h1 className="text-3xl font-black italic">
            {locale === 'ko' ? '유저 계정 생성' : 'Create User Account'}
          </h1>
          <p className="text-xs text-slate-500 mt-2">
            {locale === 'ko' ? '* 일반 유저 계정으로 생성됩니다 (관리자 권한 없음)' : '* Creates a regular user account (no admin rights)'}
          </p>
        </div>

        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2 block mb-1">{t('email')}</label>
            <input type="email" placeholder="user@example.com" required value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all" />
          </div>

          <div>
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2 block mb-1">{t('username')}</label>
            <input type="text" placeholder={locale === 'ko' ? '닉네임' : 'Username'} required value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all" />
          </div>

          <div>
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2 block mb-1">{t('password')}</label>
            <input type="password" placeholder="••••••••" required value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all" />
          </div>

          <div>
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2 block mb-1">
              {locale === 'ko' ? '섹터 선택' : 'Select Sector'}
            </label>
            <select value={selectedSectorId} onChange={(e) => setSelectedSectorId(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all text-white appearance-none cursor-pointer">
              <option value="">{locale === 'ko' ? '섹터 선택 (선택사항)' : 'Select Sector (Optional)'}</option>
              {sectors.map((s) => (
                <option key={s.id} value={s.id} className="bg-slate-900">
                  {locale === 'ko' ? `섹터 ${s.name}` : `Sector ${s.name}`}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2 block mb-1">
              {locale === 'ko' ? 'JOY 지갑 주소' : 'JOY Wallet Address'}
            </label>
            <input type="text" placeholder={locale === 'ko' ? '지갑 주소 입력' : 'Enter wallet address'} required value={walletAddress}
              onChange={(e) => setWalletAddress(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all" />
          </div>

          <div>
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2 block mb-1">
              {t('referralCode')} ({t('optional')})
            </label>
            <input type="text" placeholder="JOY..." value={referrer}
              onChange={(e) => setReferrer(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all" />
          </div>

          <div className="flex gap-3">
            <button type="button" onClick={() => router.push('/admin/dashboard')}
              className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-2xl transition-all">
              {locale === 'ko' ? '← 대시보드' : '← Dashboard'}
            </button>
            <button type="submit" disabled={isLoading}
              className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 text-white font-black rounded-2xl shadow-xl shadow-blue-900/20 active:scale-95 transition-all disabled:opacity-50">
              {isLoading ? t('loading').toUpperCase() : (locale === 'ko' ? '계정 생성' : 'Create Account')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
