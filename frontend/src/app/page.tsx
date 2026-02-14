"use client";

import Link from 'next/link';
import { useLanguage } from '@/lib/LanguageContext';
import { useAuth } from '@/lib/AuthContext';

export default function Page() {
  const { t, locale } = useLanguage();
  const { isLoggedIn, isLoading } = useAuth();

  return (
    <div className="flex-1 flex flex-col items-center justify-center space-y-8 sm:space-y-12 px-4 sm:px-6 py-12 sm:py-20 relative min-h-[calc(100vh-80px)]">

      {/* 로고 섹션 */}
      <div className="text-center group">
        <h1 className="text-5xl sm:text-7xl md:text-[10rem] font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-yellow-400 via-red-500 to-blue-500 transition-all duration-1000 group-hover:scale-105 select-none drop-shadow-2xl">
          JOYCOIN
        </h1>
      </div>

      {/* 버튼 섹션 */}
      <div className="flex flex-col md:flex-row items-stretch gap-4 sm:gap-6 w-full max-w-3xl px-4 sm:px-4">
        {isLoading ? (
          <>
            <div className="flex-1 h-24 bg-slate-800/50 rounded-3xl animate-pulse" />
            <div className="flex-1 h-24 bg-slate-800/50 rounded-3xl animate-pulse" />
            <div className="flex-1 h-24 bg-slate-800/50 rounded-3xl animate-pulse" />
          </>
        ) : isLoggedIn ? (
          <>
            {/* 로그인 상태: 마이페이지 + 참여하기 */}
            <Link
              href="/mypage"
              className="flex-1 h-[60px] sm:h-24 flex items-center justify-center px-6 sm:px-4 glass hover:bg-white/10 text-white font-black text-base sm:text-xl rounded-2xl sm:rounded-3xl transition-all border border-white/20 shadow-2xl"
            >
              {t("myPage")}
            </Link>

            <Link
              href="/buy"
              className="flex-1 h-[60px] sm:h-24 flex items-center justify-center px-6 sm:px-4 bg-gradient-to-br from-blue-500 to-indigo-700 hover:from-blue-400 hover:to-indigo-600 text-white font-black text-base sm:text-xl rounded-2xl sm:rounded-3xl shadow-2xl shadow-blue-500/40 transition-all text-center leading-tight"
            >
              {locale === 'ko' ? '조이코인 참여하기' : 'ACCESS JOYCOIN'}
            </Link>
          </>
        ) : (
          <>
            {/* 비로그인 상태: 로그인 + 회원가입 + 참여하기 */}
            <div className="flex-1 flex flex-col items-center gap-1">
              <Link
                href="/auth/login"
                className="w-full h-[60px] sm:h-24 flex items-center justify-center px-6 sm:px-4 glass hover:bg-white/10 text-white font-black text-base sm:text-xl rounded-2xl sm:rounded-3xl transition-all border border-white/20 shadow-2xl"
              >
                {t("login")}
              </Link>
              <Link href="/admin/login" className="text-slate-500 hover:text-slate-400 text-[10px] font-bold uppercase tracking-widest text-center transition-colors py-2 px-3">
                {locale === 'ko' ? '관리자 로그인' : 'ADMIN LOGIN'}
              </Link>
            </div>

            <Link
              href="/auth/signup"
              className="flex-1 h-[60px] sm:h-24 flex items-center justify-center px-6 sm:px-4 glass hover:bg-white/10 text-white font-black text-base sm:text-xl rounded-2xl sm:rounded-3xl transition-all border border-white/20 shadow-2xl"
            >
              {t("signup")}
            </Link>

            <Link
              href="/buy"
              className="flex-1 h-[60px] sm:h-24 flex items-center justify-center px-6 sm:px-4 bg-gradient-to-br from-blue-500 to-indigo-700 hover:from-blue-400 hover:to-indigo-600 text-white font-black text-base sm:text-xl rounded-2xl sm:rounded-3xl shadow-2xl shadow-blue-500/40 transition-all text-center leading-tight"
            >
              {locale === 'ko' ? '조이코인 참여하기' : 'ACCESS JOYCOIN'}
            </Link>
          </>
        )}
      </div>

      <div className="absolute bottom-12 opacity-30 animate-bounce">
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </div>
  );
}
