"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useLanguage } from '@/lib/LanguageContext';
import { useToast } from '@/components/Toast';
import { getApiBaseUrl } from '@/lib/apiBase';

export default function SignupPage() {
  const router = useRouter();
  const { t, locale } = useLanguage();
  const { showModal } = useToast();
  const [sectors, setSectors] = useState<{id: number; name: string}[]>([]);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirm: '',
    nickname: '',
    wallet_address: '',
    sector_id: '',
    ref: ''
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [emailChecked, setEmailChecked] = useState(false);
  const [nicknameChecked, setNicknameChecked] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [nicknameError, setNicknameError] = useState("");
  const [legalChecks, setLegalChecks] = useState({
    terms: false,
    risk: false,
    privacy: false,
  });

  const API_BASE_URL = getApiBaseUrl();

  useEffect(() => {
    fetch(`${API_BASE_URL}/sectors`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setSectors(data);
        }
      })
      .catch(() => setError(locale === 'ko' ? "섹터 정보를 가져오지 못했습니다." : "Failed to load sectors."));
  }, [locale]);

  const checkEmail = async () => {
    if (!formData.email) {
      setEmailError(locale === 'ko' ? "이메일을 입력해주세요." : "Please enter email.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/auth/check-email?email=${encodeURIComponent(formData.email)}`);
      const data = await res.json();
      if (data.exists) {
        setEmailError(locale === 'ko' ? "이미 사용 중인 이메일입니다." : "Email already in use.");
        setEmailChecked(false);
      } else {
        setEmailError("");
        setEmailChecked(true);
      }
    } catch {
      setEmailError(locale === 'ko' ? "확인 실패" : "Check failed");
    }
  };

  const checkNickname = async () => {
    if (!formData.nickname) {
      setNicknameError(locale === 'ko' ? "닉네임을 입력해주세요." : "Please enter nickname.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/auth/check-username?username=${encodeURIComponent(formData.nickname)}`);
      const data = await res.json();
      if (data.exists) {
        setNicknameError(locale === 'ko' ? "이미 사용 중인 닉네임입니다." : "Nickname already in use.");
        setNicknameChecked(false);
      } else {
        setNicknameError("");
        setNicknameChecked(true);
      }
    } catch {
      setNicknameError(locale === 'ko' ? "확인 실패" : "Check failed");
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.password !== formData.confirm) return setError(t("passwordMismatch"));
    if (formData.password.length < 6) return setError(locale === 'ko' ? "비밀번호는 6자 이상이어야 합니다." : "Password must be at least 6 characters.");

    if (!emailChecked) {
      return setError(locale === 'ko' ? "이메일 중복 확인을 해주세요." : "Please check email availability.");
    }
    if (!nicknameChecked) {
      return setError(locale === 'ko' ? "닉네임 중복 확인을 해주세요." : "Please check nickname availability.");
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          username: formData.nickname,
          wallet_address: formData.wallet_address.trim(),
          sector_id: formData.sector_id ? Number(formData.sector_id) : null,
          referral_code: formData.ref || null,
          terms_accepted: legalChecks.terms,
          risk_accepted: legalChecks.risk,
          privacy_accepted: legalChecks.privacy,
          legal_version: '2026-02-10',
          locale,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        showModal({
          type: 'success',
          title: locale === 'ko' ? '회원가입 완료!' : 'Registration Complete!',
          message: locale === 'ko'
            ? '계정 복구 코드가 발급되었습니다.\n마이페이지에서 복구 코드를 확인하고 안전한 곳에 보관하세요.'
            : 'A recovery code has been issued.\nPlease check your recovery code in My Page and keep it safe.',
          sub: locale === 'ko'
            ? '이 코드로 아이디/비밀번호를 찾을 수 있습니다.\n절대 타인에게 공유하지 마세요!'
            : 'You can use this code to recover your account.\nNever share it with anyone!',
          buttonText: locale === 'ko' ? '로그인하러 가기' : 'Go to Login',
          onClose: () => router.push('/auth/login?registered=1'),
        });
      } else {
        const data = await response.json();
        setError(data.detail || (locale === 'ko' ? "가입에 실패했습니다." : "Registration failed."));
      }
    } catch (err) {
      setError(locale === 'ko' ? "서버 연결에 실패했습니다." : "Server connection failed.");
    } finally {
      setLoading(false);
    }
  };

  const allLegalChecked = legalChecks.terms && legalChecks.risk && legalChecks.privacy;

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-4 sm:p-6 py-12 sm:py-24 text-white font-sans">
      <div className="glass p-5 sm:p-10 rounded-2xl sm:rounded-[2.5rem] w-full max-w-md border border-blue-500/10 shadow-2xl">
        <h1 className="text-2xl sm:text-3xl font-black italic text-center mb-5 sm:mb-8 text-blue-500 uppercase">{t("signup")}</h1>

        {/* 복구 코드 안내 */}
        <div className="mb-4 sm:mb-6 p-3 sm:p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
          <p className="text-[11px] sm:text-xs text-yellow-400 font-semibold flex items-center gap-2">
            <span className="text-base sm:text-lg">🔑</span>
            {locale === 'ko'
              ? "회원가입 시 고유 복구 코드가 발급됩니다. 이 코드로 아이디/비밀번호를 찾을 수 있으니 꼭 보관하세요!"
              : "A unique recovery code will be issued upon signup. Keep it safe to recover your account!"}
          </p>
        </div>

        <form onSubmit={handleSignup} className="space-y-4">
          {/* 닉네임 */}
          <div>
            <div className="flex gap-2">
              <input type="text" placeholder={t("username")} required
                className="flex-1 bg-slate-900/50 border border-slate-800 p-3 sm:p-4 rounded-xl sm:rounded-2xl outline-none focus:border-blue-500 text-sm sm:text-base"
                value={formData.nickname}
                onChange={e => { setFormData({...formData, nickname: e.target.value}); setNicknameChecked(false); }} />
              <button type="button" onClick={checkNickname}
                className="px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-xs font-bold transition-all whitespace-nowrap">
                {locale === 'ko' ? '중복확인' : 'Check'}
              </button>
            </div>
            {nicknameError && <p className="text-red-400 text-xs mt-1">{nicknameError}</p>}
            {nicknameChecked && !nicknameError && <p className="text-green-400 text-xs mt-1">{locale === 'ko' ? '사용 가능' : 'Available'}</p>}
          </div>

          {/* 이메일 */}
          <div>
            <div className="flex gap-2">
              <input type="email" placeholder={t("email")} required
                className="flex-1 bg-slate-900/50 border border-slate-800 p-3 sm:p-4 rounded-xl sm:rounded-2xl outline-none focus:border-blue-500 text-sm sm:text-base"
                value={formData.email}
                onChange={e => { setFormData({...formData, email: e.target.value}); setEmailChecked(false); }} />
              <button type="button" onClick={checkEmail}
                className="px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-xs font-bold transition-all whitespace-nowrap">
                {locale === 'ko' ? '중복확인' : 'Check'}
              </button>
            </div>
            {emailError && <p className="text-red-400 text-xs mt-1">{emailError}</p>}
            {emailChecked && !emailError && <p className="text-green-400 text-xs mt-1">{locale === 'ko' ? '사용 가능' : 'Available'}</p>}
          </div>

          <input type="password" placeholder={locale === 'ko' ? "비밀번호 (6자 이상)" : "Password (6+ chars)"} required
            className="w-full bg-slate-900/50 border border-slate-800 p-3 sm:p-4 rounded-xl sm:rounded-2xl outline-none focus:border-blue-500 text-sm sm:text-base"
            value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} />

          <input type="password" placeholder={t("confirmPassword")} required
            className="w-full bg-slate-900/50 border border-slate-800 p-3 sm:p-4 rounded-xl sm:rounded-2xl outline-none focus:border-blue-500 text-sm sm:text-base"
            value={formData.confirm} onChange={e => setFormData({...formData, confirm: e.target.value})} />

          <div>
            <input
              type="text"
              placeholder={locale === 'ko' ? 'JOY 수령 지갑 주소' : 'JOY receiving wallet address'}
              required
              className="w-full bg-slate-900/50 border border-slate-800 p-3 sm:p-4 rounded-xl sm:rounded-2xl outline-none focus:border-blue-500 text-sm sm:text-base"
              value={formData.wallet_address}
              onChange={e => setFormData({...formData, wallet_address: e.target.value})}
            />
            <p className="text-[10px] sm:text-xs text-red-400/70 mt-1 ml-1">
              {locale === 'ko'
                ? '⚠️ 지갑 주소를 잘못 입력하여 발생하는 코인 미수령 등의 문제는 본인 책임이며, 회사는 이에 대해 책임지지 않습니다.'
                : '⚠️ The company is not responsible for any loss caused by incorrect wallet address entry.'}
            </p>
          </div>

          <select
            required
            className="w-full bg-slate-900/50 border border-slate-800 p-3 sm:p-4 rounded-xl sm:rounded-2xl outline-none focus:border-blue-500 text-white text-sm sm:text-base"
            value={formData.sector_id}
            onChange={e => setFormData({...formData, sector_id: e.target.value})}
          >
            <option value="">{locale === 'ko' ? "소속 섹터를 선택하세요" : "Select your sector"}</option>
            {sectors.map(s => (
              <option key={s.id} value={s.id} className="text-black">
                {locale === 'ko' ? `섹터 ${s.name}` : `Sector ${s.name}`}
              </option>
            ))}
          </select>

          <input type="text" placeholder={`${t("referralCode")} (${t("optional")})`}
            className="w-full bg-slate-900/50 border border-slate-800 p-3 sm:p-4 rounded-xl sm:rounded-2xl outline-none focus:border-blue-500 text-sm sm:text-base"
            value={formData.ref} onChange={e => setFormData({...formData, ref: e.target.value})} />

          {/* Legal agreements */}
          <div className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl space-y-2">
            <p className="text-[11px] text-slate-400 font-semibold mb-1">
              {locale === 'ko' ? '필수 약관 동의' : 'Required Agreements'}
            </p>
            <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={legalChecks.terms}
                onChange={(e) => setLegalChecks((prev) => ({ ...prev, terms: e.target.checked }))}
                className="mt-0.5 accent-cyan-400"
              />
              <span>
                {locale === 'ko' ? '이용약관에 동의합니다. ' : 'I agree to the Terms of Use. '}
                <a href="/legal/terms" target="_blank" className="text-cyan-400 hover:text-cyan-300 underline">
                  {locale === 'ko' ? '[보기]' : '[View]'}
                </a>
              </span>
            </label>
            <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={legalChecks.risk}
                onChange={(e) => setLegalChecks((prev) => ({ ...prev, risk: e.target.checked }))}
                className="mt-0.5 accent-cyan-400"
              />
              <span>
                {locale === 'ko' ? '위험 고지에 동의합니다. ' : 'I agree to the Risk Disclosure. '}
                <a href="/legal/risk" target="_blank" className="text-cyan-400 hover:text-cyan-300 underline">
                  {locale === 'ko' ? '[보기]' : '[View]'}
                </a>
              </span>
            </label>
            <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={legalChecks.privacy}
                onChange={(e) => setLegalChecks((prev) => ({ ...prev, privacy: e.target.checked }))}
                className="mt-0.5 accent-cyan-400"
              />
              <span>
                {locale === 'ko' ? '개인정보처리방침에 동의합니다. ' : 'I agree to the Privacy Policy. '}
                <a href="/legal/privacy" target="_blank" className="text-cyan-400 hover:text-cyan-300 underline">
                  {locale === 'ko' ? '[보기]' : '[View]'}
                </a>
              </span>
            </label>
            {!allLegalChecked && (
              <p className="text-[10px] text-yellow-400/70 ml-5">
                {locale === 'ko' ? '모든 약관에 동의해야 가입할 수 있습니다.' : 'You must agree to all terms to sign up.'}
              </p>
            )}
          </div>

          {error && <p className="text-red-400 text-xs text-center font-bold animate-pulse">{error}</p>}

          <button type="submit" disabled={loading || !allLegalChecked}
            className={`w-full py-3 sm:py-4 rounded-xl sm:rounded-2xl font-black transition-all active:scale-95 ${
              allLegalChecked
                ? 'bg-blue-600 hover:bg-blue-500 text-white'
                : 'bg-slate-800 text-slate-600 cursor-not-allowed'
            }`}>
            {loading ? t("loading") : t("signup").toUpperCase()}
          </button>
        </form>

        <div className="mt-6 space-y-2 text-center">
          <p className="text-slate-400 text-sm">
            {t("alreadyHaveAccount")}{' '}
            <Link href="/auth/login" className="text-blue-500 hover:text-blue-400 font-semibold">
              {t("login")}
            </Link>
          </p>
          <p className="text-slate-500 text-xs">
            <Link href="/auth/recover" className="hover:text-slate-400">
              {locale === 'ko' ? '아이디/비밀번호 찾기' : 'Find ID/Password'}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
