"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  // 로그인 처리 함수
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // [치트키] 백엔드 서버 응답이 없을 때 사용하는 임시 우회 로직
    if (email === "admin@test.com" && password === "1234") {
      localStorage.setItem('accessToken', 'dev-bypass-token-2026'); // 임시 열쇠 저장
      alert("임시 계정으로 로그인합니다 (개발자 모드)");
      router.push('/admin/dashboard'); // 대시보드로 즉시 이동
      return; // 아래의 진짜 서버 통신 로직은 실행하지 않고 종료합니다.
    }

    try {
      // 실제 백엔드 서버(Docker)와 통신하는 부분
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email: email, // 형님 서버가 요구하는 필드명
          password: password 
        }),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('accessToken', data.access_token);
        alert("관리자 인증 성공!");
        router.push('/admin/dashboard');
      } else {
        const errorDetail = typeof data.detail === 'object' 
          ? JSON.stringify(data.detail) 
          : data.detail;
        alert(`로그인 실패: ${errorDetail}`); // [object Object] 방지 처리
      }
    } catch (error) {
      // 서버가 꺼져있어도 치트키를 쓰면 여기까지 오지 않습니다.
      alert("서버 연결 실패! (치트키 계정을 사용해 보세요)");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-red-500/10 shadow-2xl">
        <div className="text-center mb-10">
          <h2 className="text-red-500 text-xs font-black uppercase tracking-[0.4em] mb-2">Internal Access</h2>
          <h1 className="text-3xl font-black italic text-white">ADMIN LOGIN</h1>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Admin Email</label>
            <input 
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:outline-none focus:border-red-500 text-white transition-all font-mono"
              placeholder="admin@test.com"
            />
          </div>

          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Admin Password</label>
            <input 
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:outline-none focus:border-red-500 text-white transition-all"
              placeholder="1234"
            />
          </div>

          <button 
            type="submit"
            disabled={isLoading}
            className={`w-full py-4 font-black rounded-2xl shadow-xl transition-all ${
              isLoading ? 'bg-slate-700 cursor-not-allowed text-slate-500' : 'bg-red-600/80 hover:bg-red-600 text-white shadow-red-900/20 active:scale-95'
            }`}
          >
            {isLoading ? "VERIFYING..." : "ENTER DASHBOARD"}
          </button>
        </form>
        
        <p className="text-slate-600 text-[9px] text-center mt-6 uppercase font-bold tracking-widest opacity-50">
          Bypass mode enabled for testing
        </p>
      </div>
    </div>
  );
}