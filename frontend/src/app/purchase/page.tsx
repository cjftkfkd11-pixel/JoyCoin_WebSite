"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ActivationPage() {
  const [step, setStep] = useState(1);
  const [joyAmount, setJoyAmount] = useState(0);
  const [usdtPrice, setUsdtPrice] = useState(0);
  const router = useRouter();
  
  const EXCHANGE_RATE = 0.2; 
  const ACTIVATION_NODE = "TY7xxxxxxxxxxxxxxxxxxxxxxxxxxxx"; // 실제 주소

  useEffect(() => {
    setUsdtPrice(joyAmount * EXCHANGE_RATE);
  }, [joyAmount]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#020617] p-6 text-white font-sans">
      <div className="glass p-10 rounded-[2.5rem] w-full max-w-lg space-y-8 relative overflow-hidden">
        
        {/* 디자인 장식 */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl"></div>

        {step === 1 && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
            <div>
              <p className="text-blue-500 text-xs font-black uppercase tracking-[0.3em] mb-2">Phase 01</p>
              <h1 className="text-4xl font-black italic">ACTIVATE <span className="text-white">JOYCOIN</span></h1>
            </div>

            <div className="grid grid-cols-3 gap-4">
              {[1000, 5000, 10000].map((val) => (
                <button key={val} onClick={() => setJoyAmount(prev => prev + val)} className="py-5 bg-white/5 border border-white/10 rounded-2xl hover:bg-blue-600/20 hover:border-blue-500 transition-all font-bold text-lg">
                  +{val.toLocaleString()}
                </button>
              ))}
            </div>

            <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-[2rem] space-y-4">
              <div className="flex justify-between items-end"><span className="text-slate-500 text-sm font-bold">Activation Volume</span><span className="text-3xl font-black italic">{joyAmount.toLocaleString()} JOY</span></div>
              <div className="flex justify-between items-end border-t border-slate-800 pt-4"><span className="text-slate-500 text-sm font-bold">Required Power (U)</span><span className="text-3xl font-black text-blue-400 italic">{usdtPrice.toFixed(2)} U</span></div>
            </div>

            <button disabled={joyAmount === 0} onClick={() => setStep(2)} className="w-full py-5 bg-blue-600 disabled:bg-slate-800 font-black rounded-2xl text-xl shadow-lg shadow-blue-500/20 transition-all">
              PROCEED TO ACTIVATE
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6 text-center animate-in fade-in slide-in-from-right-4">
            <div>
              <p className="text-blue-500 text-xs font-black uppercase tracking-[0.3em] mb-2">Phase 02</p>
              <h1 className="text-3xl font-black italic"><span className="text-green-400">VERIFICATION</span></h1>
            </div>

            <div className="bg-white p-4 rounded-2xl inline-block mx-auto shadow-2xl">
              <img src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${ACTIVATION_NODE}`} alt="QR" className="w-40 h-40" />
            </div>

            <div className="space-y-2 text-left bg-slate-900/50 p-5 rounded-2xl border border-slate-800">
              <p className="text-[10px] text-slate-500 font-bold uppercase">Activation Node ID</p>
              <p className="text-xs font-mono break-all text-blue-300 select-all cursor-pointer">{ACTIVATION_NODE}</p>
            </div>

            <div className="text-[11px] text-slate-400 leading-relaxed bg-blue-500/5 p-4 rounded-xl border border-blue-500/20">
              <p>• <span className="text-white font-bold">{usdtPrice.toFixed(2)} U-Power</span>를 전송한 후 매칭 버튼을 눌러주세요.</p>
              <p>• 네트워크 유효성 검사 후 즉시 활성화가 완료됩니다.</p>
            </div>

            <button onClick={() => setStep(3)} className="w-full py-5 bg-blue-600 font-black rounded-2xl text-xl shadow-lg shadow-blue-500/20 transition-all">
              ACTIVATE REQUEST
            </button>
            <button onClick={() => setStep(1)} className="text-slate-500 text-xs font-bold uppercase">Go Back</button>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-8 text-center animate-in zoom-in">
            <div className="w-20 h-20 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-10 h-10 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
            </div>
            <div>
              <h1 className="text-3xl font-black italic mb-2">PENDING...</h1>
              <p className="text-slate-400 text-sm leading-relaxed">
                활성화 요청이 정상적으로 접수되었습니다.<br/>
                네트워크 노드 검증 절차가 진행 중이며<br/>
                잠시 후 자산 정보가 동기화됩니다.
              </p>
            </div>
            <button onClick={() => router.push('/deposits')} className="w-full py-5 bg-slate-800 font-black rounded-2xl text-xl hover:bg-slate-700 transition-all">내역 확인</button>
          </div>
        )}
      </div>
    </div>
  );
}