"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SignupPage() {
  const router = useRouter();
  const [centers, setCenters] = useState<{id: number; name: string; region: string}[]>([]);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirm: '',
    nickname: '',
    center_id: '', // [중요] 이름을 center_id로 통일합니다.
    ref: ''
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // 1. 센터 목록 불러오기
  useEffect(() => {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    fetch(`${API_BASE_URL}/centers`)
      .then(res => res.json())
      .then(data => {
        // 형님이 확인하신 데이터가 배열이므로 바로 넣습니다.
        if (Array.isArray(data)) {
          setCenters(data);
        }
      })
      .catch(() => setError("센터 정보를 가져오지 못했습니다."));
  }, []);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.password !== formData.confirm) return setError("비밀번호가 일치하지 않습니다.");
    if (formData.password.length < 12) return setError("비밀번호 12자 이상 필수입니다.");

    setLoading(true);
    setError("");

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          username: formData.nickname,
          center_id: Number(formData.center_id), // 숫자로 변환해서 전송
          referral_code: formData.ref || null
        }),
      });

      if (response.ok) {
        router.push('/auth/login?registered=1');
      } else {
        const data = await response.json();
        setError(data.detail || "가입에 실패했습니다.");
      }
    } catch (err) {
      setError("서버 연결에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6 text-white font-sans">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-blue-500/10 shadow-2xl">
        <h1 className="text-3xl font-black italic text-center mb-10 text-blue-500 uppercase">Create Account</h1>
        
        <form onSubmit={handleSignup} className="space-y-4">
          <input type="text" placeholder="Your Nickname" required 
            className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl outline-none focus:border-blue-500"
            value={formData.nickname} onChange={e => setFormData({...formData, nickname: e.target.value})} />

          <input type="email" placeholder="Email Address" required 
            className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl outline-none focus:border-blue-500"
            value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />

          <input type="password" placeholder="Password (12+ chars)" required 
            className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl outline-none focus:border-blue-500"
            value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} />
          
          <input type="password" placeholder="Confirm Password" required 
            className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl outline-none focus:border-blue-500"
            value={formData.confirm} onChange={e => setFormData({...formData, confirm: e.target.value})} />

          {/* 센터 선택 드롭다운 */}
          <select 
            required 
            className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl outline-none focus:border-blue-500 text-white"
            value={formData.center_id} // state 이름과 일치시킴
            onChange={e => {
              console.log("선택된 센터 ID:", e.target.value); // [체크용 로그]
              setFormData({...formData, center_id: e.target.value});
            }}
          >
            <option value="">소속 센터를 선택하세요</option>
            {centers.map(c => (
              <option key={c.id} value={c.id} className="text-black">
                {c.name} ({c.region})
              </option>
            ))}
          </select>

          <input type="text" placeholder="Referral Code (Optional)" 
            className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl outline-none focus:border-blue-500"
            value={formData.ref} onChange={e => setFormData({...formData, ref: e.target.value})} />

          {error && <p className="text-red-400 text-xs text-center font-bold animate-pulse">{error}</p>}

          <button type="submit" disabled={loading} 
            className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-2xl font-black transition-all active:scale-95">
            {loading ? "PROCESSING..." : "JOIN JOYCOIN"}
          </button>
        </form>
      </div>
    </div>
  );
}