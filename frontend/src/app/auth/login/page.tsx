"use client";
import { useState, useEffect } from "react";
import { login } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registeredMsg, setRegisteredMsg] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (searchParams.get("registered") === "1") {
      setRegisteredMsg(true);
    }
  }, [searchParams]);

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(email, password);
      localStorage.setItem("access", res.access);
      router.push("/deposits");
    } catch (e: any) {
      setError(e.message || "로그인 실패");
    } finally { 
      setLoading(false); 
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-12">
      <div className="glass p-8 md:p-12 rounded-3xl w-full max-w-md shadow-2xl border border-slate-700/50">
        <h2 className="text-3xl font-black mb-8 text-center text-white">로그인</h2>

        {registeredMsg && (
          <p className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm text-center">
            회원가입이 완료되었습니다. 로그인해 주세요.
          </p>
        )}

        <form onSubmit={onLogin} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2 uppercase tracking-wider">이메일</label>
            <input 
              type="email"
              value={email} 
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3.5 focus:ring-2 focus:ring-blue-500 outline-none transition text-white"
              placeholder="이메일을 입력하세요"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2 uppercase tracking-wider">비밀번호</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3.5 focus:ring-2 focus:ring-blue-500 outline-none transition text-white"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm text-center font-bold bg-red-500/10 py-3 rounded-xl border border-red-500/20">
              {error}
            </p>
          )}

          <button 
            type="submit"
            disabled={loading}
            className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-black text-lg rounded-xl shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98]"
          >
            {loading ? "로그인 중..." : "로그인"}
          </button>
        </form>

        <div className="mt-10 pt-6 border-t border-slate-800 text-center">
          <div className="flex flex-wrap justify-center gap-6 text-sm font-bold uppercase tracking-widest">
            <a href="/auth/signup" className="text-blue-500 hover:text-blue-400 transition underline underline-offset-4">
              회원가입
            </a>
            <a href="/" className="text-slate-500 hover:text-white transition">
              홈으로
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
