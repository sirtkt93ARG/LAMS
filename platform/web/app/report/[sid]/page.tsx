"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { LevelLadder } from "@/components/LevelLadder";
import { Explanation } from "@/components/Explanation";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import { topAdvice } from "@/lib/tags";
import type { Report } from "@/lib/types";

const BASELINE = 4;

export default function ReportPage() {
  const { sid } = useParams<{ sid: string }>();
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuth()) { router.replace("/"); return; }
    api.report(sid).then(setReport).catch((e) => setError(messageFor(e)));
  }, [sid, router]);

  const advice = report ? topAdvice(report.error_tags) : [];

  return (
    <Shell>
      {error && <section className="sheet"><p className="error" role="alert">{error}</p></section>}

      {report?.kind === "dirigida" && (
        <section className="sheet">
          <h1>Práctica de {report.skill_name}</h1>
          <p className="lead">Resolviste bien {report.correct} de {report.answered} ejercicios.</p>
          {report.mistakes && report.mistakes.length > 0 && (
            <>
              <h2>Los que conviene mirar de nuevo</h2>
              {report.mistakes.map((m, i) => (
                <details key={i} className="mistake">
                  <summary>{m.stem}</summary>
                  <Explanation steps={m.steps} />
                </details>
              ))}
            </>
          )}
          <div className="actions">
            <Link className="btn" href="/progress">Ver mi progreso</Link>
            <Link className="btn ghost" href={`/practice?skill=${report.skill}`}>Practicar este tema otra vez</Link>
          </div>
        </section>
      )}

      {report && report.kind !== "dirigida" && (
        <section className="sheet">
          <h1>Tu resultado: nivel N{report.level}</h1>
          <p className="lead">{report.descriptor}.</p>
          <p>{report.at_or_above_baseline
            ? "Llegaste al nivel mínimo propuesto. Seguí practicando para pasar al siguiente."
            : `Todavía no llegaste al nivel mínimo propuesto (N${BASELINE}). Con práctica en los temas de abajo podés avanzar.`}</p>
          {report.preliminary && <p className="muted">{report.note}</p>}

          <h2>Dónde estás</h2>
          <LevelLadder ladder={report.ladder} level={report.level} baseline={BASELINE} />

          <h2>Qué conviene repasar</h2>
          {advice.length === 0
            ? <p>No se detectaron errores frecuentes en esta práctica.</p>
            : <ul className="advice">{advice.map(({ advice: a, count }) => (
                <li key={a.topic}><strong>{a.topic}</strong> ({count} {count === 1 ? "respuesta" : "respuestas"}): {a.advice}</li>
              ))}</ul>}

          <div className="actions">
            <Link className="btn" href="/progress">Practicar por tema</Link>
            <Link className="btn ghost" href="/practice">Hacer otra práctica de 24 preguntas</Link>
          </div>
        </section>
      )}
    </Shell>
  );
}
