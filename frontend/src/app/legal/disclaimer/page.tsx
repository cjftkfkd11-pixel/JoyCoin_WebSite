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
              ? "본 문서는 JOY COIN 플랫폼 이용에 관한 책임 범위와 면책 조항을 명시합니다."
              : "This document specifies the scope of liability and disclaimer clauses relating to the use of the JOY COIN platform."}
          </p>

          <div className="space-y-8 text-slate-300 text-sm leading-relaxed">

            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                {ko ? "1. 법인 정보" : "1. Entity Information"}
              </h2>
              <p>
                {ko
                  ? "JOY COIN은 미국 와이오밍주에 등록된 법인으로, IRS로부터 EIN(Employer Identification Number)을 부여받은 합법적 사업체입니다."
                  : "JOY COIN is a legally registered entity in the state of Wyoming, USA, and has been assigned an Employer Identification Number (EIN) by the IRS."}
              </p>
              <div className="mt-3 p-4 rounded-xl bg-slate-800/60 border border-slate-700/50 text-xs space-y-1 font-mono">
                <p><span className="text-slate-400">{ko ? "법인명" : "Entity Name"}:</span> <span className="text-white">JOY COIN</span></p>
                <p><span className="text-slate-400">EIN:</span> <span className="text-white">35-2900714</span></p>
                <p><span className="text-slate-400">{ko ? "등록 주소" : "Registered Address"}:</span> <span className="text-white">30 N Gould St Ste R, Sheridan, WY 82801</span></p>
                <p><span className="text-slate-400">{ko ? "등록일" : "Notice Date"}:</span> <span className="text-white">06-04-2025</span></p>
              </div>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                {ko ? "2. 플랫폼 성격 및 면책" : "2. Platform Nature & Disclaimer"}
              </h2>
              <p className="mb-3">
                {ko
                  ? "JOY COIN 플랫폼은 투자 상품, 증권, 금융 서비스를 제공하지 않습니다. 플랫폼 내 JOY 단위는 생태계 내부에서만 사용되는 참여 단위이며, 법정 통화 또는 금융 자산으로 간주되지 않습니다."
                  : "The JOY COIN platform does not provide investment products, securities, or financial services. JOY units within the platform are participation units used only within the ecosystem and are not considered legal tender or financial assets."}
              </p>
              <p>
                {ko
                  ? "플랫폼 이용 중 발생하는 손실, 데이터 손상, 서비스 중단 등에 대해 JOY COIN은 법률이 허용하는 최대 범위 내에서 책임을 지지 않습니다."
                  : "JOY COIN shall not be liable, to the fullest extent permitted by law, for any losses, data corruption, or service interruptions arising from the use of the platform."}
              </p>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                {ko ? "3. 이용자 책임" : "3. User Responsibility"}
              </h2>
              <p className="mb-3">
                {ko
                  ? "이용자는 플랫폼 이용 전 관련 약관 및 위험 고지 내용을 충분히 숙지해야 하며, 자신의 판단과 책임 하에 서비스를 이용합니다."
                  : "Users must thoroughly review the relevant terms and risk disclosures before using the platform and use the service at their own judgment and responsibility."}
              </p>
              <p>
                {ko
                  ? "이용자가 제공한 지갑 주소, 개인 정보 등의 오류로 인해 발생한 손해는 이용자 본인이 책임집니다."
                  : "Users are solely responsible for any damages arising from errors in wallet addresses, personal information, or other information provided by the user."}
              </p>
            </section>

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

        {/* 법인 등록증 (EIN 통지서) */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-8 md:p-12 backdrop-blur-sm">
          <h2 className="text-xl font-bold text-white mb-2">
            {ko ? "법인 등록 확인서 (IRS EIN 통지서)" : "Entity Registration Certificate (IRS EIN Notice)"}
          </h2>
          <p className="text-sm text-slate-400 mb-6">
            {ko
              ? "아래는 미국 국세청(IRS)으로부터 발급받은 고용주 식별 번호(EIN) 공식 통지서입니다."
              : "The following is the official Employer Identification Number (EIN) notice issued by the U.S. Internal Revenue Service (IRS)."}
          </p>
          <div className="rounded-xl overflow-hidden border border-slate-700/50">
            <Image
              src="/images/ein-notice.jpg"
              alt="IRS EIN Notice - JOY COIN EIN 35-2900714"
              width={900}
              height={1200}
              className="w-full h-auto"
              priority
            />
          </div>
        </div>

        {/* SPSI Solar 파트너 링크 */}
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-8 md:p-12 backdrop-blur-sm">
          <h2 className="text-xl font-bold text-white mb-2">
            {ko ? "관련 파트너 정보" : "Partner Information"}
          </h2>
          <p className="text-sm text-slate-400 mb-6">
            {ko
              ? "JOY COIN은 아래 파트너사와 협력 관계에 있습니다. 파트너사의 공식 웹사이트에서 추가 정보를 확인하실 수 있습니다."
              : "JOY COIN is in partnership with the following partner. You can find additional information on the partner's official website."}
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
              <p className="text-xs text-slate-400 truncate">https://www.spsi.solar/</p>
            </div>
            <svg className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 transition-colors flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>

      </div>
    </div>
  );
}
