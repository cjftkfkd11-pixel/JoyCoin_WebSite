"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [msg, setMsg] = useState(false);
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => { if (params.get("registered") === "1") setMsg(true); }, [params]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (response.ok) {
        router.push('/buy');
      } else { alert(data.detail || "로그인 실패"); }
    } catch (err) { alert("서버 연결 실패"); }
    finally { setIsLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6 text-white font-sans">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-blue-500/10 shadow-2xl">
        <h1 className="text-3xl font-black italic text-center mb-10 text-blue-500">LOGIN</h1>
        {msg && <div className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs text-center rounded-2xl font-bold">Registration Success! Please Login.</div>}
        <form onSubmit={handleLogin} className="space-y-6">
          <input type="email" placeholder="Email Address" required className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl outline-none focus:border-blue-500" value={email} onChange={e => setEmail(e.target.value)} />
          <input type="password" placeholder="Password" required className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl outline-none focus:border-blue-500" value={password} onChange={e => setPassword(e.target.value)} />
          <button type="submit" disabled={isLoading} className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-2xl font-black transition-all">
            {isLoading ? "AUTHENTICATING..." : "SIGN IN"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-[#020617] text-blue-500 font-black">Loading...</div>}>
      <LoginForm />
    </Suspense>
  );
}
