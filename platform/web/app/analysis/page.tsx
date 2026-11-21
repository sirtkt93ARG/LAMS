"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import type { FamilyStat } from "@/lib/types";

export default function AnalysisPage() {
  const router = useRouter();
  const [rows, setRows] = useState<FamilyStat[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuth()) { router.replace("/"); return; }
    api.itemAnalysis().then((r) => setRows(r.templates)).catch((e) => setError(messageFor(e)));
  }, [router]);

  return (
    <Shell>
      <section className="sheet">
        <h1>Análisis de ejercicios</h1>
        <p className="lead">Cómo funcionó cada plantilla con las respuestas de tu escuela. La dificultad es la proporción de respuestas correctas; la discriminación indica si quienes aciertan este ejercicio también aciertan el resto. Con pocos datos, no hay que sacar conclusiones.</p>
        {error && <p className="error" role="alert">{error}</p>}
        {rows && rows.length === 0 && <p>Todavía no hay respuestas.</p>}
        {rows && rows.length > 0 && (
          <table className="table">
            <thead><tr><th scope="col">Plantilla</th><th scope="col">Respuestas</th><th scope="col">Dificultad</th><th scope="col">Discriminación</th><th scope="col">Tiempo</th><th scope="col">Errores más comunes</th><th scope="col">Avisos</th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.template}>
                <th scope="row">{r.template}</th><td>{r.n}</td>
                <td>{r.p === null ? "—" : `${Math.round(r.p * 100)} %`}</td>
                <td>{r.discrimination === null ? "—" : r.discrimination.toFixed(2)}</td>
                <td>{r.mean_time_s === null ? "—" : `${Math.round(r.mean_time_s)} s`}</td>
                <td>{Object.keys(r.top_errors).map((t) => t.replace(/_/g, " ")).join(", ") || "—"}</td>
                <td>{r.flags.join(", ") || "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
        <div className="actions"><Link className="btn ghost" href="/teacher">Volver al panel</Link></div>
      </section>
    </Shell>
  );
}
