"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiBaseUrl } from "@/lib/apiBase";

interface PointHistory {
  id: number;
  amount: number;
  balance_after: number;
  type: string;
  description: string;
  created_at: string;
}

interface Withdrawal {
  id: number;
  amount: number;
  method: string;
  account_info: string;
  status: string;
  created_at: string;
}

interface UserInfo {
  wallet_address?: string;
}

export default function PointsPage() {
  const router = useRouter();
  const API = getApiBaseUrl();

  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState(0);
  const [history, setHistory] = useState<PointHistory[]>([]);
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
  const [user, setUser] = useState<UserInfo | null>(null);

  // 전환 신청 폼
  const [showForm, setShowForm] = useState(false);
  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [pointsRes, withdrawalsRes, userRes] = await Promise.all([
        fetch(`${API}/points/my`, { credentials: "include" }),
        fetch(`${API}/points/withdrawals`, { credentials: "include" }),
        fetch(`${API}/auth/me`, { credentials: "include" }),
      ]);

      if (pointsRes.status === 401) {
        router.push("/auth/login");
        return;
      }

      if (pointsRes.ok) {
        const data = await pointsRes.json();
        setBalance(data.balance);
        setHistory(data.history || []);
      }

      if (withdrawalsRes.ok) {
        const data = await withdrawalsRes.json();
        setWithdrawals(data);
      }

      if (userRes.ok) {
        const data = await userRes.json();
        setUser(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const res = await fetch(`${API}/points/withdraw`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          amount: Number(amount),
          method: "joy",
          account_info: user?.wallet_address || "",
        }),
      });

      const data = await res.json();
      if (res.ok) {
        alert("JOY 코인 전환 신청이 완료되었습니다.");
        setShowForm(false);
        setAmount("");
        fetchData();
      } else {
        setError(data.detail || "전환 신청 실패");
      }
    } catch {
      setError("서버 연결 실패");
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-[10px] font-bold rounded">처리중</span>;
      case "approved":
        return <span className="px-2 py-1 bg-green-500/20 text-green-400 text-[10px] font-bold rounded">완료</span>;
      case "rejected":
        return <span className="px-2 py-1 bg-red-500/20 text-red-400 text-[10px] font-bold rounded">반려</span>;
      default:
        return <span className="text-slate-500">{status}</span>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-blue-500 font-black">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 sm:p-6 text-white font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        <h1 className="text-2xl sm:text-3xl font-black italic text-blue-500">MY JOY POINTS</h1>

        {/* JOY 포인트 잔액 + 전환 버튼 */}
        <div className="glass p-4 sm:p-8 rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-emerald-600/10 to-transparent">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                보유 JOY 포인트
              </p>
              <p className="text-2xl sm:text-4xl font-black text-emerald-400">
                {balance.toLocaleString()} <span className="text-sm">P</span>
              </p>
              <p className="text-[10px] text-slate-500 mt-1">
                JOY 포인트를 JOY 코인으로 전환할 수 있습니다
              </p>
            </div>
            <button
              onClick={() => setShowForm(true)}
              disabled={balance <= 0}
              className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 rounded-xl font-black text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
            >
              JOY 코인으로 수령
            </button>
          </div>
        </div>

        {/* 전환 신청 모달 */}
        {showForm && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="glass p-5 sm:p-8 rounded-2xl w-full max-w-md border border-emerald-500/20 shadow-2xl relative">
              <button
                onClick={() => { setShowForm(false); setError(""); setAmount(""); }}
                className="absolute top-3 right-3 text-slate-500 hover:text-white text-xl font-bold"
              >×</button>

              <h2 className="text-xl font-black text-emerald-400 mb-6">
                JOY 포인트 → JOY 코인 전환
              </h2>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* 보유 포인트 */}
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex justify-between items-center">
                  <span className="text-xs text-slate-400">보유 JOY 포인트</span>
                  <span className="font-black text-emerald-400">{balance.toLocaleString()} P</span>
                </div>

                {/* 전환 수량 입력 */}
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">
                    전환 수량
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      required
                      min={1}
                      max={balance}
                      placeholder={`최대 ${balance.toLocaleString()}P`}
                      className="flex-1 bg-slate-900/50 border border-slate-700 p-3 rounded-xl outline-none focus:border-emerald-500 text-sm font-mono"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setAmount(String(balance))}
                      className="px-3 py-2 text-xs font-bold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-xl transition-all"
                    >
                      전체
                    </button>
                  </div>
                </div>

                {/* 네트워크 (고정) */}
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">
                    네트워크
                  </label>
                  <div className="py-2 px-4 rounded-xl text-xs font-bold bg-emerald-600 text-white border border-emerald-500 text-center">
                    Solana
                  </div>
                </div>

                {/* 수령 지갑 주소 (자동) */}
                <div className="p-3 bg-slate-800/50 rounded-xl">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">
                    수령 지갑 주소
                  </p>
                  <p className="text-xs font-mono text-emerald-400 break-all">
                    {user?.wallet_address || "미등록 — 마이페이지에서 지갑 주소를 등록하세요"}
                  </p>
                </div>

                <p className="text-[9px] text-yellow-600">
                  ⚠️ JOY 포인트가 JOY 코인으로 전환되어 위 지갑 주소로 전송됩니다. 관리자 처리 후 전송되며, 처리 전에는 취소할 수 없습니다.
                </p>

                {error && <p className="text-red-400 text-xs text-center">{error}</p>}

                <button
                  type="submit"
                  disabled={submitting || !user?.wallet_address}
                  className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-xl font-black transition-all"
                >
                  {submitting ? "처리중..." : "JOY 코인으로 수령"}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* 전환 신청 내역 */}
        {withdrawals.length > 0 && (
          <div className="glass p-6 rounded-2xl border border-slate-800/50">
            <h2 className="font-bold text-sm text-slate-400 uppercase tracking-widest mb-4">
              전환 신청 내역
            </h2>
            <div className="space-y-2">
              {withdrawals.map((w) => (
                <div
                  key={w.id}
                  className="flex justify-between items-center p-3 bg-slate-900/30 rounded-xl"
                >
                  <div>
                    <p className="font-bold">{w.amount.toLocaleString()} P → JOY</p>
                    <p className="text-xs text-slate-500">
                      Solana • {new Date(w.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  {getStatusBadge(w.status)}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 포인트 적립 내역 */}
        <div className="glass p-6 rounded-2xl border border-slate-800/50">
          <h2 className="font-bold text-sm text-slate-400 uppercase tracking-widest mb-4">
            JOY 포인트 내역
          </h2>
          {history.length > 0 ? (
            <div className="space-y-2">
              {history.map((h) => (
                <div
                  key={h.id}
                  className="flex justify-between items-center p-3 bg-slate-900/30 rounded-xl"
                >
                  <div>
                    <p className="text-xs text-slate-400">{h.description}</p>
                    <p className="text-[10px] text-slate-600">
                      {new Date(h.created_at).toLocaleString()}
                    </p>
                  </div>
                  <p className={`font-bold ${h.amount >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {h.amount >= 0 ? "+" : ""}{h.amount.toLocaleString()}P
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-slate-600 py-8">JOY 포인트 내역이 없습니다.</p>
          )}
        </div>
      </div>
    </div>
  );
}
