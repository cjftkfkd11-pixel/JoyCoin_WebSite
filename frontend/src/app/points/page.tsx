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

export default function PointsPage() {
  const router = useRouter();
  const API = getApiBaseUrl();

  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState(0);
  const [history, setHistory] = useState<PointHistory[]>([]);
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);

  // 출금 신청 폼
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    amount: "",
    method: "bank",
    account_info: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [pointsRes, withdrawalsRes] = await Promise.all([
        fetch(`${API}/points/my`, { credentials: "include" }),
        fetch(`${API}/points/withdrawals`, { credentials: "include" }),
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
          amount: Number(formData.amount),
          method: formData.method,
          account_info: formData.account_info,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        alert("출금 신청이 완료되었습니다.");
        setShowForm(false);
        setFormData({ amount: "", method: "bank", account_info: "" });
        fetchData();
      } else {
        setError(data.detail || "출금 신청 실패");
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
        return <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-[10px] font-bold rounded">대기중</span>;
      case "approved":
        return <span className="px-2 py-1 bg-green-500/20 text-green-400 text-[10px] font-bold rounded">완료</span>;
      case "rejected":
        return <span className="px-2 py-1 bg-red-500/20 text-red-400 text-[10px] font-bold rounded">거절</span>;
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
        <h1 className="text-2xl sm:text-3xl font-black italic text-blue-500">MY POINTS</h1>

        {/* 포인트 잔액 + 출금 버튼 */}
        <div className="glass p-4 sm:p-8 rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-emerald-600/10 to-transparent">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                Available Points
              </p>
              <p className="text-2xl sm:text-4xl font-black text-emerald-400">
                {balance.toLocaleString()} <span className="text-sm">P</span>
              </p>
            </div>
            <button
              onClick={() => setShowForm(true)}
              disabled={balance <= 0}
              className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 rounded-xl font-black text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
            >
              출금 신청
            </button>
          </div>
        </div>

        {/* 출금 신청 폼 */}
        {showForm && (
          <div className="glass p-6 rounded-2xl border border-blue-500/20 space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="font-bold text-lg">출금 신청</h2>
              <button
                onClick={() => setShowForm(false)}
                className="text-slate-500 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">출금 포인트</label>
                <input
                  type="number"
                  required
                  min={1}
                  max={balance}
                  placeholder={`최대 ${balance.toLocaleString()}P`}
                  className="w-full bg-slate-900/50 border border-slate-700 p-3 rounded-xl outline-none focus:border-blue-500"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">출금 방법</label>
                <select
                  required
                  className="w-full bg-slate-900/50 border border-slate-700 p-3 rounded-xl outline-none focus:border-blue-500"
                  value={formData.method}
                  onChange={(e) => setFormData({ ...formData, method: e.target.value })}
                >
                  <option value="bank">은행 계좌</option>
                  <option value="usdt">USDT 지갑</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">
                  {formData.method === "bank" ? "계좌번호 (은행명 포함)" : "USDT 지갑 주소 (TRC20)"}
                </label>
                <input
                  type="text"
                  required
                  placeholder={formData.method === "bank" ? "예: 신한은행 110-123-456789" : "예: TRx..."}
                  className="w-full bg-slate-900/50 border border-slate-700 p-3 rounded-xl outline-none focus:border-blue-500"
                  value={formData.account_info}
                  onChange={(e) => setFormData({ ...formData, account_info: e.target.value })}
                />
              </div>

              {error && <p className="text-red-400 text-xs">{error}</p>}

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-black transition-all disabled:opacity-50"
              >
                {submitting ? "처리중..." : "출금 신청"}
              </button>
            </form>
          </div>
        )}

        {/* 출금 내역 */}
        {withdrawals.length > 0 && (
          <div className="glass p-6 rounded-2xl border border-slate-800/50">
            <h2 className="font-bold text-sm text-slate-400 uppercase tracking-widest mb-4">
              출금 내역
            </h2>
            <div className="space-y-2">
              {withdrawals.map((w) => (
                <div
                  key={w.id}
                  className="flex justify-between items-center p-3 bg-slate-900/30 rounded-xl"
                >
                  <div>
                    <p className="font-bold">{w.amount.toLocaleString()}P</p>
                    <p className="text-xs text-slate-500">
                      {w.method === "bank" ? "은행" : "USDT"} • {new Date(w.created_at).toLocaleDateString()}
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
            포인트 내역
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
            <p className="text-center text-slate-600 py-8">포인트 내역이 없습니다.</p>
          )}
        </div>
      </div>
    </div>
  );
}
