"use client";

import { useLanguage } from "@/lib/LanguageContext";
import { useAuth } from "@/lib/AuthContext";
import { useRouter } from "next/navigation";

export default function HeaderNav() {
  const { locale, setLocale, t } = useLanguage();
  const { user, isLoggedIn, isLoading, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push('/');
  };

  return (
    <div className="flex items-center space-x-4 pointer-events-auto">
      <nav className="hidden lg:flex items-center space-x-8 text-base font-bold text-white/80 mr-4">
        {isLoading ? null : isLoggedIn ? (
          <>
            <a href="/mypage" className="hover:text-blue-400 transition-colors">
              {t("myPage")}
            </a>
            <a href="/buy" className="hover:text-blue-400 transition-colors">
              {t("buy")}
            </a>
            {(user?.role === 'admin' || user?.role === 'us_admin' || user?.role === 'sector_manager') && (
              <a href="/admin/dashboard" className={`transition-colors ${user?.role === 'sector_manager' ? 'text-cyan-400 hover:text-cyan-300' : user?.role === 'us_admin' ? 'text-green-400 hover:text-green-300' : 'text-yellow-400 hover:text-yellow-300'}`}>
                {user?.role === 'sector_manager'
                  ? (locale === 'ko' ? '섹터관리' : 'Sector')
                  : user?.role === 'us_admin'
                  ? (locale === 'ko' ? 'US관리자' : 'US Admin')
                  : (locale === 'ko' ? '관리자' : 'Admin')}
              </a>
            )}
            <button onClick={handleLogout} className="hover:text-red-400 transition-colors">
              {t("logout")}
            </button>
          </>
        ) : (
          <>
            <a href="/auth/signup" className="hover:text-blue-400 transition-colors">
              {t("signup")}
            </a>
            <a href="/auth/login" className="hover:text-blue-400 transition-colors">
              {t("login")}
            </a>
            <a href="/buy" className="hover:text-blue-400 transition-colors">
              {t("buy")}
            </a>
          </>
        )}
      </nav>

      {/* 언어 선택 토글 */}
      <div className="flex items-center bg-white/5 border border-white/10 rounded-full p-0.5">
        <button
          onClick={() => setLocale("ko")}
          className={`px-3 py-1.5 rounded-full text-[11px] font-black tracking-wide transition-all ${
            locale === "ko"
              ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
              : "text-slate-400 hover:text-white"
          }`}
        >
          한국어
        </button>
        <button
          onClick={() => setLocale("en")}
          className={`px-3 py-1.5 rounded-full text-[11px] font-black tracking-wide transition-all ${
            locale === "en"
              ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
              : "text-slate-400 hover:text-white"
          }`}
        >
          ENG
        </button>
      </div>
    </div>
  );
}
