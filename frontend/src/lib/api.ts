// frontend/src/lib/api.ts
const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

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

// ✅ 회원가입
export async function signup(
  email: string,
  password: string,
  region_code?: string,
  referrer_code?: string
) {
  return api<{ access: string }>("/auth/signup", {
    method: "POST",
    body: { email, password, region_code, referrer_code },
  });
}

// ✅ 로그인
export async function login(email: string, password: string) {
  return api<{ access: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

// ✅ 입금요청 생성
export async function createDepositRequest(params: {
  token: string;
  chain: "TRON" | "ETH";
  amount_usdt: number;
}) {
  return api<{
    id: number;
    chain: string;
    assigned_address: string;
    expected_amount: string;
    reference_code: string;
    status: string;
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
