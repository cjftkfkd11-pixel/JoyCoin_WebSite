"use client";

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [registeredMsg, setRegisteredMsg] = useState(false); // 회원가입 완료 메시지 상태
  
  const router = useRouter();
  const searchParams = useSearchParams();

  // 페이지 로드 시 URL에 ?registered=1 이 있는지 확인
  useEffect(() => {
    if (searchParams.get("registered") === "1") {
      setRegisteredMsg(true);
    }
  }, [searchParams]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // 1. 성진 형님 명세서: POST /auth/login 호출
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          username: email, // 서버 규격에 맞춤
          password: password 
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // 2. 토큰 추출
        const token = data.access; 

        // 3. 쿠키 저장 (보안 미들웨어용)
        const expires = new Date();
        expires.setDate(expires.getDate() + 7);
        document.cookie = `accessToken=${token}; path=/; expires=${expires.toUTCString()}; SameSite=Lax`;
        
        // 4. 로컬스토리지 저장
        localStorage.setItem('accessToken', token);
        
        alert("로그인에 성공했습니다!");
        router.push('/admin/dashboard'); 
      } else {
        alert(`로그인 실패: ${data.detail || "아이디 또는 비밀번호를 확인하세요."}`);
      }
    } catch (error) {
      alert("서버 연결 실패! 백엔드 서버 상태를 확인하세요.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6 text-white font-sans">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-blue-500/10 shadow-2xl">
        
        <div className="text-center mb-10">
          <h2 className="text-blue-500 text-xs font-black uppercase tracking-[0.4em] mb-2">Secure Access</h2>
          <h1 className="text-3xl font-black italic">LOGIN</h1>
        </div>

        {/* 회원가입 성공 메시지 알림창 */}
        {registeredMsg && (
          <div className="mb-6 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-bold text-center uppercase tracking-wider animate-pulse">
            Registration Complete. Please Sign In.
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Email Address</label>
            <input 
              type="email" placeholder="admin@joycoin.com" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Password</label>
            <input 
              type="password" placeholder="••••••••" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all"
            />
          </div>

          <button 
            type="submit" disabled={isLoading}
            className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white font-black rounded-2xl shadow-xl shadow-blue-900/20 active:scale-95 transition-all"
          >
            {isLoading ? "AUTHENTICATING..." : "SIGN IN"}
          </button>
        </form>

        <div className="mt-8 text-center border-t border-white/5 pt-8">
          <p className="text-slate-500 text-[10px] font-bold uppercase tracking-[0.2em]">
            New to JoyCoin? <span onClick={() => router.push('/auth/signup')} className="text-blue-500 cursor-pointer hover:text-blue-400 transition-colors">Create Account</span>
          </p>
        </div>
      </div>
    </div>
  );
}