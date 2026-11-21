"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { LevelBars } from "@/components/LevelBars";
import { MultiLineChart } from "@/components/MultiLineChart";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import { topAdvice } from "@/lib/tags";
import type { ClassSkill, Cohort, Period } from "@/lib/types";

export default function PrintableReport() {
  const router = useRouter();
  const [cohort, setCohort] = useState<Cohort | null>(null);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [errors, setErrors] = useState<Record<string, number>>({});
  const [skills, setSkills] = useState<ClassSkill[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuth()) { router.replace("/"); return; }
    Promise.all([api.cohort(), api.trends(), api.errors(), api.skills()])
      .then(([c, t, e, s]) => { setCohort(c); setPeriods(t.periods); setErrors(e.errors); setSkills(s.skills); })
      .catch((e) => setError(messageFor(e)));
  }, [router]);

  return (
    <Shell>
      <section className="sheet report">
        <h1>Informe de la escuela</h1>
        <p className="muted">Generado el {new Date().toLocaleDateString("es-AR")}. Niveles provisorios, sin datos individuales.</p>
        {error && <p className="error" role="alert">{error}</p>}
        {cohort && <><h2>Niveles</h2><p>{cohort.n} estudiantes terminaron la práctica.</p><LevelBars data={cohort} /></>}
        {periods.length >= 2 && (
          <><h2>Evolución</h2>
            <MultiLineChart title="Nivel promedio por mes" xLabel="Mes" yLabel="Nivel (1 a 8)" yDomain={[1, 8]} categories={periods.map((p) => p.period)}
              series={[{ name: "Nivel promedio", color: "#1F4FD8", bold: true, points: periods.flatMap((p, i) => (p.mean_level === null ? [] : [[i, p.mean_level] as [number, number]])) }]} /></>
        )}
        <h2>Lo que más cuesta</h2>
        <ul className="advice">{topAdvice(errors, 5).map(({ advice, count }) => <li key={advice.topic}><strong>{advice.topic}</strong> ({count}): {advice.advice}</li>)}</ul>
        <h2>Dominio por tema</h2>
        <ul className="skills">{skills.map((s) => (
          <li key={s.skill}><span className="skill-name">{s.name}</span><span className="bar-track"><span className="bar-fill" style={{ width: `${s.mean_p * 100}%` }} /></span><span className="count">{Math.round(s.mean_p * 100)} %</span><span className="muted">{s.students} est.</span></li>
        ))}</ul>
        <div className="actions no-print"><button className="btn" type="button" onClick={() => window.print()}>Imprimir o guardar como PDF</button></div>
      </section>
    </Shell>
  );
}
