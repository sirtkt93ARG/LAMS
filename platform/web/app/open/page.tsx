"use client";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, messageFor } from "@/lib/api";
import { Stimulus } from "@/components/Stimulus";
import type { OpenAssignment } from "@/lib/types";

export default function OpenAssignmentsPage() {
  const [assignments, setAssignments] = useState<OpenAssignment[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = async () => { const out = await api.studentOpenAssignments(); setAssignments(out.assignments); };
  useEffect(() => { load().catch((e) => setError(messageFor(e))); }, []);
  const submit = async (id: string) => {
    setBusy(id); setError(""); setNotice("");
    try { await api.submitOpenResponse(id, drafts[id] ?? ""); await load(); setNotice("Tu respuesta fue entregada. El docente podrá corregirla."); }
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
      {a.status === "corregida" ? <div className="notice">
        <p><strong>Calificación: {a.score}/100</strong></p><p>{a.feedback}</p>
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
      </div> : a.submission_id ? <p className="muted">Entrega enviada. Está pendiente de corrección docente.</p> : a.expired ? <p className="error" role="status">El plazo de esta actividad venció. Ya no se aceptan nuevas entregas.</p> : <>
        <label className="field"><span>Tu desarrollo</span><textarea rows={7} maxLength={20000} value={drafts[a.id] ?? ""} onChange={(e) => setDrafts((old) => ({ ...old, [a.id]: e.target.value }))} /></label>
        <button className="btn" type="button" disabled={busy === a.id || !(drafts[a.id] ?? "").trim()} onClick={() => submit(a.id)}>Entregar respuesta</button>
      </>}
    </article>)}
  </section></Shell>;
}
