"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { LevelBars } from "@/components/LevelBars";
import { MultiLineChart } from "@/components/MultiLineChart";
import { api, downloadCsv, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import { topAdvice } from "@/lib/tags";
import type { ClassSkill, Cohort, Consent, Course, Period } from "@/lib/types";

export default function TeacherPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);
  const [course, setCourse] = useState<string>("");
  const [data, setData] = useState<Cohort | null>(null);
  const [errors, setErrors] = useState<Record<string, number>>({});
  const [skills, setSkills] = useState<ClassSkill[]>([]);
  const [consent, setConsent] = useState<Consent | null>(null);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [invites, setInvites] = useState<string[]>([]);
  const [inviteBusy, setInviteBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = getAuth()?.role === "admin";

  const load = useCallback(async (c: string) => {
    setError(null);
    const cc = c || undefined;
    try {
      const [coh, er, sk, co, cs, tr, ni] = await Promise.all([
        api.cohort(cc), api.errors(cc), api.skills(cc), api.consent(), api.courses(), api.trends(cc), api.networkInvites(),
      ]);
      setData(coh); setErrors(er.errors); setSkills(sk.skills); setConsent(co); setCourses(cs.courses);
      setPeriods(tr.periods); setInvites(ni.invites);
    } catch (e) { setError(messageFor(e)); }
  }, []);

  useEffect(() => {
    if (!getAuth()) { router.replace("/"); return; }
    load("");
  }, [router, load]);

  const attest = async () => { try { setConsent(await api.attestConsent()); } catch (e) { setError(messageFor(e)); } };
  const answerInvite = async (networkId: string, decision: "accept" | "decline") => {
    setInviteBusy(networkId); setError(null);
    try { await api.networkInviteAnswer(networkId, decision); await load(course); }
    catch (e) { setError(messageFor(e)); }
    finally { setInviteBusy(null); }
  };
  const topics = topAdvice(errors, 5);

  return (
    <Shell>
      <section className="sheet">
        <h1>Panel docente</h1>
        {error && <p className="error" role="alert">{error}</p>}

        {invites.length > 0 && (
          <div className="notice" role="region" aria-label="Invitaciones pendientes">
            <h2>Invitaciones a redes de escuelas</h2>
            <p>Una red solicita compartir los resultados agregados de esta escuela. Al aceptar, solo verá grupos que cumplan el umbral mínimo de privacidad.</p>
            <ul>{invites.map((networkId) => (
              <li key={networkId}>
                <strong>{networkId}</strong>
                <div className="actions">
                  <button className="btn" type="button" disabled={inviteBusy === networkId} onClick={() => answerInvite(networkId, "accept")}>Aceptar</button>
                  <button className="btn ghost" type="button" disabled={inviteBusy === networkId} onClick={() => answerInvite(networkId, "decline")}>Rechazar</button>
                </div>
              </li>
            ))}</ul>
          </div>
        )}

        {consent && consent.required && !consent.attested && (
          <div className="notice" role="alert">
            <p><strong>Falta un paso antes de que los estudiantes practiquen.</strong> La escuela tiene que confirmar que obtuvo el consentimiento de las familias para el uso de la plataforma.</p>
            <div className="actions"><button className="btn" type="button" onClick={attest}>Confirmo que la escuela cuenta con el consentimiento</button></div>
          </div>
        )}
        {consent?.attested && <p className="muted">Consentimiento de las familias confirmado por la escuela.</p>}

        {courses.length > 0 && (
          <label className="field"><span>Curso</span>
            <select value={course} onChange={(e) => { setCourse(e.target.value); load(e.target.value); }}>
              <option value="">Toda la escuela</option>
              {courses.map((c) => <option key={c.course_id} value={c.course_id}>{c.course_label ?? c.course_id}</option>)}
            </select>
          </label>
        )}

        <h2>Niveles</h2>
        <p className="lead">Cuántos estudiantes terminaron la práctica de 24 preguntas en cada nivel. Solo se muestran totales: no hay nombres ni datos individuales.</p>
        {data && data.n === 0 && <p>Todavía nadie terminó la práctica. Cuando lo hagan, vas a ver acá la distribución.</p>}
        {data && data.n > 0 && (
          <>
            <p><strong>{data.n}</strong> {data.n === 1 ? "estudiante terminó" : "estudiantes terminaron"} la práctica.</p>
            <LevelBars data={data} />
            <p className="muted">La línea roja marca el nivel mínimo propuesto (N{data.baseline_level}), todavía provisorio hasta calibrar con datos del piloto.</p>
          </>
        )}

        <h2>Evolución en el tiempo</h2>
        {periods.length < 2 ? <p>Cuando haya prácticas terminadas en al menos dos meses, vas a ver cómo evolucionan los niveles.</p> : (
          <>
            <MultiLineChart title="Nivel promedio por mes" xLabel="Mes" yLabel="Nivel (1 a 8)" yDomain={[1, 8]} categories={periods.map((p) => p.period)}
              series={[{ name: "Nivel promedio", color: "#1F4FD8", bold: true, points: periods.flatMap((p, i) => (p.mean_level === null ? [] : [[i, p.mean_level] as [number, number]])) }]}
              note="Los niveles son provisorios: sirven para ver la tendencia, no para comparar estudiantes." />
            <MultiLineChart title="Estudiantes que alcanzan el nivel mínimo propuesto" xLabel="Mes" yLabel="% de estudiantes" yDomain={[0, 100]} categories={periods.map((p) => p.period)}
              series={[{ name: "Alcanzan N4 o más", color: "#006B50", bold: true, points: periods.flatMap((p, i) => (p.share_baseline === null ? [] : [[i, p.share_baseline] as [number, number]])) }]} />
          </>
        )}

        <h2>Lo que más cuesta</h2>
        {topics.length === 0 ? <p>Todavía no hay errores registrados.</p> : (
          <ul className="advice">{topics.map(({ advice, count }) => (
            <li key={advice.topic}><strong>{advice.topic}</strong> ({count} respuestas): {advice.advice}</li>
          ))}</ul>
        )}

        <h2>Dominio por tema</h2>
        {skills.length === 0 ? <p>Todavía no hay datos suficientes.</p> : (
          <ul className="skills">{skills.map((s) => (
            <li key={s.skill}>
              <span className="skill-name">{s.name}</span>
              <span className="bar-track"><span className="bar-fill" style={{ width: `${s.mean_p * 100}%` }} /></span>
              <span className="count">{Math.round(s.mean_p * 100)} %</span>
              <span className="muted">{s.students} est.</span>
            </li>
          ))}</ul>
        )}

        <div className="actions">
          <button className="btn ghost" type="button" onClick={() => load(course)}>Actualizar</button>
          <button className="btn ghost" type="button" onClick={() => downloadCsv(course || undefined).catch((e) => setError(messageFor(e)))}>Descargar resumen (CSV)</button>
          {isAdmin && <Link className="btn" href="/review">Revisar plantillas de ejercicios</Link>}
          <Link className="btn ghost" href="/analysis">Análisis de ejercicios</Link>
          <Link className="btn ghost" href="/teacher/report">Informe para imprimir</Link>
        </div>
      </section>
    </Shell>
  );
}
