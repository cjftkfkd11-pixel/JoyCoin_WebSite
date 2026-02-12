"use client";

import { useState, useEffect } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAuth } from "@/lib/AuthContext";
import { getApiBaseUrl } from "@/lib/apiBase";

export default function Header() {
  const { locale, setLocale, t } = useLanguage();
  const { user, isLoggedIn, isLoading, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);

  const API_BASE_URL = getApiBaseUrl();

  // 알림 로드
  useEffect(() => {
    if (!isLoggedIn) return;
    const fetchNotifications = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/deposits/my`, { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          const items = data.items || data;
          const seenNotifs = JSON.parse(localStorage.getItem('seenNotifications') || '[]');
          const newNotifs = items.filter((dep: any) =>
            (dep.status === 'approved' || dep.status === 'rejected') &&
            !seenNotifs.includes(dep.id)
          );
          setNotifications(newNotifs);
        }
      } catch {}
    };
    fetchNotifications();
  }, [isLoggedIn]);

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

  const clearNotifications = () => {
    const seenNotifs = JSON.parse(localStorage.getItem('seenNotifications') || '[]');
    const newSeen = [...seenNotifs, ...notifications.map((n: any) => n.id)];
    localStorage.setItem('seenNotifications', JSON.stringify(newSeen));
    setNotifications([]);
    setShowNotifDropdown(false);
  };

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-[60] px-4 md:px-10 py-4 flex justify-between items-center bg-[#020617]/95 backdrop-blur-md border-b border-slate-800/50" style={{ WebkitTransform: 'translateZ(0)', transform: 'translateZ(0)' }}>
        <div className="flex items-center space-x-4">
          <a href="/" className="text-2xl md:text-3xl font-black tracking-tighter text-blue-500 cursor-pointer drop-shadow-lg">
            JOYCOIN
          </a>
        </div>

        <div className="flex items-center space-x-3">
          {/* Language Toggle */}
          <button
            type="button"
            onClick={toggleLocale}
            className="bg-slate-800/50 text-slate-300 px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-700/50 hover:bg-slate-700/50 transition-all"
          >
            {locale === "en" ? "한국어" : "ENG"}
          </button>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center space-x-5 text-sm font-semibold text-white/90">
            {isLoading ? (
              <div className="w-32 h-6 bg-slate-800/50 rounded animate-pulse" />
            ) : isLoggedIn ? (
              <>
                <a href="/mypage" className="hover:text-blue-400 transition-colors">{t("myPage")}</a>
                <a href="/buy" className="hover:text-blue-400 transition-colors">{t("buy")}</a>
                {user?.role === "admin" && (
                  <a href="/admin/dashboard" className="hover:text-yellow-400 transition-colors text-yellow-500">{t("admin")}</a>
                )}
              </>
            ) : (
              <>
                <a href="/auth/signup" className="hover:text-blue-400 transition-colors">{t("signup")}</a>
                <a href="/auth/login" className="hover:text-blue-400 transition-colors">{t("login")}</a>
                <a href="/buy" className="hover:text-blue-400 transition-colors">{t("buy")}</a>
              </>
            )}
          </nav>

          {/* Notification Bell (로그인 시에만) */}
          {isLoggedIn && (
            <div className="relative hidden lg:block">
              <button
                type="button"
                onClick={() => setShowNotifDropdown(!showNotifDropdown)}
                className="relative p-2 text-slate-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                {notifications.length > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center">
                    {notifications.length > 9 ? '9+' : notifications.length}
                  </span>
                )}
              </button>

              {/* Notification Dropdown */}
              {showNotifDropdown && (
                <div className="absolute right-0 top-10 w-80 bg-slate-900/95 border border-slate-700/50 rounded-xl shadow-2xl p-4 z-50">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="text-sm font-bold text-white">{locale === 'ko' ? '알림' : 'Notifications'}</h3>
                    {notifications.length > 0 && (
                      <button onClick={clearNotifications} className="text-[10px] text-blue-400 hover:text-blue-300">
                        {locale === 'ko' ? '모두 읽음' : 'Mark all read'}
                      </button>
                    )}
                  </div>
                  {notifications.length > 0 ? (
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {notifications.map((notif) => (
                        <div key={notif.id} className={`p-3 rounded-lg text-xs ${notif.status === 'approved' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                          <span className="font-bold">{notif.status === 'approved' ? '✅ ' : '❌ '}</span>
                          {notif.expected_amount} USDT → {(notif.joy_amount || 0).toLocaleString()} JOY
                          <span className="ml-2">{notif.status === 'approved' ? (locale === 'ko' ? '승인됨' : 'Approved') : (locale === 'ko' ? '거절됨' : 'Rejected')}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-500 text-xs text-center py-4">{locale === 'ko' ? '새 알림이 없습니다' : 'No new notifications'}</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Desktop User Actions */}
          <div className="hidden lg:flex items-center">
            {isLoading ? (
              <div className="w-20 h-10 bg-slate-800/50 rounded-2xl animate-pulse" />
            ) : isLoggedIn ? (
              <div className="flex items-center space-x-3">
                <span className="text-sm font-semibold text-slate-400">{user?.username}</span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="bg-red-500/20 text-red-400 px-4 py-2 rounded-2xl border border-red-500/30 hover:bg-red-500/30 transition-all active:scale-95 font-semibold text-sm"
                >
                  {t("logout")}
                </button>
              </div>
            ) : null}
          </div>

          {/* Mobile Hamburger Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden flex flex-col justify-center items-center w-10 h-10 bg-slate-800/50 rounded-xl border border-slate-700/50"
          >
            <span className={`block w-5 h-0.5 bg-white transition-all duration-300 ${mobileMenuOpen ? 'rotate-45 translate-y-1' : ''}`} />
            <span className={`block w-5 h-0.5 bg-white my-1 transition-all duration-300 ${mobileMenuOpen ? 'opacity-0' : ''}`} />
            <span className={`block w-5 h-0.5 bg-white transition-all duration-300 ${mobileMenuOpen ? '-rotate-45 -translate-y-1' : ''}`} />
          </button>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-[55] lg:hidden">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={closeMobileMenu} />
          <div className="absolute top-20 left-4 right-4 bg-slate-900/95 border border-slate-700/50 rounded-2xl p-6 shadow-2xl">
            <nav className="flex flex-col space-y-3">
              {isLoading ? (
                <div className="w-full h-10 bg-slate-800/50 rounded animate-pulse" />
              ) : isLoggedIn ? (
                <>
                  <div className="pb-4 border-b border-slate-700/50 mb-2">
                    <p className="text-sm text-slate-400">{locale === 'ko' ? '안녕하세요' : 'Hello'},</p>
                    <p className="text-lg font-bold text-white">{user?.username}</p>
                    {notifications.length > 0 && (
                      <p className="text-xs text-red-400 mt-1">🔔 {notifications.length}{locale === 'ko' ? '개의 새 알림' : ' new notifications'}</p>
                    )}
                  </div>
                  <a href="/mypage" onClick={closeMobileMenu} className="text-white font-semibold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                    {t("myPage")}
                  </a>
                  <a href="/buy" onClick={closeMobileMenu} className="text-white font-semibold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                    {t("buy")}
                  </a>
                  {user?.role === "admin" && (
                    <a href="/admin/dashboard" onClick={closeMobileMenu} className="text-yellow-500 font-semibold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                      {t("admin")}
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={() => { closeMobileMenu(); handleLogout(); }}
                    className="text-red-400 font-semibold py-3 px-4 rounded-xl hover:bg-red-500/10 transition-colors text-left"
                  >
                    {t("logout")}
                  </button>
                </>
              ) : (
                <>
                  <a href="/auth/login" onClick={closeMobileMenu} className="text-white font-semibold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                    {t("login")}
                  </a>
                  <a href="/auth/signup" onClick={closeMobileMenu} className="text-white font-semibold py-3 px-4 rounded-xl hover:bg-slate-800/50 transition-colors">
                    {t("signup")}
                  </a>
                  <a href="/buy" onClick={closeMobileMenu} className="text-blue-400 font-semibold py-3 px-4 rounded-xl hover:bg-blue-500/10 transition-colors">
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
