"use client";
import { useState, useEffect, useRef, useCallback } from "react";

type Lang = "en" | "ko";

const TABS = [
  { key: "terms", en: "Terms of Use", ko: "이용약관" },
  { key: "risk", en: "Risk Disclosure", ko: "위험 고지" },
  { key: "token", en: "Token Nature", ko: "토큰 성격" },
  { key: "privacy", en: "Privacy Policy", ko: "개인정보 처리방침" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

/* ══════════════════════════════════════════════════
   CONTENT COMPONENTS (bilingual)
   ══════════════════════════════════════════════════ */

function TermsContent({ lang }: { lang: Lang }) {
  if (lang === "ko") return (
    <div className="space-y-6">
      <Section title="1. 플랫폼 정의">
        <p>JOYCOIN은 자체 생태계 내에서 사용되는 내부 참여 단위(&quot;JOY&quot;)를 배정하는 디지털 플랫폼입니다.</p>
        <p className="mt-2">JOY는 다음에 해당하지 않습니다:</p>
        <BulletList items={["증권", "지분", "소유권", "금융 상품", "투자 계약"]} />
        <p className="mt-2">본 플랫폼은 서비스 시스템으로 운영되며, 금융 기관, 중개업체 또는 거래소로 운영되지 않습니다.</p>
      </Section>
      <Section title="2. 비투자 성격 인정">
        <p>사용자는 다음 사항을 인정하고 동의합니다:</p>
        <BulletList items={["JOY는 투자 상품이 아닙니다", "JOY는 재정적 수익을 위해 제공되지 않습니다", "회사는 가치, 유동성 또는 가치 상승을 보장하지 않습니다"]} />
        <p className="mt-2">플랫폼 참여는 자발적이며 서비스 이용 목적으로만 이루어집니다.</p>
      </Section>
      <Section title="3. 참여 및 배정 메커니즘">
        <p>사용자는 플랫폼 참여를 통해 JOY 배정을 요청할 수 있습니다. USDT를 포함한 디지털 자산 전송은 구매 계약이나 투자 거래가 아닌 참여 요청으로 처리됩니다.</p>
        <p className="mt-2">JOY는 관리자 확인 후에만 배정됩니다. 회사는 재량에 따라 배정 요청을 승인, 거절, 지연 또는 검토할 수 있습니다.</p>
      </Section>
      <Section title="4. 디지털 자산 전송 책임">
        <p>사용자는 블록체인 거래가 되돌릴 수 없으며, 지갑 주소의 정확성은 사용자 책임이고, 회사는 블록체인 네트워크를 통제하지 않으며, 거래 확인은 제3자 인프라에 의존한다는 점을 인정합니다.</p>
        <p className="mt-2">회사는 잘못된 전송, 네트워크 장애 또는 사용자 오류로 인한 자산 손실에 대해 책임지지 않습니다.</p>
      </Section>
      <Section title="5. 추천 프로그램">
        <p>추천 시스템은 참여 기반 활동 기능입니다. 이는 수입 보장, 투자 인센티브, 이익 분배 프로그램 또는 재정 배분 권리를 구성하지 않습니다.</p>
        <p className="mt-2">추천 비율은 사전 통지 없이 언제든지 수정, 중단 또는 종료될 수 있습니다.</p>
      </Section>
      <Section title="6. 섹터 구조">
        <p>섹터 배정 및 섹터 기여 모델은 운영 관리 구조입니다. 이는 소유권, 지분 참여, 수익 권리 또는 파트너십 약정을 나타내지 않습니다.</p>
      </Section>
      <Section title="7. 거래소 또는 중개 서비스 없음">
        <p>JOYCOIN은 암호화폐 거래소를 운영하지 않으며, 중개 서비스를 제공하지 않고, 외부 거래를 촉진하지 않으며, 토큰 유동성을 보장하지 않습니다. 제3자 거래 활동은 회사의 책임 범위 밖입니다.</p>
      </Section>
      <Section title="8. 위험 고지">
        <p>사용자는 규제 불확실성, 디지털 자산 변동성, 기술적 장애, 블록체인 네트워크 지연, 시스템 다운타임을 포함한 디지털 참여와 관련된 위험을 인정합니다. 참여는 자발적이며 사용자의 단독 위험 하에 이루어집니다.</p>
      </Section>
      <Section title="9. 사용자 책임">
        <p>사용자는 현지 법률 준수, 세금 의무, 지갑 보안, 디지털 자산 관리 및 개인 계정 보호에 대해 전적으로 책임집니다. 회사는 사용자의 과실이나 결정에 대해 책임지지 않습니다.</p>
      </Section>
      <Section title="10. 책임 제한">
        <p>회사는 토큰 가치 변동, 추천 구조 변경, 섹터 정책 조정, 제3자 지갑 문제, 블록체인 장애 또는 외부 거래소 활동에 대해 책임지지 않습니다.</p>
      </Section>
      <Section title="11. 서비스 수정">
        <p>회사는 언제든지 사전 통지 없이 JOY 구조 수정, 배정 로직 조정, 추천 프로그램 중단, 섹터 설정 변경 또는 참여 패키지 중단을 할 수 있습니다.</p>
      </Section>
      <Section title="12. 접근 제한">
        <p>회사는 불법 활동 의심, 플랫폼 오용, 시스템 남용 감지 또는 규정 준수 위험 발생 시 접근을 중단하거나 종료할 수 있습니다.</p>
      </Section>
      <Section title="13. 규정 준수 및 법적 책임">
        <p>사용자는 해당 관할권 내 디지털 자산에 관한 모든 적용 가능한 법률을 준수해야 합니다. 회사는 사용자의 규제 위반, 불법 참여 또는 디지털 자산 오용에 대해 책임지지 않습니다.</p>
      </Section>
      <Section title="14. 준거법">
        <p>본 플랫폼은 미국 등록 법인이 운영합니다. 모든 분쟁은 적용 가능한 미국 법률 및 관련 관할권에 의해 규율됩니다.</p>
      </Section>
      <Section title="15. 법적 인정">
        <p>플랫폼에 접근함으로써 사용자는 JOY가 투자가 아님을 이해하고, 참여가 자발적이며, 이익 기대가 없고, 모든 위험을 인정하며, 본 약관을 완전히 수락함을 확인합니다.</p>
        <p className="mt-2">플랫폼의 접근 및 지속적인 사용은 본 계약의 수락을 구성합니다.</p>
      </Section>
    </div>
  );
  return (
    <div className="space-y-6">
      <Section title="1. Platform Definition">
        <p>JOYCOIN is a digital platform that allocates internal participation units (&quot;JOY&quot;) for use within its ecosystem.</p>
        <p className="mt-2">JOY does not represent:</p>
        <BulletList items={["securities","equity","ownership","financial instruments","investment contracts"]} />
        <p className="mt-2">The platform operates as a service system and not as a financial institution, brokerage, or exchange.</p>
      </Section>
      <Section title="2. Acknowledgement of Non-Investment Nature">
        <p>Users acknowledge and agree that:</p>
        <BulletList items={["JOY is not an investment product","JOY is not offered for financial return","the Company does not guarantee value, liquidity, or appreciation"]} />
        <p className="mt-2">Participation in the platform is voluntary and for service use only.</p>
      </Section>
      <Section title="3. Participation & Allocation Mechanism">
        <p>Users may request JOY allocation through platform participation. Digital asset transfers (including USDT) are processed as participation requests, not purchase agreements or investment transactions.</p>
        <p className="mt-2">JOY is allocated only after administrative verification. The Company reserves the right to approve, reject, delay, or review any allocation request at its discretion.</p>
      </Section>
      <Section title="4. Digital Asset Transfer Responsibility">
        <p>Users acknowledge blockchain transactions are irreversible, wallet accuracy is user responsibility, the Company does not control blockchain networks, and transaction confirmation depends on third-party infrastructure.</p>
        <p className="mt-2">The Company is not liable for incorrect transfers, network failures, or lost assets due to user error.</p>
      </Section>
      <Section title="5. Referral Program">
        <p>The referral system is a participation-based engagement feature. It does not constitute income guarantee, investment incentive, profit-sharing program, or financial distribution right.</p>
        <p className="mt-2">Referral ratios may be modified, suspended, or discontinued at any time without notice.</p>
      </Section>
      <Section title="6. Sector Structure">
        <p>Sector assignments and sector contribution models are operational management structures. They do not represent ownership, equity participation, revenue rights, or partnership arrangements.</p>
      </Section>
      <Section title="7. No Exchange or Brokerage Services">
        <p>JOYCOIN does not operate a cryptocurrency exchange, provide brokerage services, facilitate external trading, or guarantee token liquidity. Any third-party trading activity is outside the Company&apos;s responsibility.</p>
      </Section>
      <Section title="8. Risk Disclosure">
        <p>Users acknowledge risks associated with digital participation, including regulatory uncertainty, digital asset volatility, technical failures, blockchain network delays, and system downtime. Participation is voluntary and undertaken at the user&apos;s sole risk.</p>
      </Section>
      <Section title="9. User Responsibility">
        <p>Users are solely responsible for compliance with local laws, tax obligations, wallet security, digital asset management, and personal account protection. The Company shall not be liable for user negligence or decisions.</p>
      </Section>
      <Section title="10. Limitation of Liability">
        <p>The Company is not responsible for token value changes, referral structure changes, sector policy adjustments, third-party wallet issues, blockchain failures, or external exchange activity.</p>
      </Section>
      <Section title="11. Service Modification">
        <p>The Company may at any time modify JOY structure, adjust allocation logic, suspend referral programs, change sector settings, or discontinue participation packages without prior notice.</p>
      </Section>
      <Section title="12. Access Restriction">
        <p>The Company may suspend or terminate access if illegal activity is suspected, misuse of the platform occurs, system abuse is detected, or compliance risks arise.</p>
      </Section>
      <Section title="13. Compliance & Legal Responsibility">
        <p>Users must comply with all applicable laws regarding digital assets within their jurisdiction. The Company is not responsible for regulatory violations by users, unlawful participation, or misuse of digital assets.</p>
      </Section>
      <Section title="14. Governing Law">
        <p>This platform is operated by a U.S.-registered entity. All disputes shall be governed by applicable U.S. law and relevant jurisdiction.</p>
      </Section>
      <Section title="15. Legal Acknowledgement">
        <p>By accessing the platform, users confirm that they understand JOY is not an investment, participation is voluntary, no profit expectation exists, all risks are acknowledged, and they accept these Terms fully.</p>
        <p className="mt-2">Access and continued use of the platform constitutes acceptance of this agreement.</p>
      </Section>
    </div>
  );
}

function RiskContent({ lang }: { lang: Lang }) {
  if (lang === "ko") return (
    <div className="space-y-6">
      <p>JOYCOIN 플랫폼 참여에는 디지털 자산 관련 상호작용이 포함되며 내재적 위험이 수반됩니다. 사용자는 다음을 인정하고 수락합니다:</p>
      <Section title="1. 규제 위험">
        <p>디지털 자산 규제는 언제든지 변경될 수 있으며, 플랫폼 운영이나 가용성에 영향을 미칠 수 있습니다.</p>
      </Section>
      <Section title="2. 변동성 위험">
        <p>디지털 참여 단위 및 관련 자산은 인식된 가치나 효용이 변동할 수 있습니다.</p>
      </Section>
      <Section title="3. 기술적 위험">
        <p>플랫폼은 다운타임, 시스템 오류, 스마트 계약 문제 및 블록체인 네트워크 지연을 경험할 수 있습니다.</p>
      </Section>
      <Section title="4. 전송 위험">
        <p>디지털 자산 전송은 되돌릴 수 없습니다. 잘못된 지갑 주소는 영구적인 손실을 초래할 수 있습니다.</p>
      </Section>
      <Section title="5. 추천 및 배정 변경">
        <p>추천 비율, 배정 모델 및 섹터 구조는 언제든지 변경될 수 있습니다.</p>
      </Section>
      <Section title="6. 보장 없음">
        <p>회사는 배정, 가치 유지, 유동성 또는 서비스 지속성을 보장하지 않습니다.</p>
        <p className="mt-3 text-yellow-400 font-semibold">참여는 자발적이며 사용자의 단독 위험 하에 이루어집니다.</p>
      </Section>
    </div>
  );
  return (
    <div className="space-y-6">
      <p>Participation in the JOYCOIN platform involves digital asset interactions and carries inherent risks. Users acknowledge and accept the following:</p>
      <Section title="1. Regulatory Risk">
        <p>Digital asset regulations may change at any time and may affect platform operation or availability.</p>
      </Section>
      <Section title="2. Volatility Risk">
        <p>Digital participation units and related assets may fluctuate in perceived value or utility.</p>
      </Section>
      <Section title="3. Technical Risk">
        <p>The platform may experience downtime, system errors, smart contract issues, and blockchain network delays.</p>
      </Section>
      <Section title="4. Transfer Risk">
        <p>Digital asset transfers are irreversible. Incorrect wallet addresses may result in permanent loss.</p>
      </Section>
      <Section title="5. Referral & Allocation Changes">
        <p>Referral ratios, allocation models, and sector structures may change at any time.</p>
      </Section>
      <Section title="6. No Guarantee">
        <p>The Company does not guarantee allocation, value retention, liquidity, or continuity of service.</p>
        <p className="mt-3 text-yellow-400 font-semibold">Participation is voluntary and at the user&apos;s sole risk.</p>
      </Section>
    </div>
  );
}

function TokenContent({ lang }: { lang: Lang }) {
  if (lang === "ko") return (
    <div className="space-y-6">
      <p>JOY는 플랫폼 생태계 내에서 사용하도록 설계된 디지털 참여 단위입니다.</p>
      <div>
        <p className="font-semibold text-white mb-2">JOY는 다음에 해당하지 않습니다:</p>
        <BulletList items={["투자 상품", "증권", "소유권", "이익 배당권", "지분 참여"]} />
      </div>
      <p className="text-yellow-400 font-semibold">JOY는 내부 접근 및 참여 메커니즘으로만 기능합니다.</p>
      <div>
        <p className="font-semibold text-white mb-2">플랫폼은 다음을 보장하지 않습니다:</p>
        <BulletList items={["재판매 가치", "유동성", "가격 상승"]} />
      </div>
      <p>외부 거래가 있는 경우, 이는 회사와 독립적입니다.</p>
      <p className="text-yellow-400 font-semibold">사용자는 JOY가 투자 목적으로 구매되지 않음을 인정합니다.</p>
    </div>
  );
  return (
    <div className="space-y-6">
      <p>JOY is a digital participation unit designed for use within the platform ecosystem.</p>
      <div>
        <p className="font-semibold text-white mb-2">JOY does NOT represent:</p>
        <BulletList items={["investment instruments","securities","ownership rights","profit entitlement","equity participation"]} />
      </div>
      <p className="text-yellow-400 font-semibold">JOY functions solely as an internal access and participation mechanism.</p>
      <div>
        <p className="font-semibold text-white mb-2">The platform does not guarantee:</p>
        <BulletList items={["resale value","liquidity","price appreciation"]} />
      </div>
      <p>External trading, if any, is independent of the Company.</p>
      <p className="text-yellow-400 font-semibold">Users acknowledge JOY is not purchased for investment purposes.</p>
    </div>
  );
}

function PrivacyContent({ lang }: { lang: Lang }) {
  if (lang === "ko") return (
    <div className="space-y-6">
      <Section title="수집 정보">
        <p>플랫폼은 다음을 수집할 수 있습니다:</p>
        <BulletList items={["이메일 주소", "IP 주소", "로그인 기록", "지갑 주소", "거래 기록"]} />
      </Section>
      <Section title="사용 목적">
        <p>데이터는 다음 목적으로 사용됩니다:</p>
        <BulletList items={["계정 인증", "서비스 배정", "사기 방지", "운영 분석"]} />
      </Section>
      <Section title="데이터 저장">
        <p>사용자 데이터는 보안 서버에 저장되며 운영 및 규정 준수 목적으로 보관될 수 있습니다.</p>
      </Section>
      <Section title="제3자 서비스">
        <p>플랫폼은 블록체인 API, 분석 도구 및 보안 서비스를 사용할 수 있습니다. 이러한 제공업체는 제한된 기술 데이터를 처리할 수 있습니다.</p>
      </Section>
      <Section title="사용자 책임">
        <p>사용자는 자격 증명, 지갑 접근 및 기기 보안을 보호해야 합니다.</p>
      </Section>
      <Section title="정책 업데이트">
        <p>본 정책은 사전 통지 없이 업데이트될 수 있습니다. 플랫폼의 지속적인 사용은 수락을 구성합니다.</p>
      </Section>
    </div>
  );
  return (
    <div className="space-y-6">
      <Section title="Data Collection">
        <p>The platform may collect:</p>
        <BulletList items={["email address","IP address","login records","wallet address","transaction logs"]} />
      </Section>
      <Section title="Purpose of Use">
        <p>Data is used for:</p>
        <BulletList items={["account authentication","service allocation","fraud prevention","operational analytics"]} />
      </Section>
      <Section title="Data Storage">
        <p>User data may be stored on secure servers and retained for operational and compliance purposes.</p>
      </Section>
      <Section title="Third-Party Services">
        <p>The platform may use blockchain APIs, analytics tools, and security services. These providers may process limited technical data.</p>
      </Section>
      <Section title="User Responsibility">
        <p>Users must protect their credentials, wallet access, and device security.</p>
      </Section>
      <Section title="Policy Updates">
        <p>This policy may be updated without prior notice. Continued platform use constitutes acceptance.</p>
      </Section>
    </div>
  );
}

/* ── Helpers ── */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-white mb-2">{title}</h3>
      <div className="text-slate-400 text-xs leading-relaxed">{children}</div>
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc list-inside space-y-0.5 ml-3 mt-1">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

const TAB_CONTENT: Record<TabKey, React.FC<{ lang: Lang }>> = {
  terms: TermsContent,
  risk: RiskContent,
  token: TokenContent,
  privacy: PrivacyContent,
};

/* ── i18n texts ── */
const UI_TEXT = {
  en: {
    title: "Legal Acknowledgement Required",
    subtitle: "Before accessing the JOYCOIN platform, please review and acknowledge the following:",
    howTo: "How to proceed: Read all 4 tabs by scrolling to the bottom of each one. Once all tabs are read, the checkboxes below will be enabled.",
    scrollHint: "Scroll to the bottom to continue",
    scrollAllHint: "Please scroll through all four documents to enable the checkboxes below.",
    progress: (done: number) => `${done}/4 documents read`,
    check1: "I confirm JOY is not an investment product",
    check2: "I acknowledge digital asset participation risks",
    check3: "I agree to the Terms of Use",
    check4: "I accept the Privacy Policy",
    enter: "ENTER PLATFORM",
    disclaimer: "This platform provides digital participation services and does not offer financial, investment, or securities products.",
  },
  ko: {
    title: "법적 고지 확인 필요",
    subtitle: "JOYCOIN 플랫폼에 접근하기 전에 아래 내용을 검토하고 동의해 주세요:",
    howTo: "진행 방법: 아래 4개 탭을 각각 끝까지 스크롤하여 읽어주세요. 4개 탭을 모두 읽으면 체크박스가 활성화됩니다.",
    scrollHint: "계속하려면 아래로 스크롤하세요",
    scrollAllHint: "4개 문서를 모두 끝까지 읽어야 체크박스가 활성화됩니다.",
    progress: (done: number) => `${done}/4 문서 읽음`,
    check1: "JOY가 투자 상품이 아님을 확인합니다",
    check2: "디지털 자산 참여 위험을 인정합니다",
    check3: "이용약관에 동의합니다",
    check4: "개인정보 처리방침에 동의합니다",
    enter: "플랫폼 입장",
    disclaimer: "본 플랫폼은 디지털 참여 서비스를 제공하며, 금융, 투자 또는 증권 상품을 제공하지 않습니다.",
  },
};

/* ══════════════════════════════════════════════════
   ENTRY GATE COMPONENT
   ══════════════════════════════════════════════════ */
export default function EntryGate({ children }: { children: React.ReactNode }) {
  const [agreed, setAgreed] = useState<boolean | null>(null);
  const [lang, setLang] = useState<Lang>("en");
  const [activeTab, setActiveTab] = useState<TabKey>("terms");
  const [scrolledTabs, setScrolledTabs] = useState<Record<TabKey, boolean>>({
    terms: false,
    risk: false,
    token: false,
    privacy: false,
  });
  const [checks, setChecks] = useState({
    notInvestment: false,
    risks: false,
    terms: false,
    privacy: false,
  });

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setAgreed(localStorage.getItem("legal_agreed") === "true");
    // Detect browser language for default
    const browserLang = navigator.language?.toLowerCase() || "";
    if (browserLang.startsWith("ko")) {
      setLang("ko");
    }
  }, []);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 30;
    if (atBottom && !scrolledTabs[activeTab]) {
      setScrolledTabs((prev) => ({ ...prev, [activeTab]: true }));
    }
  }, [activeTab, scrolledTabs]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [activeTab]);

  const scrolledCount = TABS.filter((tab) => scrolledTabs[tab.key]).length;
  const allScrolled = scrolledCount === 4;
  const allChecked = checks.notInvestment && checks.risks && checks.terms && checks.privacy;

  const handleEnter = () => {
    localStorage.setItem("legal_agreed", "true");
    setAgreed(true);
  };

  if (agreed === null) {
    return (
      <div className="fixed inset-0 bg-black z-[9999] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (agreed) return <>{children}</>;

  const t = UI_TEXT[lang];
  const ContentComponent = TAB_CONTENT[activeTab];

  return (
    <div className="fixed inset-0 bg-black z-[9999] flex items-center justify-center p-2 sm:p-4 overflow-auto">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-700/50 rounded-xl sm:rounded-2xl shadow-2xl flex flex-col max-h-[98vh] sm:max-h-[95vh]">
        {/* Header + Language Toggle */}
        <div className="p-3 sm:p-6 pb-2 sm:pb-4 border-b border-slate-700/50 flex-shrink-0">
          {/* Language Toggle */}
          <div className="flex justify-center mb-2 sm:mb-3">
            <div className="flex bg-slate-800 rounded-lg p-0.5 text-[10px] sm:text-xs font-bold">
              <button
                onClick={() => setLang("ko")}
                className={`px-3 py-1.5 rounded-md transition-all ${
                  lang === "ko" ? "bg-cyan-500 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                한국어
              </button>
              <button
                onClick={() => setLang("en")}
                className={`px-3 py-1.5 rounded-md transition-all ${
                  lang === "en" ? "bg-cyan-500 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                English
              </button>
            </div>
          </div>

          <h1 className="text-base sm:text-xl font-bold text-white text-center">{t.title}</h1>
          <p className="text-[10px] sm:text-xs text-slate-400 text-center mt-1 sm:mt-2 leading-relaxed">
            {t.subtitle}
          </p>

          {/* How-to instruction banner */}
          <div className="mt-2 sm:mt-3 p-2 sm:p-3 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
            <p className="text-[10px] sm:text-xs text-cyan-400 text-center font-medium leading-relaxed">
              {t.howTo}
            </p>
            <p className="text-[10px] text-cyan-300/60 text-center mt-1 font-bold">
              {t.progress(scrolledCount)}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700/50 flex-shrink-0">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 min-w-0 py-2 sm:py-3 text-[9px] sm:text-xs font-medium transition-colors relative px-1 ${
                activeTab === tab.key
                  ? "text-cyan-400 bg-slate-800/50"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {tab[lang]}
              {scrolledTabs[tab.key] && (
                <span className="absolute top-0.5 right-0.5 text-green-400 text-[8px] sm:text-[10px]">&#10003;</span>
              )}
              {activeTab === tab.key && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400" />
              )}
            </button>
          ))}
        </div>

        {/* Scrollable content */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-3 sm:p-6 min-h-0"
          style={{ maxHeight: "45vh" }}
        >
          <p className="text-[10px] text-cyan-400/60 mb-3 italic">
            {t.disclaimer}
          </p>
          <ContentComponent lang={lang} />
          {!scrolledTabs[activeTab] && (
            <p className="text-[10px] text-yellow-400/80 text-center mt-6 animate-pulse">
              &#8595; {t.scrollHint} &#8595;
            </p>
          )}
        </div>

        {/* Checkboxes + Button */}
        <div className="p-3 sm:p-6 pt-2 sm:pt-4 border-t border-slate-700/50 flex-shrink-0 space-y-2 sm:space-y-3">
          {!allScrolled && (
            <p className="text-[10px] text-slate-500 text-center">
              {t.scrollAllHint}
            </p>
          )}

          <label className={`flex items-start gap-2 text-[11px] sm:text-xs cursor-pointer ${allScrolled ? "text-slate-300" : "text-slate-600 pointer-events-none"}`}>
            <input type="checkbox" checked={checks.notInvestment} onChange={(e) => setChecks((p) => ({ ...p, notInvestment: e.target.checked }))} disabled={!allScrolled} className="mt-0.5 accent-cyan-400 min-w-[16px]" />
            {t.check1}
          </label>

          <label className={`flex items-start gap-2 text-[11px] sm:text-xs cursor-pointer ${allScrolled ? "text-slate-300" : "text-slate-600 pointer-events-none"}`}>
            <input type="checkbox" checked={checks.risks} onChange={(e) => setChecks((p) => ({ ...p, risks: e.target.checked }))} disabled={!allScrolled} className="mt-0.5 accent-cyan-400 min-w-[16px]" />
            {t.check2}
          </label>

          <label className={`flex items-start gap-2 text-[11px] sm:text-xs cursor-pointer ${allScrolled ? "text-slate-300" : "text-slate-600 pointer-events-none"}`}>
            <input type="checkbox" checked={checks.terms} onChange={(e) => setChecks((p) => ({ ...p, terms: e.target.checked }))} disabled={!allScrolled} className="mt-0.5 accent-cyan-400 min-w-[16px]" />
            {t.check3}
          </label>

          <label className={`flex items-start gap-2 text-[11px] sm:text-xs cursor-pointer ${allScrolled ? "text-slate-300" : "text-slate-600 pointer-events-none"}`}>
            <input type="checkbox" checked={checks.privacy} onChange={(e) => setChecks((p) => ({ ...p, privacy: e.target.checked }))} disabled={!allScrolled} className="mt-0.5 accent-cyan-400 min-w-[16px]" />
            {t.check4}
          </label>

          <button
            onClick={handleEnter}
            disabled={!allChecked}
            className={`w-full py-3 rounded-xl text-sm font-bold tracking-wider transition-all mt-2 ${
              allChecked
                ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 shadow-lg shadow-cyan-500/20"
                : "bg-slate-800 text-slate-600 cursor-not-allowed"
            }`}
          >
            {t.enter}
          </button>
        </div>
      </div>
    </div>
  );
}
