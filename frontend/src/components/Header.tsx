"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAuth } from "@/lib/AuthContext";

export default function Header() {
  const { locale, setLocale, t } = useLanguage();
  const { user, isLoggedIn, isLoading, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    window.location.href = '/';
  };

  const toggleLocale = () => {
    setLocale(locale === "en" ? "ko" : "en");
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  return (
    <>
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
            {locale === "en" ? "한국어" : "ENG"}
          </button>

          {/* Desktop Navigation */}
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

          {/* Desktop User Actions */}
          <div className="hidden lg:flex items-center">
            {isLoading ? (
              <div className="w-20 h-10 bg-slate-800/50 rounded-2xl animate-pulse" />
            ) : isLoggedIn ? (
              <div className="flex items-center space-x-3">
                <span className="text-sm font-bold text-slate-400">
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

          {/* Mobile Hamburger Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden flex flex-col justify-center items-center w-10 h-10 bg-slate-800/50 rounded-xl border border-slate-700/50"
          >
            <span className={`block w-5 h-0.5 bg-white transition-all duration-300 ${mobileMenuOpen ? 'rotate-45 translate-y-1' : ''}`} />
            <span className={`block w-5 h-0.5 bg-white my-1 transition-all duration-300 ${mobileMenuOpen ? 'opacity-0' : ''}`} />
            <span className={`block w-5 h-0.5 bg-white transition-all duration-300 ${mobileMenuOpen ? '-rotate-45 -translate-y-1' : ''}`} />
          </button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-[55] lg:hidden">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={closeMobileMenu} />
          <div className="absolute top-20 left-4 right-4 bg-slate-900/95 border border-slate-700/50 rounded-2xl p-6 shadow-2xl">
            <nav className="flex flex-col space-y-4">
              {isLoading ? (
                <div className="w-full h-10 bg-slate-800/50 rounded animate-pulse" />
              ) : isLoggedIn ? (
                <>
                  <div className="pb-4 border-b border-slate-700/50 mb-2">
                    <p className="text-sm text-slate-400">{locale === 'ko' ? '안녕하세요' : 'Hello'},</p>
                    <p className="text-lg font-black text-white">{user?.username}</p>
                  </div>
                  <a href="/mypage" onClick={closeMobileMenu} className="text-white font-bold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                    {t("myPage")}
                  </a>
                  <a href="/buy" onClick={closeMobileMenu} className="text-white font-bold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                    {t("buy")}
                  </a>
                  {user?.role === "admin" && (
                    <a href="/admin/dashboard" onClick={closeMobileMenu} className="text-yellow-500 font-bold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                      {t("admin")}
                    </a>
                  )}
                  <button
                    onClick={() => { closeMobileMenu(); handleLogout(); }}
                    className="text-red-400 font-bold py-3 px-4 rounded-xl hover:bg-red-500/10 transition-colors text-left"
                  >
                    {t("logout")}
                  </button>
                </>
              ) : (
                <>
                  <a href="/auth/login" onClick={closeMobileMenu} className="text-white font-bold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                    {t("login")}
                  </a>
                  <a href="/auth/signup" onClick={closeMobileMenu} className="text-white font-bold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                    {t("signup")}
                  </a>
                  <a href="/buy" onClick={closeMobileMenu} className="text-blue-400 font-bold py-3 px-4 rounded-xl hover:bg-blue-500/10 transition-colors">
                    {t("buy")}
                  </a>
                </>
              )}
            </nav>
          </div>
        </div>
      )}
    </>
  );
}
