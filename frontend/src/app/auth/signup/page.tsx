"use client";
import { useState } from "react";
import { signup } from "@/lib/api";

export default function SignupPage() {
  const [email, setEmail] = useState(""); 
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [region, setRegion] = useState("");
  const [ref, setRef] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSignup = async () => {
    if (password.length < 12) { setMsg("비밀번호는 12자 이상이어야 합니다."); return; }
    if (password !== confirm) { setMsg("비밀번호가 일치하지 않습니다."); return; }
    setLoading(true); setMsg(null);
    try {
      const res = await signup(email, password, region || undefined, ref || undefined);
      localStorage.setItem("access", res.access);
      setMsg("회원가입 성공!");
    } catch (e:any) {
      setMsg(e.message);
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-md mx-auto bg-white border rounded-xl p-6">
      <h2 className="text-xl font-bold mb-4">회원가입</h2>
      <label className="block text-sm mb-1">이메일</label>
      <input className="w-full border rounded p-2 mb-3" value={email} onChange={e=>setEmail(e.target.value)} />
      <label className="block text-sm mb-1">비밀번호</label>
      <input type="password" className="w-full border rounded p-2 mb-3" value={password} onChange={e=>setPassword(e.target.value)} />
      <label className="block text-sm mb-1">비밀번호 확인</label>
      <input type="password" className="w-full border rounded p-2 mb-4" value={confirm} onChange={e=>setConfirm(e.target.value)} />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm mb-1">지역 코드(선택)</label>
          <input className="w-full border rounded p-2" value={region} onChange={e=>setRegion(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm mb-1">추천 코드(선택)</label>
          <input className="w-full border rounded p-2" value={ref} onChange={e=>setRef(e.target.value)} />
        </div>
      </div>
      <button disabled={loading} onClick={onSignup} className="w-full mt-4 px-4 py-2 rounded bg-violet-600 text-white">
        {loading ? "회원가입 중..." : "회원가입"}
      </button>
      {msg && <p className="text-sm mt-3">{msg}</p>}
    </div>
  );
}
