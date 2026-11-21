"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import type { NetworkSummary } from "@/lib/types";

export default function NetworkPage() {
  const router = useRouter();
  const [data, setData] = useState<NetworkSummary | null>(null);
  const [school, setSchool] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = () => api.networkSummary().then(setData).catch((e) => setError(messageFor(e)));
  useEffect(() => { if (!getAuth()) { router.replace("/"); return; } load(); }, [router]);

  const add = async () => {
    if (!school.trim()) return;
    try { await api.networkAdd(school.trim()); setSchool(""); await load(); } catch (e) { setError(messageFor(e)); }
  };
  const row = (r: { school: string; n: number; mean_level: number; share_baseline: number }) => (
    <tr key={r.school}><th scope="row">{r.school}</th><td>{r.n}</td><td>{r.mean_level.toLocaleString("es-AR")}</td><td>{r.share_baseline.toLocaleString("es-AR")} %</td></tr>
  );

  return (
    <Shell>
      <section className="sheet">
        <h1>Resumen de la red de escuelas</h1>
        <p className="lead">Niveles de las prácticas terminadas en cada escuela. Solo se muestran grupos de al menos {data?.min_cell ?? 10} estudiantes; los más chicos se agrupan para proteger la privacidad.</p>
        {error && <p className="error" role="alert">{error}</p>}
        {data && (data.schools.length === 0 && !data.others ? <p>Todavía no hay escuelas con suficientes estudiantes para mostrar.</p> : (
          <table className="table">
            <thead><tr><th scope="col">Escuela</th><th scope="col">Estudiantes</th><th scope="col">Nivel promedio</th><th scope="col">Alcanzan N{data.baseline_level} o más</th></tr></thead>
            <tbody>{data.schools.map(row)}{data.others && row(data.others)}{data.total && row({ school: "Total", ...data.total })}</tbody>
          </table>
        ))}
        {data && <p className="muted">{data.note}</p>}
        <label className="field"><span>Agregar una escuela a la red (identificador)</span>
          <input value={school} onChange={(e) => setSchool(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") add(); }} />
        </label>
        <div className="actions"><button className="btn ghost" type="button" onClick={add}>Agregar escuela</button></div>
      </section>
    </Shell>
  );
}
