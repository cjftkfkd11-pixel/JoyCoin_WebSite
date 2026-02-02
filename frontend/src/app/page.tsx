import Link from 'next/link';

export default function Page() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center space-y-12 px-6 py-20 relative min-h-[calc(100vh-80px)]">
      
      {/* 로고 섹션 */}
      <div className="text-center group">
        <h1 className="text-7xl md:text-[10rem] font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-yellow-400 via-red-500 to-blue-500 transition-all duration-1000 group-hover:scale-105 select-none drop-shadow-2xl">
          JOYCOIN
        </h1>
      </div>

      {/* 버튼 섹션 */}
      <div className="flex flex-col md:flex-row items-stretch gap-6 w-full max-w-3xl px-4">
        
        {/* 로그인 + 어드민 링크 묶음 */}
        <div className="flex-1 flex flex-col gap-3">
          <Link 
            href="/auth/login"
            className="h-24 flex items-center justify-center glass hover:bg-white/10 text-white font-black text-xl rounded-3xl transition-all border border-white/20 shadow-2xl"
          >
            로그인
          </Link>
          {/* 어드민 로그인: 연회색으로 아래 배치 */}
          <Link href="/admin/login" className="text-slate-500 hover:text-slate-400 text-[10px] font-bold uppercase tracking-widest text-center transition-colors">
            admin login
          </Link>
        </div>

        {/* 회원가입 버튼 */}
        <Link 
          href="/auth/signup"
          className="flex-1 h-24 flex items-center justify-center glass hover:bg-white/10 text-white font-black text-xl rounded-3xl transition-all border border-white/20 shadow-2xl"
        >
          회원가입
        </Link>

        {/* ACTIVATE JOYCOIN 버튼 */}
        <Link 
          href="/purchase"
          className="flex-1 h-24 flex items-center justify-center bg-gradient-to-br from-blue-500 to-indigo-700 hover:from-blue-400 hover:to-indigo-600 text-white font-black text-xl rounded-3xl shadow-2xl shadow-blue-500/40 transition-all text-center px-4 leading-tight"
        >
          ACTIVATE<br/>JOYCOIN
        </Link>
        
      </div>

      <div className="absolute bottom-12 opacity-30 animate-bounce">
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </div>
  );
}