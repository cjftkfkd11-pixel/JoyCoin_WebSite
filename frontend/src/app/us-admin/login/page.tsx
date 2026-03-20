"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { getApiBaseUrl } from '@/lib/apiBase';

export default function UsAdminLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const API = getApiBaseUrl();
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || '로그인에 실패했습니다.');
        return;
      }

      const meRes = await fetch(`${API}/auth/me`, { credentials: 'include' });
      if (meRes.ok) {
        const me = await meRes.json();
        if (me.role !== 'us_admin' && me.role !== 'admin') {
          await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' });
          setError('미국관리자 권한이 없습니다.');
          return;
        }
      }
      router.push('/us-admin/dashboard');
    } catch {
      setError('서버 연결에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-blue-500/10 shadow-2xl">
        <div className="text-center mb-10">
          <h2 className="text-blue-400 text-xs font-black uppercase tracking-[0.4em] mb-2">US ADMIN ACCESS</h2>
          <h1 className="text-3xl font-black italic text-white">미국 관리자 로그인</h1>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <input
            type="email"
            required
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:outline-none focus:border-blue-500 text-white transition-all font-mono"
            placeholder="admin@example.com"
          />
          <input
            type="password"
            required
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:outline-none focus:border-blue-500 text-white transition-all"
            placeholder="••••••••"
          />

          {error && <p className="text-red-400 text-sm text-center">{error}</p>}

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-4 font-black rounded-2xl shadow-xl transition-all ${
              isLoading ? 'bg-slate-700 cursor-not-allowed text-slate-500' : 'bg-blue-600/80 hover:bg-blue-600 text-white active:scale-95'
            }`}
          >
            {isLoading ? '확인 중...' : '대시보드 입장'}
          </button>
        </form>

        <p className="text-slate-600 text-[9px] text-center mt-6 uppercase font-bold tracking-widest opacity-50">
          AUTHORIZED PERSONNEL ONLY
        </p>
      </div>
    </div>
  );
}
