const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`API ${res.status}: ${msg}`);
  }
  return res.json() as Promise<T>;
}

export async function signup(email: string, password: string, region_code?: string, referrer_code?: string) {
  return api<{access:string}>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, region_code, referrer_code }),
  });
}

export async function login(email: string, password: string) {
  return api<{access:string}>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}
