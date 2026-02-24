// frontend/src/lib/api.ts
import { getApiBaseUrl } from "./apiBase";

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

  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
    credentials: "include", // HttpOnly 쿠키 인증 방식 통일
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
  wallet_address: string;
  referral_code?: string;
  center_id?: number;
  sector_id?: number;
  terms_accepted?: boolean;
  risk_accepted?: boolean;
  privacy_accepted?: boolean;
  legal_version?: string;
  locale?: "ko" | "en";
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
    // credentials: 'include'는 api() 내부에서 처리됨
  });
}

// 입금요청 생성 (쿠키 인증 방식)
export async function createDepositRequest(params: {
  chain: "Polygon" | "Ethereum" | "TRON";
  amount_usdt: number;
}) {
  return api<{
    id: number;
    chain: string;
    assigned_address: string;
    expected_amount: number;
    joy_amount: number;
    status: string;
    created_at: string;
  }>("/deposits/request", {
    method: "POST",
    body: {
      chain: params.chain,
      amount_usdt: params.amount_usdt,
    },
  });
}

// 내 입금내역 (쿠키 인증)
export async function getMyDeposits() {
  return api<{ items: Array<any> }>("/deposits/my");
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

// 내 정보 조회 (쿠키 인증)
export async function getMe() {
  return api<{
    id: number;
    email: string;
    username: string;
    referral_code: string;
    recovery_code: string;
    role: string;
    wallet_address: string | null;
    total_joy: number;
    total_points: number;
    referral_reward_remaining: number;
  }>("/auth/me");
}

// 알림 목록 (쿠키 인증)
export async function getNotifications() {
  return api<Array<{
    id: number;
    type: string;
    title: string;
    message: string;
    is_read: boolean;
    related_id: number | null;
    created_at: string;
  }>>("/notifications");
}

// 읽지 않은 알림 개수
export async function getUnreadNotificationCount() {
  return api<{ count: number }>("/notifications/unread-count");
}

// 알림 읽음 처리
export async function markNotificationAsRead(notificationId: number) {
  return api<{ message: string }>(`/notifications/${notificationId}/read`, { method: "POST" });
}

// 모든 알림 읽음 처리
export async function markAllNotificationsAsRead() {
  return api<{ message: string }>("/notifications/read-all", { method: "POST" });
}

// ===== 관리자 API (쿠키 인증) =====

// 입금 목록 (관리자)
export async function getAdminDeposits(status?: string) {
  const query = status ? `?status=${status}` : "";
  return api<Array<any>>(`/admin/deposits${query}`);
}

// 입금 승인 (관리자)
export async function approveDeposit(depositId: number, data?: { actual_amount?: number; admin_notes?: string }) {
  return api<{ message: string; id: number }>(`/admin/deposits/${depositId}/approve`, {
    method: "POST",
    body: data || {},
  });
}

// 입금 거부 (관리자)
export async function rejectDeposit(depositId: number, notes?: string) {
  return api<{ message: string; id: number }>(`/admin/deposits/${depositId}/reject`, {
    method: "POST",
    body: { admin_notes: notes },
  });
}
