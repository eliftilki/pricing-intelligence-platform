import type { UUID } from "@/lib/pricing-api";

export type AuthSession = {
  access_token: string;
  refresh_token?: string | null;
  user_id: UUID;
  company_id: UUID;
};

const SESSION_KEY = "feraset_auth_session";

export function getAuthSession(): AuthSession | null {
  if (typeof window === "undefined") return null;

  const rawSession = window.localStorage.getItem(SESSION_KEY);
  if (!rawSession) return null;

  try {
    return JSON.parse(rawSession) as AuthSession;
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function setAuthSession(session: AuthSession) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearAuthSession() {
  window.localStorage.removeItem(SESSION_KEY);
  window.localStorage.removeItem("pricing_auth_token");
}
