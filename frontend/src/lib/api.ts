// frontend/src/lib/api.ts
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// ✅ fetch wrapper
type ApiOptions = { method?: string; headers?: Record<string, string>; body?: any };
async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const body: string | undefined =
    options.body && typeof options.body !== "string"
      ? JSON.stringify(options.body)
      : options.body;

  const res = await fetch(`${BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${text}`);
  }

  return res.json();
}

// ✅ 회원가입 (백엔드: username 필수, referral_code/center_id 선택)
export async function signup(body: {
  email: string;
  password: string;
  username: string;
  referral_code?: string;
  center_id?: number;
}) {
  return api<{ message: string; user_id: number; referral_code: string }>("/auth/signup", {
    method: "POST",
    body,
  });
}

// ✅ 로그인
export async function login(email: string, password: string) {
  return api<{ access: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

// ✅ 입금요청 생성 (백엔드 허용: TRC20, ERC20, BSC, Polygon)
export async function createDepositRequest(params: {
  token: string;
  chain: "TRC20" | "ERC20" | "BSC" | "Polygon";
  amount_usdt: number;
}) {
  return api<{
    id: number;
    chain: string;
    assigned_address: string;
    expected_amount: number;
    status: string;
    created_at: string;
  }>("/deposits/request", {
    method: "POST",
    headers: { Authorization: `Bearer ${params.token}` },
    body: { chain: params.chain, amount_usdt: params.amount_usdt },
  });
}

// ✅ 내 입금내역
export async function getMyDeposits(token: string) {
  return api<{ items: Array<any> }>("/deposits/my", {
    headers: { Authorization: `Bearer ${token}` },
  });
}
