import { authHeaders } from "./auth";
import type { ClassSkill, Cohort, CompareRow, Consent, Course, FamilyStat, Focus, GapRow, NetworkSummary, ObsMeta, ObsSeriesOut, Period, Progress, Report, ReviewList, ReviewSample, SessionState, StartOut } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init.headers ?? {}) },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return (await res.json()) as T;
}

/** Reintenta solo errores de red; la API es idempotente, así que repetir una respuesta no la duplica. */
async function withRetry<T>(fn: () => Promise<T>, tries = 3): Promise<T> {
  let last: unknown;
  for (let i = 0; i < tries; i++) {
    try { return await fn(); } catch (e) {
      if (e instanceof ApiError) throw e;
      last = e;
      await new Promise((r) => setTimeout(r, 400 * (i + 1)));
    }
  }
  throw last;
}

const q = (params: Record<string, string | undefined>) => {
  const entries = Object.entries(params).filter(([, v]) => v) as [string, string][];
  return entries.length ? "?" + new URLSearchParams(entries).toString() : "";
};

export async function downloadCsv(course?: string): Promise<void> {
  const res = await fetch(`${BASE}/v1/teacher/export.csv${q({ course })}`, { headers: authHeaders() });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url; a.download = "resumen.csv"; a.click();
  URL.revokeObjectURL(url);
}

export const api = {
  start: (mode: "practica" | "medicion" | "dirigida", skill?: string) =>
    withRetry(() => req<StartOut>("/v1/sessions", { method: "POST", body: JSON.stringify({ mode, skill }) })),
  hint: (sid: string, itemId: string, level: number) =>
    req<{ level: number; hint: string }>(`/v1/sessions/${sid}/hint${q({ item_id: itemId, level: String(level) })}`),
  progress: () => req<Progress>("/v1/me/progress"),
  deleteMyData: () => req<{ sessions: number; responses: number }>("/v1/me/data", { method: "DELETE" }),
  courses: () => req<{ courses: Course[] }>("/v1/teacher/courses"),
  errors: (course?: string) => req<{ errors: Record<string, number> }>(`/v1/teacher/errors${q({ course })}`),
  skills: (course?: string) => req<{ skills: ClassSkill[] }>(`/v1/teacher/skills${q({ course })}`),
  itemAnalysis: () => req<{ templates: FamilyStat[] }>("/v1/teacher/item-analysis"),
  trends: (course?: string) => req<{ periods: Period[]; baseline_level: number; note: string }>(`/v1/teacher/trends${q({ course })}`),
  obsMeta: () => req<ObsMeta>("/v1/observatory/meta"),
  obsSeries: (domain: string, entities: string[]) => req<ObsSeriesOut>(`/v1/observatory/series${q({ domain, entities: entities.join(",") })}`),
  obsCompare: (domain: string, cycle: number) => req<{ rows: CompareRow[] }>(`/v1/observatory/compare${q({ domain, cycle: String(cycle) })}`),
  obsGaps: (entity: string, domain: string) => req<{ has_data: boolean; rows: GapRow[] }>(`/v1/observatory/gaps${q({ entity, domain })}`),
  obsFocus: (entity: string) => req<Focus>(`/v1/observatory/focus${q({ entity })}`),
  networkSummary: () => req<NetworkSummary>("/v1/network/summary"),
  networkAdd: (tenant: string) => req<{ tenants: string[] }>("/v1/network/tenants", { method: "POST", body: JSON.stringify({ token: tenant }) }),
  consent: () => req<Consent>("/v1/teacher/consent"),
  attestConsent: () => req<Consent>("/v1/teacher/consent", { method: "POST" }),
  items: (sid: string) => req<SessionState>(`/v1/sessions/${sid}/items`),
  answer: (sid: string, itemId: string, response: string, durationS: number) =>
    withRetry(() => req<SessionState>(`/v1/sessions/${sid}/answers`, {
      method: "POST",
      body: JSON.stringify({ item_id: itemId, response, duration_s: durationS }),
    })),
  report: (sid: string) => req<Report>(`/v1/sessions/${sid}/report`),
  cohort: (course?: string) => req<Cohort>(`/v1/teacher/cohort${q({ course })}`),
  reviewList: () => req<ReviewList>("/v1/review/templates"),
  reviewSample: (tid: string) => req<ReviewSample>(`/v1/review/templates/${tid}/sample?n=5`),
  reviewSubmit: (tid: string, decision: "aprobar" | "rechazar", comment: string, checklist: Record<string, boolean>) =>
    req<{ status: string }>(`/v1/review/templates/${tid}`, { method: "POST", body: JSON.stringify({ decision, comment, checklist }) }),
  exchange: (token: string) =>
    req<{ access_token: string; role: "student" | "teacher" }>("/v1/lti/exchange", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
};

export function messageFor(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401) return "Tu sesión venció. Volvé a ingresar.";
    if (e.status === 403) return e.message || "Tu usuario no tiene permiso para esta pantalla.";
    if (e.status === 409 || e.status === 429) return e.message;
    return e.message || "Algo salió mal. Probá de nuevo.";
  }
  return "No pudimos conectar con el servidor. Revisá tu conexión y probá de nuevo.";
}
