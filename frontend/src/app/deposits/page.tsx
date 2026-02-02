"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";

// [변경] 백엔드 상태값(pending, approved, rejected)에 맞게 매핑
function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    approved: "bg-green-500/10 text-green-500 border-green-500/20", // 성공
    rejected: "bg-red-500/10 text-red-500 border-red-500/20", // 거절
  };
  const labels: Record<string, string> = {
    pending: "Waiting",
    approved: "Completed",
    rejected: "Rejected",
  };

  return (
    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${styles[status] || styles.pending}`}>
      {labels[status] || status}
    </span>
  );
}

export default function MyPage() {
  const [items, setItems] = useState<any[]>([]); 
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState(""); // 사용자 이메일 표시용
  const router = useRouter();

  // 1. 실데이터 가져오기 (GET /deposits/my)
  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('accessToken');
      if (!token) {
        router.push('/auth/login');
        return;
      }

      try {
        const response = await fetch('http://localhost:8000/deposits/my', {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
          const data = await response.json();
          setItems(data.items || []); // 형님 명세서: { "items": [...] }
          // 임시로 로컬스토리지나 토큰에서 이메일을 가져올 수 있습니다.
          setUserEmail(localStorage.getItem('userEmail') || "user@joycoin.com");
        }
      } catch (error) {
        console.error("데이터 로드 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [router]);

  // 2. 총 자산 계산 (approved 상태인 금액만 합산)
  const totalJoy = useMemo(() => 
    items.filter(i => i.status === "approved").reduce((sum, i) => sum + i.expected_amount, 0)
  , [items]);

  if (loading) return <div className="min-h-screen bg-[#020617] flex items-center justify-center text-blue-500 font-black italic">SYNCING ASSETS...</div>;

  return (
    <div className="min-h-screen bg-[#020617] text-white p-6 pt-20 font-sans">
      <div className="max-w-2xl mx-auto space-y-6">
        
        {/* 1. 메인 자산 카드 */}
        <div className="glass p-8 rounded-[2.5rem] relative overflow-hidden border-white/5 bg-gradient-to-br from-blue-600/10 to-transparent">
          <div className="relative space-y-4">
            <p className="text-slate-500 text-xs font-black uppercase tracking-widest">Total Active Assets</p>
            <div className="flex items-baseline gap-2">
              <h1 className="text-6xl font-black italic">{totalJoy.toLocaleString()}</h1>
              <span className="text-blue-500 font-bold text-xl">USDT</span>
            </div>
          </div>
        </div>

        {/* 2. 내 추천 정보 (Referral ID) */}
        <div className="glass p-5 rounded-2xl border-white/5 flex justify-between items-center bg-slate-900/40">
          <div className="space-y-1">
            <p className="text-slate-500 text-[9px] font-black uppercase">My Referral ID (Email)</p>
            <p className="text-xs font-mono text-blue-300">{userEmail}</p>
          </div>
          <button 
            onClick={() => {navigator.clipboard.writeText(userEmail); alert("ID가 복사되었습니다.");}}
            className="text-[10px] font-black bg-white/5 px-4 py-2 rounded-xl hover:bg-white/10 transition-all uppercase border border-white/10"
          >
            Copy
          </button>
        </div>

        {/* 3. 활성화 로그 리스트 (GET /deposits/my 결과) */}
        <div className="space-y-4 pt-4">
          <div className="flex justify-between items-center px-2">
            <h2 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] italic">Activation Logs</h2>
            <span className="text-[10px] text-slate-600 font-bold">{items.length} Activities</span>
          </div>

          {items.length === 0 ? (
            <div className="p-10 text-center border border-white/5 rounded-[2rem] text-slate-600 text-xs font-bold uppercase tracking-widest">
              No activation history found
            </div>
          ) : (
            items.map((item) => (
              <div key={item.id} className="glass p-6 rounded-[2rem] flex items-center justify-between border-white/5 bg-slate-900/20 hover:border-blue-500/20 transition-all">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className="text-xl font-black italic">{item.expected_amount.toLocaleString()} USDT</span>
                    <StatusBadge status={item.status} />
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-tighter">
                    Network: {item.chain} | {new Date(item.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>

        {/* 하단 버튼 */}
        <button 
          onClick={() => router.push('/purchase')}
          className="w-full py-5 bg-blue-600 text-white font-black rounded-2xl hover:bg-blue-500 transition-all uppercase tracking-widest text-sm shadow-xl shadow-blue-900/20 active:scale-95"
        >
          + New Activation
        </button>
      </div>
    </div>
  );
}