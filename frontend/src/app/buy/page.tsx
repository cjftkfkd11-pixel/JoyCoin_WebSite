"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLanguage } from '@/lib/LanguageContext';
import { useAuth } from '@/lib/AuthContext';

export default function BuyPage() {
  const router = useRouter();
  const { t, locale } = useLanguage();
  const { isLoggedIn, isLoading: authLoading } = useAuth();

  const [products, setProducts] = useState<any[]>([]);
  const [totalUsdt, setTotalUsdt] = useState(0);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [selectedChain, setSelectedChain] = useState("TRC20");
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [depositInfo, setDepositInfo] = useState<{ id: number; address: string; amount: number; joyAmount: number; chain: string } | null>(null);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${API_BASE_URL}/products`)
      .then(res => res.json())
      .then(data => {
        setProducts(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleProductClick = (product: any) => {
    setTotalUsdt(prev => prev + product.price_usdt);
    setSelectedItems(prev => [...prev, product.name]);
    setMessage({ type: '', text: '' });
  };

  const resetSelection = () => {
    setTotalUsdt(0);
    setSelectedItems([]);
    setMessage({ type: '', text: '' });
  };

  const handleDepositRequest = async () => {
    if (totalUsdt <= 0) {
      return alert(locale === 'ko' ? "구매하실 패키지를 먼저 선택해주세요!" : "Please select a package first!");
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
          amount: totalUsdt,
          joyAmount: result.joy_amount || totalUsdt * 5,
          chain: selectedChain
        });
        setMessage({
          type: 'success',
          text: locale === 'ko' ? '입금 요청이 생성되었습니다! 아래 주소로 입금해주세요.' : 'Deposit request created! Please send to the address below.'
        });
        resetSelection();

      } else if (response.status === 401) {
        setMessage({ type: 'error', text: locale === 'ko' ? "인증 세션이 만료되었습니다. 다시 로그인해주세요." : "Session expired. Please login again." });
        setTimeout(() => router.push('/auth/login'), 2000);
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || (locale === 'ko' ? "입금 요청 실패" : "Deposit request failed") });
      }
    } catch (err) {
      setMessage({ type: 'error', text: locale === 'ko' ? "서버 연결에 실패했습니다." : "Server connection failed." });
    } finally {
      setRequesting(false);
    }
  };

  if (loading) return <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center font-black italic">{t("loading").toUpperCase()}</div>;

  const closeDepositInfo = () => {
    setDepositInfo(null);
    setMessage({ type: '', text: '' });
  };

  const copyAddress = () => {
    if (depositInfo?.address) {
      navigator.clipboard.writeText(depositInfo.address);
      alert(t("copied"));
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white p-8 font-sans">
      {/* 입금 정보 모달 */}
      {depositInfo && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-6">
          <div className="glass p-10 rounded-[2.5rem] w-full max-w-lg border border-blue-500/20 shadow-2xl relative">
            <button
              onClick={closeDepositInfo}
              className="absolute top-6 right-6 text-slate-500 hover:text-white text-2xl font-bold"
            >
              ×
            </button>

            <h2 className="text-2xl font-black italic text-blue-500 mb-8 text-center">
              {locale === 'ko' ? '입금 정보' : 'Deposit Info'}
            </h2>

            {/* QR 코드 */}
            <div className="bg-white p-6 rounded-2xl mb-6 flex justify-center">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${depositInfo.address}`}
                alt="QR Code"
                className="w-48 h-48"
              />
            </div>

            {/* 입금 정보 */}
            <div className="space-y-4">
              <div className="bg-slate-900/50 p-4 rounded-xl">
                <div className="flex justify-between items-center mb-2">
                  <p className="text-[10px] text-slate-500 font-bold uppercase">{t("address")}</p>
                  <button
                    onClick={copyAddress}
                    className="text-[10px] font-bold text-blue-400 hover:text-blue-300 transition-all px-3 py-1 bg-blue-500/10 rounded-lg hover:bg-blue-500/20"
                  >
                    {t("copy")}
                  </button>
                </div>
                <p className="text-xs font-mono text-blue-300 break-all select-all">{depositInfo.address}</p>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-900/50 p-4 rounded-xl">
                  <p className="text-[10px] text-slate-500 font-bold uppercase mb-2">{t("chain")}</p>
                  <p className="text-sm font-black text-white">{depositInfo.chain}</p>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-xl">
                  <p className="text-[10px] text-slate-500 font-bold uppercase mb-2">{t("amount")}</p>
                  <p className="text-sm font-black text-white">{depositInfo.amount} USDT</p>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/20 p-4 rounded-xl">
                  <p className="text-[10px] text-blue-400 font-bold uppercase mb-2">JOY</p>
                  <p className="text-sm font-black text-blue-400">{depositInfo.joyAmount.toLocaleString()}</p>
                </div>
              </div>

              <div className="bg-yellow-500/10 border border-yellow-500/20 p-4 rounded-xl text-[11px] text-yellow-400 leading-relaxed">
                <p className="font-bold mb-2">{locale === 'ko' ? '⚠️ 주의사항' : '⚠️ Important'}</p>
                <ul className="list-disc list-inside space-y-1 text-[10px]">
                  <li>{locale === 'ko' ? '반드시 위 주소로 정확한 금액을 입금해주세요' : 'Please send the exact amount to the address above'}</li>
                  <li>{locale === 'ko' ? `네트워크(${depositInfo.chain})를 정확히 선택해주세요` : `Make sure to select the correct network (${depositInfo.chain})`}</li>
                  <li>{locale === 'ko' ? '입금 후 관리자 승인까지 최대 10분 소요됩니다' : 'Approval may take up to 10 minutes after deposit'}</li>
                </ul>
              </div>

              <button
                onClick={() => router.push('/mypage')}
                className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-2xl font-black transition-all shadow-xl shadow-blue-900/20"
              >
                {locale === 'ko' ? '내역 확인하러 가기' : 'Check Deposit History'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto">

        <div className="flex justify-between items-center mb-10">
          <h1 className="text-4xl font-black italic text-blue-500 uppercase tracking-tighter">{t("buyJoycoin")}</h1>
          <button
            onClick={() => router.push('/mypage')}
            className="text-xs font-bold text-slate-500 hover:text-white transition-all underline underline-offset-4"
          >
            {locale === 'ko' ? '마이페이지로 돌아가기' : 'BACK TO MY PAGE'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          <div className="lg:col-span-2 space-y-6">
            <div className="flex justify-between items-end">
              <h2 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em]">{t("selectAmount")}</h2>
              <button onClick={resetSelection} className="text-[10px] text-red-500/70 hover:text-red-500 uppercase font-bold">
                {locale === 'ko' ? '선택 초기화' : 'Reset Selection'}
              </button>
            </div>

            {products.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {products.map((product) => (
                  <div
                    key={product.id}
                    onClick={() => handleProductClick(product)}
                    className="group cursor-pointer p-8 rounded-[2.5rem] border border-slate-800 bg-slate-900/30 hover:border-blue-500/50 hover:bg-blue-500/5 transition-all active:scale-[0.98]"
                  >
                    <h3 className="text-2xl font-black mb-2 group-hover:text-blue-400 transition-colors">{product.name}</h3>
                    <p className="text-slate-500 text-xs mb-8 leading-relaxed">{product.description}</p>
                    <div className="flex justify-between items-end">
                      <div className="text-3xl font-black text-white">
                        {product.price_usdt} <span className="text-sm text-blue-500 font-bold ml-1">USDT</span>
                      </div>
                      <div className="text-lg font-black text-blue-400">
                        = {(product.price_usdt * 5).toLocaleString()} <span className="text-xs">JOY</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="text-6xl mb-4">📦</div>
                <h3 className="text-xl font-black text-slate-400 mb-2">
                  {locale === 'ko' ? '패키지 준비 중' : 'Packages Coming Soon'}
                </h3>
                <p className="text-sm text-slate-600">
                  {locale === 'ko' ? '곧 새로운 패키지가 출시됩니다.' : 'New packages will be available soon.'}
                </p>
              </div>
            )}
          </div>

          <div className="space-y-6">
            <div className="glass p-8 rounded-[2.5rem] border border-blue-500/10 shadow-2xl sticky top-8">
              <h2 className="text-lg font-bold mb-8 text-slate-300 uppercase italic">{t("orderSummary")}</h2>

              <div className="mb-10">
                <label className="text-[10px] font-black text-slate-500 uppercase mb-4 block tracking-widest">{t("chain")}</label>
                <div className="grid grid-cols-2 gap-2">
                  {["TRC20", "ERC20", "BSC", "Polygon"].map((chain) => (
                    <button
                      key={chain}
                      onClick={() => setSelectedChain(chain)}
                      className={`py-3 rounded-xl font-bold text-xs transition-all ${
                        selectedChain === chain
                        ? 'bg-blue-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.4)]'
                        : 'bg-slate-800/50 text-slate-500 hover:bg-slate-800'
                      }`}
                    >
                      {chain}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4 mb-10 border-t border-slate-800/50 pt-8">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 text-xs font-bold uppercase">{t("total")}</span>
                  <span className="text-4xl font-black text-blue-500">{totalUsdt.toLocaleString()} <span className="text-xs">USDT</span></span>
                </div>
                <div className="flex justify-between items-center bg-blue-500/10 p-4 rounded-xl border border-blue-500/20">
                  <span className="text-blue-400 text-xs font-bold uppercase">{locale === 'ko' ? '받을 JOY' : 'JOY TO RECEIVE'}</span>
                  <span className="text-2xl font-black text-blue-400">{(totalUsdt * 5).toLocaleString()} <span className="text-xs">JOY</span></span>
                </div>
                <div className="bg-black/20 p-4 rounded-xl text-[10px] text-slate-600 italic break-words leading-normal min-h-[50px]">
                  {selectedItems.length > 0 ? selectedItems.join(' + ') : (locale === 'ko' ? '선택된 패키지가 없습니다.' : 'No packages selected yet.')}
                </div>
              </div>

              {message.text && (
                <div className={`mb-6 p-4 rounded-2xl text-[11px] font-bold text-center ${
                  message.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {message.text}
                </div>
              )}

              {authLoading ? (
                <div className="w-full py-5 bg-slate-800 rounded-[1.5rem] animate-pulse" />
              ) : isLoggedIn ? (
                <button
                  onClick={handleDepositRequest}
                  disabled={requesting || totalUsdt === 0}
                  className="w-full py-5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 rounded-[1.5rem] font-black text-lg transition-all shadow-xl shadow-blue-900/20 active:scale-95"
                >
                  {requesting ? t("loading") : (locale === 'ko' ? '입금 요청하기' : 'CONFIRM DEPOSIT')}
                </button>
              ) : (
                <div className="space-y-3">
                  <p className="text-center text-sm text-slate-400">
                    {locale === 'ko' ? '구매하시려면 로그인이 필요합니다' : 'Please login to purchase'}
                  </p>
                  <a
                    href="/auth/login"
                    className="block w-full py-5 bg-blue-600 hover:bg-blue-500 rounded-[1.5rem] font-black text-lg transition-all shadow-xl shadow-blue-900/20 text-center"
                  >
                    {t("login")}
                  </a>
                  <a
                    href="/auth/signup"
                    className="block w-full py-3 bg-slate-800 hover:bg-slate-700 rounded-xl font-bold text-sm transition-all text-center text-slate-300"
                  >
                    {locale === 'ko' ? '아직 계정이 없으신가요? 회원가입' : "Don't have an account? Sign up"}
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
