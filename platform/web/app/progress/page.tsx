"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { MultiLineChart } from "@/components/MultiLineChart";
import { api, messageFor } from "@/lib/api";
import { clearAuth, getAuth } from "@/lib/auth";
import type { Progress } from "@/lib/types";

const MODE = { practica: "Práctica de 24 preguntas", medicion: "Medición", dirigida: "Práctica por tema", piloto: "Actividad de calibración" } as Record<string, string>;

export default function ProgressPage() {
  const router = useRouter();
  const [data, setData] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuth()) { router.replace("/"); return; }
    api.progress().then(setData).catch((e) => setError(messageFor(e)));
  }, [router]);

  const wipe = async () => {
    if (!window.confirm("Se van a borrar todas tus prácticas y respuestas de esta escuela. No se puede deshacer. ¿Querés continuar?")) return;
    try { await api.deleteMyData(); clearAuth(); router.replace("/"); } catch (e) { setError(messageFor(e)); }
  };

  return (
    <Shell>
      <section className="sheet">
        <h1>Mi progreso</h1>
        {error && <p className="error" role="alert">{error}</p>}
        {data && data.responses === 0 && <p className="lead">Todavía no practicaste. Empezá con una práctica de 24 preguntas para que podamos recomendarte temas.</p>}

        {data && data.recommended.length > 0 && (
          <>
            <h2>Qué practicar hoy</h2>
            <ul className="recs">
              {data.recommended.map((r) => (
                <li key={r.skill}>
                  <span><strong>{r.name}</strong> <span className="tagline">{r.reason}</span></span>
                  <Link className="btn small" href={`/practice?skill=${r.skill}`}>Practicar</Link>
                </li>
              ))}
            </ul>
          </>
        )}

        {data && (
          <>
            <h2>Mis temas</h2>
            <ul className="skills">
              {data.mastery.map((m) => (
                <li key={m.skill}>
                  <span className="skill-name">{m.name}</span>
                  <span className="bar-track" role="img" aria-label={m.p_known === null ? "sin práctica" : `dominio estimado ${Math.round(m.p_known * 100)} por ciento`}>
                    <span className="bar-fill" style={{ width: `${(m.p_known ?? 0) * 100}%` }} />
                  </span>
                  <span className="count">{m.p_known === null ? "—" : `${Math.round(m.p_known * 100)} %`}</span>
                  <Link className="small-link" href={`/practice?skill=${m.skill}`}>Practicar</Link>
                </li>
              ))}
            </ul>
            <p className="muted">El dominio es una estimación que se ajusta con tus respuestas sin pistas. Con pocas respuestas puede variar mucho.</p>

            {(() => {
              const done = data.sessions.filter((x) => x.level !== null && x.finished_at && x.mode !== "dirigida").reverse();
              return done.length >= 2 ? (
                <>
                  <h2>Mi evolución</h2>
                  <MultiLineChart title="Nivel en cada práctica de 24 preguntas" xLabel="Práctica" yLabel="Nivel (1 a 8)" yDomain={[1, 8]}
                    categories={done.map((x) => (x.finished_at ?? "").slice(0, 10))}
                    series={[{ name: "Mi nivel", color: "#1F4FD8", bold: true, points: done.map((x, i) => [i, x.level as number] as [number, number]) }]}
                    note="Los niveles son provisorios. Una subida o bajada de un nivel puede ser solo variación normal." />
                </>
              ) : null;
            })()}

            <h2>Mis prácticas</h2>
            {data.sessions.length === 0 ? <p>Todavía no hay prácticas.</p> : (
              <ul className="history">{data.sessions.map((s) => (
                <li key={s.id}>{MODE[s.mode] ?? s.mode}{s.level ? ` · nivel N${s.level}` : ""}{s.finished_at ? "" : " · sin terminar"}
                  {s.finished_at && <> · <Link href={`/report/${s.id}`}>ver resultado</Link></>}</li>
              ))}</ul>
            )}

            <h2>Mis datos</h2>
            <p>Tus respuestas se guardan con un código y no con tu nombre. Si querés, podés borrarlas.</p>
            <div className="actions"><button className="btn ghost" type="button" onClick={wipe}>Borrar mis datos</button></div>
          </>
        )}
        <div className="actions"><Link className="btn" href="/practice">Hacer una práctica de 24 preguntas</Link></div>
      </section>
    </Shell>
  );
}
