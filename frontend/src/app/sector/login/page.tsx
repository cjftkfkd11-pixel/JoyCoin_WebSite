"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { getApiBaseUrl } from '@/lib/apiBase';
import { useLanguage } from '@/lib/LanguageContext';

export default function SectorLogin() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { t } = useLanguage();

  const API_BASE_URL = getApiBaseUrl();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || t("loginFailed"));
      }

      // 로그인 성공 후 역할 확인
      const meRes = await fetch(`${API_BASE_URL}/auth/me`, { credentials: 'include' });
      if (meRes.ok) {
        const user = await meRes.json();
        if (user.role !== 'sector_manager') {
          setError(t("notSectorManager"));
          await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
          return;
        }
        router.push('/sector/dashboard');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-black italic text-blue-500 uppercase tracking-tighter">{t("sector")}</h1>
          <p className="text-slate-500 text-[10px] font-bold uppercase mt-2 tracking-[0.3em]">{t("managerLogin")}</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs text-center font-bold">
              {error}
            </div>
          )}

          <input
            type="email"
            placeholder={t("email")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-4 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
          />
          <input
            type="password"
            placeholder={t("password")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-4 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-4 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white font-black text-sm rounded-xl transition-all uppercase tracking-widest"
          >
            {isLoading ? t("loading").toUpperCase() : t("login").toUpperCase()}
          </button>
        </form>
      </div>
    </div>
  );
}
