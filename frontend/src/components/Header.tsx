"use client";

import { useLanguage } from "@/lib/LanguageContext";
import { useAuth } from "@/lib/AuthContext";
import { useRouter } from "next/navigation";

export default function Header() {
  const { locale, setLocale, t } = useLanguage();
  const { user, isLoggedIn, isLoading, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push('/');
  };

  const toggleLocale = () => {
    setLocale(locale === "en" ? "ko" : "en");
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-[60] px-4 md:px-10 py-5 flex justify-between items-center pointer-events-none">
      <div className="flex items-center space-x-4 pointer-events-auto">
        <a
          href="/"
          className="text-2xl md:text-3xl font-black tracking-tighter text-blue-500 cursor-pointer drop-shadow-lg"
        >
          JOYCOIN
        </a>
      </div>

      <div className="flex items-center space-x-4 pointer-events-auto">
        {/* Language Toggle */}
        <button
          onClick={toggleLocale}
          className="bg-slate-800/50 text-slate-300 px-3 py-1.5 rounded-xl text-xs font-bold border border-slate-700/50 hover:bg-slate-700/50 transition-all"
        >
          {locale === "en" ? "한국어" : "English"}
        </button>

        {/* Navigation */}
        <nav className="hidden lg:flex items-center space-x-6 text-base font-bold text-white/80">
          {isLoading ? (
            <div className="w-32 h-6 bg-slate-800/50 rounded animate-pulse" />
          ) : isLoggedIn ? (
            <>
              <a href="/mypage" className="hover:text-blue-400 transition-colors">
                {t("myPage")}
              </a>
              <a href="/buy" className="hover:text-blue-400 transition-colors">
                {t("buy")}
              </a>
              {user?.role === "admin" && (
                <a href="/admin/dashboard" className="hover:text-yellow-400 transition-colors text-yellow-500">
                  {t("admin")}
                </a>
              )}
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

        {/* User Actions */}
        {isLoading ? (
          <div className="w-20 h-10 bg-slate-800/50 rounded-2xl animate-pulse" />
        ) : isLoggedIn ? (
          <div className="flex items-center space-x-3">
            <span className="text-sm font-bold text-slate-400 hidden md:block">
              {user?.username}
            </span>
            <button
              onClick={handleLogout}
              className="bg-red-500/20 text-red-400 px-4 py-2 rounded-2xl border border-red-500/30 hover:bg-red-500/30 transition-all active:scale-95 font-bold text-sm"
            >
              {t("logout")}
            </button>
          </div>
        ) : (
          <a
            href="/auth/login"
            className="bg-blue-500/20 text-blue-400 px-4 py-2 rounded-2xl border border-blue-500/30 hover:bg-blue-500/30 transition-all active:scale-95 font-bold text-sm"
          >
            {t("login")}
          </a>
        )}
      </div>
    </div>
  );
}
