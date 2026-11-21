import type { Role } from "./types";

export type AuthState = { role: Role; token?: string; devUser?: string };

export function roleFromKeycloakRoles(roles: string[]): Role {
  return roles.includes("admin") ? "admin"
    : roles.includes("network") ? "network"
    : roles.includes("teacher") ? "teacher"
    : "student";
}
const KEY = "matheval.auth";

export function getAuth(): AuthState | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(KEY);
  return raw ? (JSON.parse(raw) as AuthState) : null;
}

export function setAuth(a: AuthState): void {
  window.sessionStorage.setItem(KEY, JSON.stringify(a));
}

export function clearAuth(): void {
  window.sessionStorage.removeItem(KEY);
  window.sessionStorage.removeItem("matheval.sid");
}

export function authHeaders(): Record<string, string> {
  const a = getAuth();
  if (!a) return {};
  if (a.token) return { Authorization: `Bearer ${a.token}` };
  if (a.devUser) return { "X-Dev-User": a.devUser };
  return {};
}

/** Ingreso de desarrollo: sub:tenant:rol (la API debe correr con MATHEVAL_DEV=1). */
export function devLogin(sub: string, tenant: string, role: Role): void {
  setAuth({ role, devUser: `${sub}:${tenant}:${role}` });
}

/** Ingreso con Keycloak (PKCE). El token se renueva solo mientras la pestaña siga abierta. */
export async function keycloakLogin(): Promise<Role> {
  const { default: Keycloak } = await import("keycloak-js");
  const kc = new Keycloak({
    url: process.env.NEXT_PUBLIC_KC_URL ?? "http://localhost:8080",
    realm: process.env.NEXT_PUBLIC_KC_REALM ?? "matheval",
    clientId: process.env.NEXT_PUBLIC_KC_CLIENT ?? "matheval-web",
  });
  const ok = await kc.init({ onLoad: "login-required", pkceMethod: "S256", checkLoginIframe: false });
  if (!ok || !kc.token) throw new Error("No se pudo iniciar sesión.");
  const roles: string[] = (kc.tokenParsed as { realm_access?: { roles?: string[] } } | undefined)?.realm_access?.roles ?? [];
  const role = roleFromKeycloakRoles(roles);
  setAuth({ role, token: kc.token });
  window.setInterval(() => {
    kc.updateToken(60).then((refreshed) => {
      if (refreshed && kc.token) setAuth({ role, token: kc.token });
    }).catch(() => clearAuth());
  }, 30_000);
  return role;
}
