"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Shell } from "@/components/Shell";
import { ItemView } from "@/components/ItemView";
import { Explanation } from "@/components/Explanation";
import { Progress } from "@/components/Progress";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import type { SessionState } from "@/lib/types";

const SID_KEY = "matheval.sid";
type Feedback = { correct: boolean; next: SessionState; explanation?: string[] };

function Practice() {
  const router = useRouter();
  const skill = useSearchParams().get("skill");
  const [sid, setSid] = useState<string | null>(null);
  const [state, setState] = useState<SessionState | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const shownAt = useRef(Date.now());

  useEffect(() => {
    if (!getAuth()) { router.replace("/"); return; }
    const saved = window.sessionStorage.getItem(SID_KEY);
    if (!saved) return;
    api.items(saved)
      .then((s) => { if (s.done) router.replace(`/report/${saved}`); else { setSid(saved); setState(s); shownAt.current = Date.now(); } })
      .catch(() => window.sessionStorage.removeItem(SID_KEY));
  }, [router]);

  const begin = async () => {
    setBusy(true); setError(null);
    try {
      const out = await api.start(skill ? "dirigida" : "practica", skill ?? undefined);
      window.sessionStorage.setItem(SID_KEY, out.session_id);
      setSid(out.session_id); setState(out); shownAt.current = Date.now();
    } catch (e) { setError(messageFor(e)); } finally { setBusy(false); }
  };

  const send = async (response: string) => {
    if (!sid || !state || !state.items[0]) return;
    setBusy(true); setError(null);
    try {
      const out = await api.answer(sid, state.items[0].id, response, (Date.now() - shownAt.current) / 1000);
      setFeedback({ correct: out.correct ?? false, next: out, explanation: out.explanation });
    } catch (e) { setError(messageFor(e)); } finally { setBusy(false); }
  };

  const next = () => {
    if (!feedback || !sid) return;
    if (feedback.next.done) { window.sessionStorage.removeItem(SID_KEY); router.push(`/report/${sid}`); return; }
    setState(feedback.next); setFeedback(null); shownAt.current = Date.now();
  };

  const directed = state?.mode === "dirigida";

  return (
    <>
      {!state && (
        <section className="sheet">
          <h1>{skill ? "Práctica por tema" : "Práctica de matemática"}</h1>
          {skill ? (
            <p className="lead">Diez ejercicios que se ajustan a cómo vas respondiendo. Podés pedir pistas, y si te equivocás vas a ver cómo se resuelve y te damos otro parecido para practicar.</p>
          ) : (
            <p className="lead">24 preguntas, sin tiempo límite. Después de cada respuesta te avisamos si fue correcta. Al final ves tu nivel.</p>
          )}
          <div className="actions">
            <button className="btn" type="button" onClick={begin} disabled={busy}>{skill ? "Empezar la práctica por tema" : "Empezar práctica de 24 preguntas"}</button>
            <Link className="btn ghost" href="/progress">{skill ? "Elegir otro tema" : "Practicar un tema / ver mi progreso"}</Link>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
        </section>
      )}

      {state && state.items[0] && !feedback && (
        <>
          <Progress answered={state.answered} total={state.total} />
          <ItemView item={state.items[0]} busy={busy} onSubmit={send}
            onHint={directed && sid ? (level) => api.hint(sid, state.items[0].id, level).then((r) => r.hint) : undefined} />
          {error && <p className="error" role="alert">{error}</p>}
        </>
      )}

      {state && feedback && (
        <section className="sheet" aria-live="polite">
          <h2 className={feedback.correct ? "ok" : "retry"}>{feedback.correct ? "Respuesta correcta" : "Esta vez no fue correcta"}</h2>
          {feedback.explanation
            ? <Explanation steps={feedback.explanation} />
            : <p className="lead">{feedback.correct ? "Seguí con la próxima." : "No te mostramos la solución todavía: al final vas a ver qué conviene repasar."}</p>}
          {directed && !feedback.correct && !feedback.next.done && <p>Ahora te damos otro ejercicio parecido para que lo intentes de nuevo.</p>}
          <div className="actions">
            <button className="btn" type="button" onClick={next} autoFocus>{feedback.next.done ? "Ver mi resultado" : "Siguiente pregunta"}</button>
          </div>
        </section>
      )}
    </>
  );
}

export default function PracticePage() {
  return <Shell><Suspense fallback={null}><Practice /></Suspense></Shell>;
}
