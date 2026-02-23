"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/Toast';
import { getApiBaseUrl } from '@/lib/apiBase';
import { useLanguage } from '@/lib/LanguageContext';

export default function SignupPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { t, locale } = useLanguage();

  // 1. 입력 데이터를 담을 바구니(상태) 만들기
  const [email, setEmail] = useState(''); // 화면에는 Email로 표시하지만 서버에는 username으로 보냅니다.
  const [password, setPassword] = useState('');
  const [walletAddress, setWalletAddress] = useState('');
  const [referrer, setReferrer] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 2. 센터 목록을 위한 상태
  const [centers, setCenters] = useState<{ id: number; name: string; region: string }[]>([]);
  const [selectedCenterId, setSelectedCenterId] = useState<string>("");

  // 3. 페이지가 열리자마자 서버에서 센터 목록을 가져옵니다.
  useEffect(() => {
    const fetchCenters = async () => {
      try {
        const API_BASE_URL = getApiBaseUrl();
        const response = await fetch(`${API_BASE_URL}/centers`);
        if (response.ok) {
          const data = await response.json();
          setCenters(data);
        }
      } catch (error) {
        console.error("센터 목록을 가져오는데 실패했습니다:", error);
      }
    };
    fetchCenters();
  }, []);

  // 4. 회원가입 버튼을 눌렀을 때 실행되는 함수
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // 백엔드 스키마에 맞춘 데이터 구성
      const signupData = {
        email: email,
        password: password,
        username: email.split('@')[0], // 이메일 앞부분을 username으로 사용
        wallet_address: walletAddress.trim(),
        center_id: Number(selectedCenterId),
        referral_code: referrer || null,
        terms_accepted: true,
        risk_accepted: true,
        privacy_accepted: true,
        legal_version: "2026-02-10",
        locale,
      };

      const API_BASE_URL = getApiBaseUrl();
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signupData),
      });

      if (response.ok) {
        toast(t("adminSignupSuccess"), "success");
        router.push('/auth/login');
      } else {
        const errorData = await response.json();
        const detail = typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : errorData.detail;
        toast(`${t("adminSignupFailed")}: ${detail}`, "error");
      }
    } catch (error) {
      toast(t("serverConnectionFailed"), "error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6 text-white font-sans">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-md border border-blue-500/10 shadow-2xl relative">
        <div className="text-center mb-10">
          <h2 className="text-blue-500 text-xs font-black uppercase tracking-[0.4em] mb-2">{t("joinJoycoin")}</h2>
          <h1 className="text-3xl font-black italic">{t("signup").toUpperCase()}</h1>
        </div>

        <form onSubmit={handleSignup} className="space-y-6">
          {/* 이메일(Username) 입력창 */}
          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">{t("email")}</label>
            <input 
              type="email" placeholder="example@joy.com" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all"
            />
          </div>
          
          {/* 비밀번호 입력창 */}
          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">{t("password")}</label>
            <input 
              type="password" placeholder="••••••••" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all"
            />
          </div>

          {/* 센터 선택 드롭다운 (GET /centers 연동) */}
          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">{t("selectCenter")}</label>
            <select 
              required
              value={selectedCenterId}
              onChange={(e) => setSelectedCenterId(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all text-white appearance-none cursor-pointer"
            >
              <option value="" disabled>{t("selectCenter")}</option>
              {centers.map((center) => (
                <option key={center.id} value={center.id} className="bg-slate-900">
                  {center.name} ({center.region})
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">{t("joyWalletAddress")}</label>
            <input
              type="text"
              placeholder={t("joyWalletPlaceholder")}
              required
              value={walletAddress}
              onChange={(e) => setWalletAddress(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all"
            />
          </div>

          {/* 추천인 코드 입력창 */}
          <div className="space-y-2">
            <label className="text-slate-500 text-[10px] font-bold uppercase ml-2">{t("referralCodeOptional")}</label>
            <input 
              type="text" placeholder={t("referralCodePlaceholder")} value={referrer} onChange={(e) => setReferrer(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-800 p-4 rounded-2xl focus:border-blue-500 outline-none transition-all"
            />
          </div>

          <button 
            type="submit" disabled={isLoading}
            className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white font-black rounded-2xl shadow-xl shadow-blue-900/20 active:scale-95 transition-all"
          >
            {isLoading ? t("loading").toUpperCase() : t("registerNow").toUpperCase()}
          </button>
        </form>
      </div>
    </div>
  );
}
