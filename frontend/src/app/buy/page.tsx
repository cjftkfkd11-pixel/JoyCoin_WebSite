"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLanguage } from '@/lib/LanguageContext';
import { useAuth } from '@/lib/AuthContext';
import { useToast } from '@/components/Toast';
import { getApiBaseUrl } from '@/lib/apiBase';
import { copyText } from '@/lib/clipboard';

// 패키지 다국어 매핑 (joy_amount 기준)
const packageNamesByJoy: Record<number, { ko: string; en: string }> = {
  1000: { ko: 'JOY 1,000개 패키지', en: 'JOY 1,000 Package' },
  2000: { ko: 'JOY 2,000개 패키지', en: 'JOY 2,000 Package' },
  5000: { ko: 'JOY 5,000개 패키지', en: 'JOY 5,000 Package' },
  10000: { ko: 'JOY 10,000개 패키지', en: 'JOY 10,000 Package' },
  50000: { ko: 'JOY 50,000개 패키지', en: 'JOY 50,000 Package' },
};

export default function BuyPage() {
  const router = useRouter();
  const { t, locale } = useLanguage();
  const { isLoggedIn, isLoading: authLoading } = useAuth();
  const { toast } = useToast();

  const [products, setProducts] = useState<any[]>([]);
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [depositInfo, setDepositInfo] = useState<{ id: number; address: string; amount: number; joyAmount: number; chain: string } | null>(null);
  const [joyPerUsdt, setJoyPerUsdt] = useState(5.0);
  const [selectedChain, setSelectedChain] = useState('Solana');
  const [showConsent, setShowConsent] = useState(false);
  const [consentChecks, setConsentChecks] = useState({
    notInvestment: false,
    risks: false,
    notGuaranteed: false,
    voluntary: false,
  });

  const chains = [
    { id: 'Solana', label: 'Solana (USDT)', color: 'purple' },
  ];

  const API_BASE_URL = getApiBaseUrl();

  useEffect(() => {
    // 상품 + 환율 동시 로드
    Promise.all([
      fetch(`${API_BASE_URL}/products`).then(res => res.json()),
      fetch(`${API_BASE_URL}/exchange-rate`).then(res => res.json()),
    ])
      .then(([productData, rateData]) => {
        setProducts(productData);
        const initQty: Record<number, number> = {};
        productData.forEach((p: any) => { initQty[p.id] = 0; });
        setQuantities(initQty);
        if (rateData.joy_per_usdt) setJoyPerUsdt(rateData.joy_per_usdt);
        setLoading(false);
      })
      .catch(() => { setLoading(false); setLoadError(true); });
  }, []);

  const updateQuantity = (productId: number, delta: number) => {
    setQuantities(prev => ({
      ...prev,
      [productId]: Math.max(0, (prev[productId] || 0) + delta)
    }));
    setMessage({ type: '', text: '' });
  };

  const totalUsdt = products.reduce((sum, p) => sum + (p.price_usdt * (quantities[p.id] || 0)), 0);
  const totalJoy = products.reduce((sum, p) => sum + (p.joy_amount * (quantities[p.id] || 0)), 0);

  const resetSelection = () => {
    const resetQty: Record<number, number> = {};
    products.forEach((p: any) => { resetQty[p.id] = 0; });
    setQuantities(resetQty);
    setMessage({ type: '', text: '' });
  };

  const getPackageName = (product: any) => {
    const mapped = packageNamesByJoy[product.joy_amount];
    if (mapped) return locale === 'ko' ? mapped.ko : mapped.en;
    // 매핑에 없는 경우 자동 생성
    if (locale === 'ko') return product.name;
    return `JOY ${product.joy_amount.toLocaleString()} Package`;
  };

  const handleDepositRequest = async () => {
    if (totalUsdt <= 0) {
      toast(locale === 'ko' ? "참여하실 패키지를 먼저 선택해주세요!" : "Please select a package first!", "warning");
      return;
    }

    setRequesting(true);
    setMessage({ type: '', text: '' });

    try {
      const response = await fetch(`${API_BASE_URL}/deposits/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          chain: selectedChain,
          amount_usdt: totalUsdt
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setDepositInfo({
          id: result.id,
          address: result.assigned_address,
          amount: result.expected_amount || totalUsdt,
          joyAmount: result.joy_amount || totalUsdt * joyPerUsdt,
          chain: selectedChain
        });
        setMessage({
          type: 'success',
          text: locale === 'ko' ? '입금 요청이 생성되었습니다!' : 'Deposit request created!'
        });
        resetSelection();
      } else if (response.status === 401) {
        setMessage({ type: 'error', text: locale === 'ko' ? "로그인이 필요합니다." : "Please login first." });
        setTimeout(() => router.push('/auth/login'), 2000);
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || (locale === 'ko' ? "입금 요청 실패" : "Deposit request failed") });
      }
    } catch {
      setMessage({ type: 'error', text: locale === 'ko' ? "서버 연결에 실패했습니다." : "Server connection failed." });
    } finally {
      setRequesting(false);
    }
  };

  if (loading) return <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center font-semibold">{t("loading")}</div>;
  if (loadError) return (
    <div className="min-h-screen bg-[#020617] text-white flex flex-col items-center justify-center gap-4">
      <p className="text-red-400 font-bold">{locale === 'ko' ? '상품 정보를 불러올 수 없습니다.' : 'Failed to load products.'}</p>
      <button onClick={() => window.location.reload()} className="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold transition-all">
        {locale === 'ko' ? '다시 시도' : 'Retry'}
      </button>
    </div>
  );

  const closeDepositInfo = () => {
    setDepositInfo(null);
    setMessage({ type: '', text: '' });
  };

  const copyAddress = async () => {
    if (depositInfo?.address) {
      const copied = await copyText(depositInfo.address);
      if (copied) {
        toast(locale === 'ko' ? '복사되었습니다!' : 'Copied!', 'success');
      } else {
        toast(locale === 'ko' ? '복사에 실패했습니다.' : 'Copy failed.', 'error');
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white p-4 sm:p-6 pb-24 md:p-8 md:pb-24">
      {/* 입금 정보 모달 */}
      {depositInfo && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 p-5 sm:p-8 rounded-2xl sm:rounded-3xl w-full max-w-lg border border-blue-500/20 shadow-2xl relative max-h-[95vh] overflow-y-auto">
            <button onClick={closeDepositInfo} className="absolute top-3 right-3 sm:top-4 sm:right-4 text-slate-500 hover:text-white text-2xl">×</button>

            <h2 className="text-xl sm:text-2xl font-bold text-blue-400 mb-4 sm:mb-6 text-center">
              {locale === 'ko' ? '입금 정보' : 'Deposit Info'}
            </h2>

            <div className="bg-white p-3 sm:p-4 rounded-xl mb-4 flex justify-center">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${depositInfo.address}`}
                alt="QR Code"
                className="w-32 h-32 sm:w-44 sm:h-44"
              />
            </div>

            <div className="space-y-3">
              <div className="bg-slate-800 p-4 rounded-xl">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs text-slate-400">{locale === 'ko' ? `USDT 입금 주소 (Solana 네트워크)` : `USDT Address (Solana Network)`}</span>
                  <button type="button" onClick={copyAddress} className="text-xs text-blue-400 hover:text-blue-300 px-2 py-1 bg-blue-500/10 rounded touch-manipulation">
                    {locale === 'ko' ? '복사' : 'Copy'}
                  </button>
                </div>
                <p className="text-sm font-mono text-blue-300 break-all">{depositInfo.address}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-800 p-4 rounded-xl text-center">
                  <p className="text-xs text-slate-400 mb-1">{locale === 'ko' ? '입금 금액' : 'Amount'}</p>
                  <p className="text-base sm:text-xl font-bold">{depositInfo.amount} USDT</p>
                </div>
                <div className="bg-blue-600/20 border border-blue-500/30 p-4 rounded-xl text-center">
                  <p className="text-xs text-blue-300 mb-1">{locale === 'ko' ? '받을 JOY' : 'JOY to receive'}</p>
                  <p className="text-base sm:text-xl font-bold text-blue-400">{depositInfo.joyAmount.toLocaleString()}</p>
                </div>
              </div>

              <div className="bg-yellow-500/10 border border-yellow-500/20 p-3 rounded-xl text-xs text-yellow-400">
                <p className="font-semibold mb-1">{locale === 'ko' ? '⚠️ 주의사항' : '⚠️ Important'}</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>{locale === 'ko' ? `반드시 Solana 네트워크로 입금해주세요 (SPL USDT)` : `Send via Solana network only (SPL USDT)`}</li>
                  <li>{locale === 'ko' ? '소수점 포함 정확한 금액을 입금해주세요 (예: 200.37 USDT)' : 'Send the exact amount including decimals (e.g. 200.37 USDT)'}</li>
                  <li>{locale === 'ko' ? '다른 네트워크로 전송 시 복구 불가' : 'Wrong network = unrecoverable'}</li>
                </ul>
              </div>

              <button
                onClick={() => window.location.href = '/mypage'}
                className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold transition-all"
              >
                {locale === 'ko' ? '마이페이지에서 확인' : 'Check in My Page'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Participation Consent Modal */}
      {showConsent && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 p-5 sm:p-8 rounded-2xl sm:rounded-3xl w-full max-w-lg border border-cyan-500/20 shadow-2xl relative max-h-[95vh] overflow-y-auto">
            <button onClick={() => setShowConsent(false)} className="absolute top-3 right-3 sm:top-4 sm:right-4 text-slate-500 hover:text-white text-2xl">&times;</button>

            <h2 className="text-lg sm:text-xl font-bold text-white mb-2 text-center">
              {locale === 'ko' ? '참여 확인' : 'Participation Confirmation'}
            </h2>
            <p className="text-xs text-slate-400 text-center mb-6">
              {locale === 'ko'
                ? 'JOY 참여 단위 배정을 요청합니다. 아래 사항을 확인해 주세요:'
                : 'You are requesting allocation of JOY participation units. Please confirm:'}
            </p>

            <div className="space-y-3 mb-6">
              <p className="text-xs text-slate-400 leading-relaxed">
                {locale === 'ko'
                  ? 'JOY는 투자 상품이 아닙니다. 배정은 관리자 확인 후 진행됩니다. 디지털 자산 전송은 되돌릴 수 없습니다. 참여는 자발적이며 본인의 책임 하에 이루어집니다.'
                  : 'JOY is not an investment product. Allocation is subject to verification. Digital asset transfers are irreversible. Participation is voluntary and at your own risk.'}
              </p>
            </div>

            <div className="space-y-3 mb-6">
              <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" checked={consentChecks.notInvestment} onChange={e => setConsentChecks(p => ({...p, notInvestment: e.target.checked}))} className="mt-0.5 accent-cyan-400" />
                {locale === 'ko' ? 'JOY가 투자 상품이 아님을 이해합니다' : 'I understand JOY is not an investment product'}
              </label>
              <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" checked={consentChecks.risks} onChange={e => setConsentChecks(p => ({...p, risks: e.target.checked}))} className="mt-0.5 accent-cyan-400" />
                {locale === 'ko' ? '디지털 자산 전송 위험을 인정합니다' : 'I acknowledge digital asset transfer risks'}
              </label>
              <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" checked={consentChecks.notGuaranteed} onChange={e => setConsentChecks(p => ({...p, notGuaranteed: e.target.checked}))} className="mt-0.5 accent-cyan-400" />
                {locale === 'ko' ? '배정이 보장되지 않음을 수락합니다' : 'I accept that allocation is not guaranteed'}
              </label>
              <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" checked={consentChecks.voluntary} onChange={e => setConsentChecks(p => ({...p, voluntary: e.target.checked}))} className="mt-0.5 accent-cyan-400" />
                {locale === 'ko' ? '자발적 참여임을 확인합니다' : 'I confirm participation is voluntary'}
              </label>
            </div>

            <button
              onClick={() => { setShowConsent(false); handleDepositRequest(); }}
              disabled={!consentChecks.notInvestment || !consentChecks.risks || !consentChecks.notGuaranteed || !consentChecks.voluntary}
              className={`w-full py-3 rounded-xl text-sm font-bold tracking-wider transition-all ${
                consentChecks.notInvestment && consentChecks.risks && consentChecks.notGuaranteed && consentChecks.voluntary
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 shadow-lg shadow-cyan-500/20'
                  : 'bg-slate-800 text-slate-600 cursor-not-allowed'
              }`}
            >
              {locale === 'ko' ? '참여 요청' : 'REQUEST ALLOCATION'}
            </button>
          </div>
        </div>
      )}

      <div className="max-w-5xl mx-auto">
        <div className="flex justify-between items-center mb-5 sm:mb-8">
          <h1 className="text-lg sm:text-3xl md:text-4xl font-bold text-blue-400">{locale === 'ko' ? 'JOY 참여 요청' : 'Request JOY Allocation'}</h1>
          <a href="/mypage" className="text-xs sm:text-sm text-slate-400 hover:text-white underline flex-shrink-0">
            {locale === 'ko' ? '마이페이지' : 'My Page'}
          </a>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 sm:gap-8">
          {/* 패키지 목록 */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
              {locale === 'ko' ? '패키지 선택' : 'Select Package'}
            </h2>

            {products.length > 0 ? (
              <div className="space-y-4">
                {products.map((product) => (
                  <div key={product.id} className="bg-slate-900/50 border border-slate-800 rounded-xl sm:rounded-2xl p-4 sm:p-6 flex flex-col md:flex-row md:items-center justify-between gap-3 sm:gap-4">
                    <div className="flex-1">
                      <h3 className="text-base sm:text-xl font-bold text-white mb-1">{getPackageName(product)}</h3>
                      <p className="text-xs sm:text-sm text-slate-400 mb-2">{product.description}</p>
                      <div className="flex items-center gap-2 sm:gap-3">
                        <span className="text-lg sm:text-2xl font-bold">{product.price_usdt} USDT</span>
                        <span className="text-sm sm:text-base text-blue-400">= {product.joy_amount.toLocaleString()} JOY</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => updateQuantity(product.id, -1)}
                        disabled={quantities[product.id] === 0}
                        className="w-11 h-11 sm:w-10 sm:h-10 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed rounded-xl text-xl font-bold transition-all"
                      >
                        −
                      </button>
                      <span className="w-10 sm:w-12 text-center text-lg sm:text-xl font-bold">{quantities[product.id] || 0}</span>
                      <button
                        onClick={() => updateQuantity(product.id, 1)}
                        className="w-11 h-11 sm:w-10 sm:h-10 bg-blue-600 hover:bg-blue-500 rounded-xl text-xl font-bold transition-all"
                      >
                        +
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-16">
                <p className="text-4xl mb-4">📦</p>
                <h3 className="text-xl font-bold text-slate-400">{locale === 'ko' ? '패키지 준비 중' : 'Coming Soon'}</h3>
              </div>
            )}
          </div>

          {/* 주문 요약 */}
          <div className="lg:sticky lg:top-24 h-fit space-y-4">
            {/* 체인 선택 */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl sm:rounded-2xl p-4 sm:p-6">
              <h2 className="text-xs sm:text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                {locale === 'ko' ? '네트워크 선택' : 'Select Network'}
              </h2>
              <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
                {chains.map(chain => (
                  <button
                    key={chain.id}
                    onClick={() => setSelectedChain(chain.id)}
                    className={`py-3.5 px-1 rounded-xl text-[10px] sm:text-xs font-bold transition-all text-center ${
                      selectedChain === chain.id
                        ? 'bg-blue-600 text-white border border-blue-500'
                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white border border-transparent'
                    }`}
                  >
                    {chain.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl sm:rounded-2xl p-4 sm:p-6">
              <h2 className="text-base sm:text-lg font-bold text-white mb-4 sm:mb-6">{locale === 'ko' ? '참여 요약' : 'Allocation Summary'}</h2>

              {/* 선택된 패키지 목록 */}
              <div className="space-y-2 mb-6 max-h-40 overflow-y-auto">
                {products.filter(p => quantities[p.id] > 0).map(p => (
                  <div key={p.id} className="flex justify-between text-sm">
                    <span className="text-slate-400">{getPackageName(p)} × {quantities[p.id]}</span>
                    <span className="text-white">{(p.price_usdt * quantities[p.id]).toLocaleString()} USDT</span>
                  </div>
                ))}
                {products.filter(p => quantities[p.id] > 0).length === 0 && (
                  <p className="text-sm text-slate-500 text-center py-4">{locale === 'ko' ? '선택된 패키지 없음' : 'No package selected'}</p>
                )}
              </div>

              <div className="border-t border-slate-800 pt-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400">{locale === 'ko' ? '총 참여금액' : 'Total'}</span>
                  <span className="text-lg sm:text-2xl font-bold">{totalUsdt.toLocaleString()} USDT</span>
                </div>
                <div className="flex justify-between bg-blue-600/20 p-3 rounded-xl">
                  <span className="text-blue-300">{locale === 'ko' ? '배정 JOY' : 'JOY Allocation'}</span>
                  <span className="text-xl font-bold text-blue-400">{totalJoy.toLocaleString()} JOY</span>
                </div>
              </div>

              {message.text && (
                <div className={`mt-4 p-3 rounded-xl text-sm text-center ${
                  message.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                }`}>
                  {message.text}
                </div>
              )}

              <div className="mt-6">
                {authLoading ? (
                  <div className="w-full py-4 bg-slate-800 rounded-xl animate-pulse" />
                ) : (
                  <>
                    {!isLoggedIn && (
                      <p className="text-center text-xs text-slate-500 mb-3">
                        {locale === 'ko' ? '* 참여하려면 로그인이 필요합니다' : '* Login required to participate'}
                      </p>
                    )}
                    <button
                      onClick={() => {
                        if (!isLoggedIn) {
                          const confirmed = confirm(
                            locale === 'ko'
                              ? '로그인이 필요한 서비스입니다.\n로그인 페이지로 이동하시겠습니까?'
                              : 'Login is required.\nWould you like to go to the login page?'
                          );
                          if (confirmed) {
                            router.push('/auth/login');
                          }
                          return;
                        }
                        setConsentChecks({ notInvestment: false, risks: false, notGuaranteed: false, voluntary: false });
                        setShowConsent(true);
                      }}
                      disabled={requesting || totalUsdt === 0}
                      className="w-full py-4 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 rounded-xl font-bold text-lg transition-all"
                    >
                      {requesting ? (locale === 'ko' ? '처리 중...' : 'Processing...') : (locale === 'ko' ? '참여 요청' : 'Request Allocation')}
                    </button>
                  </>
                )}

                {totalUsdt > 0 && (
                  <button onClick={resetSelection} className="w-full mt-3 py-2 text-sm text-slate-500 hover:text-red-400 transition-all">
                    {locale === 'ko' ? '선택 초기화' : 'Reset'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 모바일 하단 고정 버튼 */}
      {totalUsdt > 0 && !authLoading && (
        <div className="lg:hidden fixed bottom-0 left-0 right-0 p-4 bg-[#020617]/95 backdrop-blur-md border-t border-slate-800 z-40">
          <div className="flex items-center gap-3">
            <div className="flex-1 text-sm">
              <span className="text-slate-400">{totalJoy.toLocaleString()} JOY</span>
              <span className="text-slate-600 mx-1">·</span>
              <span className="text-white font-bold">{totalUsdt.toLocaleString()} USDT</span>
            </div>
            <button
              onClick={() => {
                if (!isLoggedIn) {
                  const confirmed = confirm(
                    locale === 'ko'
                      ? '로그인이 필요한 서비스입니다.\n로그인 페이지로 이동하시겠습니까?'
                      : 'Login is required.\nWould you like to go to the login page?'
                  );
                  if (confirmed) router.push('/auth/login');
                  return;
                }
                setConsentChecks({ notInvestment: false, risks: false, notGuaranteed: false, voluntary: false });
                setShowConsent(true);
              }}
              disabled={requesting}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 rounded-xl font-bold text-sm transition-all"
            >
              {requesting ? (locale === 'ko' ? '처리 중...' : 'Processing...') : (locale === 'ko' ? '참여 요청' : 'Request')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
