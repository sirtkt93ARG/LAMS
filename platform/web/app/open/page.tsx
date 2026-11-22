"use client";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, messageFor } from "@/lib/api";
import { Stimulus } from "@/components/Stimulus";
import type { OpenAssignment, OpenSubmission } from "@/lib/types";

export default function OpenAssignmentsPage() {
  const [assignments, setAssignments] = useState<OpenAssignment[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [histories, setHistories] = useState<Record<string, OpenSubmission[]>>({});
  const [historyOpen, setHistoryOpen] = useState<string | null>(null);
  const load = async () => { const out = await api.studentOpenAssignments(); setAssignments(out.assignments); };
  useEffect(() => { load().catch((e) => setError(messageFor(e))); }, []);
  const toggleHistory = async (id: string) => {
    if (historyOpen === id) { setHistoryOpen(null); return; }
    setHistoryOpen(id);
    if (histories[id]) return;
    try {
      const out = await api.studentSubmissionHistory(id);
      setHistories((old) => ({ ...old, [id]: out.attempts }));
    } catch (e) { setError(messageFor(e)); }
  };
  const submit = async (id: string) => {
    setBusy(id); setError(""); setNotice("");
    try {
      await api.submitOpenResponse(id, drafts[id] ?? "");
      setDrafts((old) => ({ ...old, [id]: "" }));
      setHistories((old) => { const next = { ...old }; delete next[id]; return next; });
      await load();
      setNotice("Tu respuesta fue entregada. El docente podrá corregirla.");
    }
    catch (e) { setError(messageFor(e)); } finally { setBusy(null); }
  };
  return <Shell><section className="sheet">
    <h1>Actividades de respuesta abierta</h1>
    <p className="lead">Desarrollá tu razonamiento con tus propias palabras. El docente revisará tu entrega y te enviará una devolución.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p className="ok" role="status">{notice}</p>}
    {assignments.length === 0 && <p>No tenés actividades abiertas asignadas en este momento.</p>}
    {assignments.map((a) => <article key={a.id}>
      <h2>{a.title}</h2><p>{a.instructions}</p>
      {a.due_at && <p className="muted">Fecha límite: {new Date(a.due_at).toLocaleString()}{a.expired ? " · Plazo vencido" : ""}</p>}
      {a.item && <div className="notice"><p className="stem">{a.item.stem}</p><Stimulus s={a.item.stimulus} /></div>}
      {a.status === "corregida" && <div className="notice">
        <p><strong>Última calificación · intento {a.attempt_number ?? 1}: {a.score}/100</strong></p><p>{a.feedback}</p>
        {a.rubric_snapshot && a.rubric && <div>
          <h3>Devolución por competencia: {a.rubric_snapshot.competency}</h3>
          <p>{a.rubric_snapshot.focus}</p>
          <ul>{a.rubric_snapshot.criteria.map((criterion) => {
            const value = a.rubric?.[criterion.id] ?? 0;
            return <li key={criterion.id}><strong>{criterion.label}: {value}/4.</strong> {criterion.descriptors?.[String(value)]}</li>;
          })}</ul>
          <p className="muted">{a.rubric_snapshot.notice}</p>
        </div>}
        {!a.rubric_snapshot && a.rubric && <ul>{Object.entries(a.rubric).map(([criterion, value]) => <li key={criterion}>{criterion}: {value}/4</li>)}</ul>}
      </div>}
      {a.submission_id && <button className="btn ghost" type="button" onClick={() => toggleHistory(a.id)}>
        {historyOpen === a.id ? "Ocultar historial" : "Ver historial de intentos"}
      </button>}
      {historyOpen === a.id && <div className="notice">
        <h3>Historial de entregas</h3>
        {(histories[a.id] ?? []).length === 0 ? <p>No hay intentos anteriores.</p> : <ol>
          {(histories[a.id] ?? []).map((attempt) => <li key={attempt.id}>
            <p><strong>Intento {attempt.attempt_number} · {new Date(attempt.submitted_at).toLocaleString()}</strong></p>
            <p>{attempt.response}</p>
            {attempt.status === "corregida" ? <p>Calificación: {attempt.score}/100 · {attempt.feedback}</p> : <p className="muted">Pendiente de corrección</p>}
          </li>)}
        </ol>}
      </div>}
      {a.status === "pendiente" && <p className="muted">Intento {a.attempt_number ?? 1} entregado. Está pendiente de corrección docente; podrás volver a entregar después de recibir la devolución.</p>}
      {a.expired && <p className="error" role="status">El plazo venció. No se aceptan nuevos intentos.</p>}
      {!a.expired && a.status !== "pendiente" && <>
        <label className="field"><span>{a.status === "corregida" ? "Tu nuevo desarrollo" : "Tu desarrollo"}</span>
          <textarea rows={7} maxLength={20000} value={drafts[a.id] ?? ""} onChange={(e) => setDrafts((old) => ({ ...old, [a.id]: e.target.value }))} />
        </label>
        <button className="btn" type="button" disabled={busy === a.id || !(drafts[a.id] ?? "").trim()} onClick={() => submit(a.id)}>
          {a.status === "corregida" ? "Entregar nuevo intento" : "Entregar respuesta"}
        </button>
      </>}
    </article>)}
  </section></Shell>;
}
