"use client";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, messageFor } from "@/lib/api";
import type { Course, OpenAssignment, OpenItem, OpenSubmission, RubricCriterion } from "@/lib/types";

const fallbackCriteria: RubricCriterion[] = ["Comprensión", "Estrategia", "Procedimiento", "Argumentación"].map((label) => ({ id: label, label, descriptors: {} }));

export default function OpenReviewPage() {
  const [items, setItems] = useState<OpenItem[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [selectedCompetency, setSelectedCompetency] = useState("");
  const [assignments, setAssignments] = useState<OpenAssignment[]>([]);
  const [selected, setSelected] = useState("");
  const [submissions, setSubmissions] = useState<OpenSubmission[]>([]);
  const [active, setActive] = useState<OpenSubmission | null>(null);
  const [historyFor, setHistoryFor] = useState<string | null>(null);
  const [history, setHistory] = useState<OpenSubmission[]>([]);
  const [cancelConfirm, setCancelConfirm] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [itemId, setItemId] = useState("");
  const [score, setScore] = useState("0");
  const [feedback, setFeedback] = useState("");
  const [rubric, setRubric] = useState<Record<string, number>>({ Comprensión: 0, Estrategia: 0, Procedimiento: 0, Argumentación: 0 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadAssignments = async () => {
    const [catalog, list, courseList] = await Promise.all([
      api.openItems(), api.teacherOpenAssignments(), api.courses(),
    ]);
    setItems(catalog.items);
    setAssignments(list.assignments);
    setCourses(courseList.courses);
    if (!itemId && catalog.items.length) {
      setItemId(catalog.items[0].id);
      setSelectedCompetency(catalog.items[0].competencies?.[0]?.id ?? "");
    }
  };
  const loadSubmissions = async (id: string) => {
    const out = await api.openSubmissions(id); setSubmissions(out.submissions);
  };
  useEffect(() => { loadAssignments().catch((e) => setError(messageFor(e))); }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      await api.createOpenAssignment({
        item_id: itemId, title, instructions,
        ...(selectedCourse ? { course_id: selectedCourse } : {}),
        ...(selectedCompetency ? { competency_id: selectedCompetency } : {}),
        ...(dueAt ? { due_at: new Date(dueAt).toISOString() } : {}),
      });
      setTitle(""); setInstructions(""); setDueAt(""); await loadAssignments();
      setNotice(selectedCourse ? "Actividad asignada al curso correctamente." : "Actividad asignada a toda la escuela correctamente.");
    } catch (e) { setError(messageFor(e)); } finally { setBusy(false); }
  };
  const choose = async (id: string) => {
    setSelected(id); setActive(null); setHistoryFor(null); setHistory([]); setError("");
    try { await loadSubmissions(id); } catch (e) { setError(messageFor(e)); }
  };
  const cancelAssignment = async (id: string) => {
    setBusy(true); setError(""); setNotice("");
    try {
      await api.cancelOpenAssignment(id, cancelReason);
      setCancelConfirm(null); setCancelReason("");
      await loadAssignments();
      if (selected === id) await loadSubmissions(id);
      setNotice("Actividad cancelada. Las entregas y correcciones existentes se conservaron.");
    } catch (e) { setError(messageFor(e)); } finally { setBusy(false); }
  };
  const showHistory = async (submission: OpenSubmission) => {
    if (historyFor === submission.id) { setHistoryFor(null); return; }
    setBusy(true); setError("");
    try {
      const out = await api.teacherSubmissionHistory(submission.id);
      setHistory(out.attempts); setHistoryFor(submission.id);
    } catch (e) { setError(messageFor(e)); } finally { setBusy(false); }
  };
  const startGrade = (submission: OpenSubmission) => {
    setActive(submission); setScore(String(submission.score ?? 0)); setFeedback(submission.feedback ?? "");
    const criteria = submission.rubric_snapshot?.criteria ?? fallbackCriteria;
    setRubric(submission.rubric ?? Object.fromEntries(criteria.map((criterion) => [criterion.id, 0])));
  };
  const grade = async (e: React.FormEvent) => {
    e.preventDefault(); if (!active) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await api.gradeOpenSubmission(active.id, Number(score), feedback, rubric);
      setActive(null); await loadSubmissions(selected); await loadAssignments();
      setNotice("Corrección guardada y devolución disponible para el estudiante.");
    } catch (e) { setError(messageFor(e)); } finally { setBusy(false); }
  };

  const selectedItem = items.find((item) => item.id === itemId);
  const selectedRubric = selectedItem?.competencies?.find((entry) => entry.id === selectedCompetency)?.rubric;

  return <Shell><section className="sheet">
    <h1>Corrección de respuestas abiertas</h1>
    <p className="lead">Asigná una consigna, leé las entregas y devolvé una calificación con criterios y comentarios.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p className="ok" role="status">{notice}</p>}
    <h2>Crear actividad</h2>
    {items.length === 0 ? <p>No hay preguntas abiertas disponibles en el banco actual.</p> : <form onSubmit={create}>
      <label className="field"><span>Consigna del banco</span>
        <select value={itemId} onChange={(e) => {
          const next = items.find((item) => item.id === e.target.value);
          setItemId(e.target.value); setSelectedCompetency(next?.competencies?.[0]?.id ?? "");
        }}>{items.map((item) => <option key={item.id} value={item.id}>{item.stem.slice(0, 110)}</option>)}</select>
      </label>
      {selectedItem?.competencies?.length ? <>
        <label className="field"><span>Competencia que se evaluará</span>
          <select value={selectedCompetency} onChange={(e) => setSelectedCompetency(e.target.value)}>
            {selectedItem.competencies.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}
          </select>
        </label>
        {selectedRubric && <details className="notice"><summary>Ver rúbrica: {selectedRubric.competency}</summary>
          <p>{selectedRubric.focus}</p>
          {selectedRubric.criteria.map((criterion) => <div key={criterion.id}>
            <strong>{criterion.label}</strong>
            <ul>{Object.entries(criterion.descriptors ?? {}).map(([level, descriptor]) => <li key={level}>{level}/4 — {descriptor}</li>)}</ul>
          </div>)}
          <p className="muted">{selectedRubric.notice}</p>
        </details>}
      </> : <p className="muted">Esta plantilla no tiene una competencia vinculada en el mapa del banco; se usará la corrección orientativa general.</p>}
      <label className="field"><span>Curso destinatario</span>
        <select value={selectedCourse} onChange={(e) => setSelectedCourse(e.target.value)}>
          <option value="">Toda la escuela (sin curso específico)</option>
          {courses.map((course) => <option key={course.course_id} value={course.course_id}>{course.course_label || course.course_id}</option>)}
        </select>
      </label>
      {courses.length === 0 && <p className="muted">No hay cursos registrados en esta sesión. La actividad se asignará a toda la escuela.</p>}
      <label className="field"><span>Título de la actividad</span><input value={title} maxLength={160} onChange={(e) => setTitle(e.target.value)} required /></label>
      <label className="field"><span>Indicaciones para el estudiante</span><textarea value={instructions} maxLength={4000} rows={3} onChange={(e) => setInstructions(e.target.value)} /></label>
      <label className="field"><span>Fecha y hora límite (opcional)</span><input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} /></label>
      <button className="btn" type="submit" disabled={busy || !itemId || !title.trim()}>Asignar actividad</button>
    </form>}
    <h2>Actividades y entregas</h2>
    {assignments.length === 0 ? <p>Todavía no creaste actividades abiertas.</p> : <ul>
      {assignments.map((a) => <li key={a.id}>
        <button className="btn ghost" type="button" onClick={() => choose(a.id)} aria-pressed={selected === a.id}>{a.title} — {a.pending ?? 0} pendientes / {a.submissions ?? 0} entregas</button>
        {a.competency_id && <p className="muted">Competencia: {a.rubric_snapshot?.competency ?? a.competency_id}</p>}
        {a.due_at && <p className="muted">Vence: {new Date(a.due_at).toLocaleString()}</p>}
        {a.cancelled ? <p className="error" role="status">Cancelada{a.cancellation_reason ? `: ${a.cancellation_reason}` : ""}</p> : cancelConfirm === a.id ? <>
          <label className="field"><span>Motivo de cancelación (opcional)</span>
            <input value={cancelReason} maxLength={1000} onChange={(e) => setCancelReason(e.target.value)} />
          </label>
          <button className="btn" type="button" disabled={busy} onClick={() => cancelAssignment(a.id)}>Confirmar cancelación</button>
          <button className="btn ghost" type="button" onClick={() => { setCancelConfirm(null); setCancelReason(""); }}>Volver</button>
        </> : <button className="btn ghost" type="button" onClick={() => setCancelConfirm(a.id)}>Cancelar actividad</button>}
      </li>)}
    </ul>}
    {selected && <><h2>Entregas</h2>
      {submissions.length === 0 ? <p>Aún no hay entregas para esta actividad.</p> : <ul>
        {submissions.map((s) => <li key={s.id}>
          <p><strong>{s.student_name ?? s.student_label}</strong> · Intento {s.attempt_number} · {s.status === "pendiente" ? "Pendiente" : `Corregida · ${s.score}/100`}</p>
          <blockquote>{s.response}</blockquote>
          {s.status === "pendiente" && <button className="btn" type="button" onClick={() => startGrade(s)}>Corregir entrega</button>}
          {s.status === "corregida" && <p className="muted">{s.feedback}</p>}
          <button className="btn ghost" type="button" disabled={busy} onClick={() => showHistory(s)}>
            {historyFor === s.id ? "Ocultar historial" : "Ver historial"}
          </button>
          {historyFor === s.id && <div className="notice">
            <h3>Intentos anteriores</h3>
            <ol>{history.map((attempt) => <li key={attempt.id}>
              <p><strong>Intento {attempt.attempt_number} · {new Date(attempt.submitted_at).toLocaleString()}</strong></p>
              <p>{attempt.response}</p>
              {attempt.status === "corregida" ? <p>{attempt.score}/100 · {attempt.feedback}</p> : <p className="muted">Pendiente de corrección</p>}
            </li>)}</ol>
          </div>}
        </li>)}
      </ul>}
    </>}
    {active && <form onSubmit={grade}>
      <h2>Devolución para {active.student_label}</h2>
      <blockquote>{active.response}</blockquote>
      <label className="field"><span>Calificación (0 a 100)</span><input type="number" min="0" max="100" step="1" value={score} onChange={(e) => setScore(e.target.value)} required /></label>
      <h3>Rúbrica orientativa (0 a 4)</h3>
      {(active.rubric_snapshot?.criteria ?? fallbackCriteria).map((criterion) => <label className="field" key={criterion.id}><span>{criterion.label}</span>
        <select value={rubric[criterion.id] ?? 0} onChange={(e) => setRubric((old) => ({ ...old, [criterion.id]: Number(e.target.value) }))}>
          {[0,1,2,3,4].map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        {criterion.descriptors && <p className="muted">{criterion.descriptors[String(rubric[criterion.id] ?? 0)]}</p>}
      </label>)}
      {active.rubric_snapshot && <p className="muted">{active.rubric_snapshot.notice}</p>}
      <label className="field"><span>Retroalimentación</span><textarea rows={5} maxLength={10000} value={feedback} onChange={(e) => setFeedback(e.target.value)} /></label>
      <div className="actions"><button className="btn" type="submit" disabled={busy}>Guardar corrección</button>
        <button className="btn ghost" type="button" onClick={() => setActive(null)}>Cancelar</button></div>
    </form>}
  </section></Shell>;
}
