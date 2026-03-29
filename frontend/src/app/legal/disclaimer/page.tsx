"use client";

import { useLanguage } from "@/lib/LanguageContext";
import Image from "next/image";

export default function DisclaimerPage() {
  const { locale } = useLanguage();
  const ko = locale === "ko";

  return (
    <div className="min-h-screen pt-28 pb-20 px-4">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* 책임약관 본문 */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-8 md:p-12 backdrop-blur-sm">
          <h1 className="text-3xl font-bold text-white mb-2">
            {ko ? "책임 약관" : "Liability Disclaimer"}
          </h1>
          <p className="text-sm text-cyan-400 font-medium mb-8 border-b border-slate-700/50 pb-6">
            {ko
              ? "본 문서는 JOY COIN 플랫폼의 운영 책임자 및 법적 책임 범위를 명시합니다."
              : "This document identifies the responsible party for the JOY COIN platform and defines the scope of legal liability."}
          </p>

          <div className="space-y-8 text-slate-300 text-sm leading-relaxed">

            {/* 운영 책임자 */}
            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                {ko ? "1. 운영 책임자" : "1. Responsible Party"}
              </h2>
              <p className="mb-4">
                {ko
                  ? "JOY COIN 플랫폼은 아래 명시된 책임자에 의해 운영됩니다. 본 플랫폼과 관련한 모든 법적 책임은 해당 책임자에게 귀속됩니다."
                  : "The JOY COIN platform is operated by the responsible party identified below. All legal responsibilities related to this platform are attributed to said party."}
              </p>
              <div className="p-5 rounded-xl bg-slate-800/60 border border-cyan-500/20 space-y-3">
                <div className="flex items-center gap-3">
                  <span className="text-cyan-400 text-xl">👤</span>
                  <div>
                    <p className="text-[10px] text-slate-400 uppercase font-black mb-0.5">{ko ? "책임자" : "Responsible Person"}</p>
                    <p className="text-white font-bold text-lg">SEUNGCHUL YOO</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-cyan-400 text-xl">🏢</span>
                  <div>
                    <p className="text-[10px] text-slate-400 uppercase font-black mb-0.5">{ko ? "운영 법인" : "Operating Entity"}</p>
                    <p className="text-white font-bold">JOY COIN</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-cyan-400 text-xl">📍</span>
                  <div>
                    <p className="text-[10px] text-slate-400 uppercase font-black mb-0.5">{ko ? "등록 주소" : "Registered Address"}</p>
                    <p className="text-white font-mono text-sm">30 N Gould St Ste R, Sheridan, WY 82801, USA</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-cyan-400 text-xl">🔢</span>
                  <div>
                    <p className="text-[10px] text-slate-400 uppercase font-black mb-0.5">EIN (Employer Identification Number)</p>
                    <p className="text-white font-mono font-bold">35-2900714</p>
                  </div>
                </div>
              </div>
            </section>

            {/* 책임자 운영 기관 */}
            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                {ko ? "2. 책임자 운영 기관" : "2. Organization Operated by Responsible Party"}
              </h2>
              <p className="mb-4">
                {ko
                  ? "위 책임자(SEUNGCHUL YOO)는 아래 기관의 대표로서 JOY COIN 플랫폼에 대한 전반적인 운영 책임을 집니다."
                  : "The above responsible party (SEUNGCHUL YOO), as the representative of the organization below, bears overall operational responsibility for the JOY COIN platform."}
              </p>
              <a
                href="https://www.spsi.solar/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-4 p-5 rounded-xl bg-slate-800/60 border border-slate-700/50 hover:border-cyan-500/40 hover:bg-slate-800 transition-all group"
              >
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-400/20 to-orange-500/20 border border-yellow-500/30 flex items-center justify-center flex-shrink-0">
                  <span className="text-2xl">☀️</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-white group-hover:text-cyan-400 transition-colors">SPSI Solar</p>
                  <p className="text-xs text-slate-400">www.spsi.solar</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {ko ? "책임자 SEUNGCHUL YOO 대표 운영 기관" : "Organization represented by SEUNGCHUL YOO"}
                  </p>
                </div>
                <svg className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 transition-colors flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </section>

            {/* 면책 조항 */}
            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                {ko ? "3. 플랫폼 성격 및 면책" : "3. Platform Nature & Disclaimer"}
              </h2>
              <p className="mb-3">
                {ko
                  ? "JOY COIN 플랫폼은 투자 상품, 증권, 금융 서비스를 제공하지 않습니다. 플랫폼 내 JOY 단위는 생태계 내부에서만 사용되는 참여 단위이며, 법정 통화 또는 금융 자산으로 간주되지 않습니다."
                  : "The JOY COIN platform does not provide investment products, securities, or financial services. JOY units within the platform are participation units used only within the ecosystem and are not considered legal tender or financial assets."}
              </p>
              <p>
                {ko
                  ? "플랫폼 이용 중 발생하는 손실, 데이터 손상, 서비스 중단 등에 대해 운영 책임자는 법률이 허용하는 최대 범위 내에서 책임의 한계를 가질 수 있습니다."
                  : "The responsible party may have limits of liability, to the fullest extent permitted by law, for any losses, data corruption, or service interruptions arising from the use of the platform."}
              </p>
            </section>

            {/* 준거법 */}
            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                {ko ? "4. 준거법 및 분쟁 해결" : "4. Governing Law & Dispute Resolution"}
              </h2>
              <p>
                {ko
                  ? "본 약관은 미국 와이오밍주 법률에 따라 해석되며, 관련 분쟁은 와이오밍주 관할 법원에서 해결합니다."
                  : "These terms shall be interpreted in accordance with the laws of the State of Wyoming, USA, and any related disputes shall be resolved in the courts of Wyoming."}
              </p>
            </section>

          </div>
        </div>

        {/* IRS EIN 증빙 문서 */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-8 md:p-12 backdrop-blur-sm">
          <h2 className="text-xl font-bold text-white mb-2">
            {ko ? "운영 책임자 법인 등록 증빙" : "Responsible Party — Legal Entity Registration"}
          </h2>
          <p className="text-sm text-slate-400 mb-6">
            {ko
              ? "아래는 책임자 SEUNGCHUL YOO 명의로 미국 국세청(IRS)에 등록된 JOY COIN의 공식 EIN 통지서입니다. 본 문서는 운영 책임자의 법적 실체를 증명합니다."
              : "Below is the official IRS EIN notice for JOY COIN, registered under the name of responsible party SEUNGCHUL YOO. This document certifies the legal identity of the responsible operator."}
          </p>
          <div className="rounded-xl overflow-hidden border border-slate-700/50">
            <Image
              src="/images/ein-notice.jpg"
              alt="IRS EIN Notice - JOY COIN, SEUNGCHUL YOO, EIN 35-2900714"
              width={900}
              height={1200}
              className="w-full h-auto"
              priority
            />
          </div>
        </div>

      </div>
    </div>
  );
}
