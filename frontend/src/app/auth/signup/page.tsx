"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SignupPage() {
  const router = useRouter();

  // 1. 모든 필드 상태 통합
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [username, setUsername] = useState("");
  const [centerId, setCenterId] = useState("");
  const [ref, setRef] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // 2. 회원가입 처리 로직 (보안 검증 + API 연동)
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // [보안 검증] 윤성 님의 로직 유지
    if (password.length < 12) {
      setError("비밀번호는 12자 이상이어야 합니다.");
      return;
    }
    if (password !== confirm) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }
    if (!username.trim()) {
      setError("이름(닉네임)을 입력해 주세요.");
      return;
    }

    setIsLoading(true);

    try {
      // [성진 형님 백엔드 규격] 필드명 일치화
      const response = await fetch('http://localhost:8000/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: email,        // 서버 규격: 이메일을 username으로 사용
          password: password,
          nickname: username.trim(), // 추가 필드: 이름/닉네임
          center_id: centerId ? Number(centerId) : null, // 숫자 변환
          referral_code: ref.trim() || null // 추천인 코드
        }),
      });

      if (response.ok) {
        alert("회원가입 성공! 이제 로그인을 해주세요.");
        router.push('/auth/login?registered=1'); // 로그인 페이지로 이동
      } else {
        const data = await response.json();
        setError(data.detail || "가입 실패. 입력 정보를 확인하세요.");
      }
    } catch (err) {
      setError("서버 연결 실패! 백엔드 서버가 켜져 있는지 확인하세요.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6 text-white font-sans">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-blue-500/10 shadow-2xl relative">
        <div className="text-center mb-8">
          <h2 className="text-blue-500 text-xs font-black uppercase tracking-[0.4em] mb-2 text-glow">Join JoyCoin</h2>
          <h1 className="text-3xl font-black italic">SIGN UP</h1>
        </div>

        <form onSubmit={handleSignup} className="space-y-4">
          {/* Email / Username */}
          <div className="space-y-1">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Email Address</label>
            <input 
              type="email" placeholder="example@joy.com" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all"
            />
          </div>

          {/* Nickname */}
          <div className="space-y-1">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Display Name</label>
            <input 
              type="text" placeholder="2자 이상 닉네임" required value={username} onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all"
            />
          </div>
          
          {/* Password & Confirm */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Password</label>
              <input 
                type="password" placeholder="12자 이상" required value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-xl text-sm focus:border-blue-500 outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Confirm</label>
              <input 
                type="password" placeholder="비밀번호 확인" required value={confirm} onChange={(e) => setConfirm(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-xl text-sm focus:border-blue-500 outline-none"
              />
            </div>
          </div>

          {/* Center & Referral */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Center ID</label>
              <input 
                type="number" placeholder="ID (1, 2...)" value={centerId} onChange={(e) => setCenterId(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-xl text-sm outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">Referral</label>
              <input 
                type="text" placeholder="Code (JOY...)" value={ref} onChange={(e) => setRef(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-xl text-sm outline-none"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-[10px] font-bold text-center">
              {error}
            </div>
          )}

          <button 
            type="submit" disabled={isLoading}
            className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white font-black rounded-2xl shadow-xl shadow-blue-900/20 active:scale-95 transition-all mt-4"
          >
            {isLoading ? "PROCESSING..." : "REGISTER NOW"}
          </button>
        </form>
      </div>
    </div>
  );
}