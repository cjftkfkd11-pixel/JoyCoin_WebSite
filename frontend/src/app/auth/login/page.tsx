"use client";
import { useState } from "react";
import { login } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState(""); 
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onLogin = async () => {
    setLoading(true); setMsg(null);
    try {
      const res = await login(email, password);
      localStorage.setItem("access", res.access);
      setMsg("로그인 성공!");
    } catch (e:any) {
      setMsg(e.message);
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-md mx-auto bg-white border rounded-xl p-6">
      <h2 className="text-xl font-bold mb-4">로그인</h2>
      <label className="block text-sm mb-1">이메일</label>
      <input className="w-full border rounded p-2 mb-3" value={email} onChange={e=>setEmail(e.target.value)} />
      <label className="block text-sm mb-1">비밀번호</label>
      <input type="password" className="w-full border rounded p-2 mb-4" value={password} onChange={e=>setPassword(e.target.value)} />
      <button disabled={loading} onClick={onLogin} className="w-full px-4 py-2 rounded bg-violet-600 text-white">
        {loading ? "로그인 중..." : "로그인"}
      </button>
      {msg && <p className="text-sm mt-3">{msg}</p>}
      <p className="text-sm text-slate-500 mt-3">계정이 없으신가요? <a className="underline" href="/auth/signup">회원가입</a></p>
    </div>
  );
}
