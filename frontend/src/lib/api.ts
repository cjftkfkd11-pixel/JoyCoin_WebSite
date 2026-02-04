// frontend/src/lib/api.ts
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// fetch wrapper
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

// 회원가입
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

// 로그인
export async function login(email: string, password: string) {
  return api<{ access: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

// 입금요청 생성
export async function createDepositRequest(params: {
  token: string;
  chain: "TRC20" | "ERC20" | "BSC" | "Polygon";
  amount_usdt: number;
  joy_amount: number;
  sender_name: string;
}) {
  return api<{
    id: number;
    chain: string;
    assigned_address: string;
    sender_name: string;
    expected_amount: number;
    joy_amount: number;
    status: string;
    created_at: string;
  }>("/deposits/request", {
    method: "POST",
    headers: { Authorization: `Bearer ${params.token}` },
    body: {
      chain: params.chain,
      amount_usdt: params.amount_usdt,
      joy_amount: params.joy_amount,
      sender_name: params.sender_name,
    },
  });
}

// 내 입금내역
export async function getMyDeposits(token: string) {
  return api<{ items: Array<any> }>("/deposits/my", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// 센터 목록
export async function getCenters() {
  return api<Array<{ id: number; name: string; region: string }>>("/centers");
}

// 상품 목록
export async function getProducts() {
  return api<Array<{
    id: number;
    name: string;
    joy_amount: number;
    price_usdt: number;
    price_krw: number;
    discount_rate: number;
  }>>("/products");
}

// 내 정보 조회
export async function getMe(token: string) {
  return api<{
    id: number;
    email: string;
    username: string;
    referral_code: string;
    role: string;
    center_id: number | null;
    total_joy: number;
    total_points: number;
    is_email_verified: boolean;
    created_at: string;
  }>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// 알림 목록
export async function getNotifications(token: string) {
  return api<Array<{
    id: number;
    type: string;
    title: string;
    message: string;
    is_read: boolean;
    related_id: number | null;
    created_at: string;
  }>>("/notifications", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// 읽지 않은 알림 개수
export async function getUnreadNotificationCount(token: string) {
  return api<{ count: number }>("/notifications/unread-count", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// 알림 읽음 처리
export async function markNotificationAsRead(token: string, notificationId: number) {
  return api<{ message: string }>(`/notifications/${notificationId}/read`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

// 모든 알림 읽음 처리
export async function markAllNotificationsAsRead(token: string) {
  return api<{ message: string }>("/notifications/read-all", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ===== 관리자 API =====

// 입금 목록 (관리자)
export async function getAdminDeposits(token: string, status?: string) {
  const query = status ? `?status=${status}` : "";
  return api<Array<any>>(`/admin/deposits${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// 입금 승인 (관리자)
export async function approveDeposit(token: string, depositId: number, data?: { actual_amount?: number; admin_notes?: string }) {
  return api<{ message: string; id: number }>(`/admin/deposits/${depositId}/approve`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: data || {},
  });
}

// 입금 거부 (관리자)
export async function rejectDeposit(token: string, depositId: number, notes?: string) {
  return api<{ message: string; id: number }>(`/admin/deposits/${depositId}/reject`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: { admin_notes: notes },
  });
}
