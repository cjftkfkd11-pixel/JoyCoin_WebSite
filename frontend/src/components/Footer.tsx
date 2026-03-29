"use client";

import Link from "next/link";
import { useLanguage } from "@/lib/LanguageContext";

export default function Footer() {
  const { t } = useLanguage();

  return (
    <footer className="py-6 sm:py-10 text-center z-10 space-y-3 sm:space-y-4 px-4">
      <p className="text-slate-600 text-[10px] sm:text-xs font-bold uppercase tracking-[0.2em] sm:tracking-[0.3em]">
        {t("footer")}
      </p>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-1.5 sm:gap-1 text-xs sm:text-[11px] text-slate-600">
        <span className="font-semibold text-slate-500">Legal</span>
        <span className="hidden sm:inline mx-1">—</span>
        <div className="flex items-center gap-2 sm:gap-1 flex-wrap justify-center">
          <Link href="/legal/terms" className="hover:text-cyan-400 transition-colors py-1">Terms of Use</Link>
          <span>·</span>
          <Link href="/legal/risk" className="hover:text-cyan-400 transition-colors py-1">Risk Disclosure</Link>
          <span>·</span>
          <Link href="/legal/privacy" className="hover:text-cyan-400 transition-colors py-1">Privacy Policy</Link>
          <span>·</span>
          <Link href="/legal/token" className="hover:text-cyan-400 transition-colors py-1">Token Nature</Link>
          <span>·</span>
          <Link href="/legal/disclaimer" className="hover:text-cyan-400 transition-colors py-1">Disclaimer</Link>
        </div>
      </div>
    </footer>
  );
}
