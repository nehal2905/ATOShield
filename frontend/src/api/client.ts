import type {
  Alert,
  CurrentUser,
  ScoredEvent,
  SimulateInput,
  SimulateResult,
  Stats,
} from "./types";

// Same-origin in prod (NGINX) and dev (Vite proxy). Cookies carry the JWT, so
// every request includes credentials. No tokens in JS-accessible storage.
const BASE = "/api";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (username: string, password: string) =>
    req<{ access_token: string; username: string; role: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => req<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  me: () => req<CurrentUser>("/auth/me"),
  register: (username: string, password: string, role = "analyst") =>
    req<CurrentUser>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, role }),
    }),

  events: (limit = 30) => req<ScoredEvent[]>(`/events?limit=${limit}`),
  postEvent: (e: Partial<ScoredEvent> & { user: string; ip: string; device_fp: string; geo_lat: number; geo_lon: number }) =>
    req<ScoredEvent>("/events", { method: "POST", body: JSON.stringify(e) }),

  simulate: (input: SimulateInput) =>
    req<SimulateResult>("/simulate", { method: "POST", body: JSON.stringify(input) }),

  alerts: (status?: string) =>
    req<Alert[]>(`/alerts${status ? `?status=${status}` : ""}`),
  updateAlert: (id: number, status: "open" | "ack" | "closed") =>
    req<Alert>(`/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),

  stats: () => req<Stats>("/stats"),
};

export { ApiError };
