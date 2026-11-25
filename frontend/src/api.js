const BASE = import.meta.env.VITE_API_URL || "";
export const tokenStore = {
  get: () => localStorage.getItem("rs_token"),
  set: (t) => localStorage.setItem("rs_token", t),
  clear: () => localStorage.removeItem("rs_token"),
};

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : detail?.message || "Request failed");
    this.status = status; this.detail = detail;
  }
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const t = tokenStore.get();
  if (t) headers.Authorization = `Bearer ${t}`;
  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError(0, "Cannot reach the RoomSync server. Is the backend running?");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let d = data.detail;
    if (Array.isArray(d)) d = d.map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`).join("; ");
    throw new ApiError(res.status, d || res.statusText);
  }
  return data;
}

export const login = (email, password) => api("/api/auth/login", { method: "POST", body: { email, password } });
export const signup = (name, email, password) => api("/api/auth/signup", { method: "POST", body: { name, email, password } });
