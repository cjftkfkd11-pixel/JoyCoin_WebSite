"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/Toast';
import { getApiBaseUrl } from '@/lib/apiBase';
import { useLanguage } from '@/lib/LanguageContext';

export default function AdminLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useLanguage();

  // 로그인 처리 함수
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const API_BASE_URL = getApiBaseUrl();
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        // role 검증: admin 권한인지 확인
        const meRes = await fetch(`${API_BASE_URL}/auth/me`, { credentials: 'include' });
        if (meRes.ok) {
          const me = await meRes.json();
          if (me.role !== 'admin') {
            // 권한 없으면 로그아웃 후 에러 표시
            await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
            toast(t("notAdminRole"), "error");
            return;
          }
        }
        router.push('/admin/dashboard');
      } else {
        const errorDetail = typeof data.detail === 'object'
          ? JSON.stringify(data.detail)
          : data.detail;
        toast(`${t("loginFailed")}: ${errorDetail}`, "error");
      }
    } catch (error) {
      toast(t("serverError"), "error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-red-500/10 shadow-2xl">
        <div className="text-center mb-10">
          <h2 className="text-red-500 text-xs font-black uppercase tracking-[0.4em] mb-2">{t("internalAccess")}</h2>
          <h1 className="text-3xl font-black italic text-white">{t("adminLogin").toUpperCase()}</h1>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">{t("adminEmail")}</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:outline-none focus:border-red-500 text-white transition-all font-mono"
              placeholder="admin@example.com"
            />
          </div>

          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">{t("adminPassword")}</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:outline-none focus:border-red-500 text-white transition-all"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-4 font-black rounded-2xl shadow-xl transition-all ${
              isLoading ? 'bg-slate-700 cursor-not-allowed text-slate-500' : 'bg-red-600/80 hover:bg-red-600 text-white shadow-red-900/20 active:scale-95'
            }`}
          >
            {isLoading ? t("verifying").toUpperCase() : t("enterDashboard").toUpperCase()}
          </button>
        </form>

        <p className="text-slate-600 text-[9px] text-center mt-6 uppercase font-bold tracking-widest opacity-50">
          {t("authorizedOnly")}
        </p>
      </div>
    </div>
  );
}
