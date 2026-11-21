"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import type { ReviewList } from "@/lib/types";

const STATUS = { pendiente: "Pendiente", aprobada: "Aprobada", rechazada: "Rechazada" } as const;

export default function ReviewListPage() {
  const router = useRouter();
  const [data, setData] = useState<ReviewList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const auth = getAuth();
    if (!auth) { router.replace("/"); return; }
    if (auth.role !== "admin") { router.replace("/teacher"); return; }
    api.reviewList().then(setData).catch((e) => setError(messageFor(e)));
  }, [router]);

  return (
    <Shell>
      <section className="sheet">
        <h1>Revisión de plantillas de ejercicios</h1>
        <p className="lead">Cada plantilla genera muchos ejercicios y la cuenta de cada uno ya se verifica sola. Tu revisión confirma que el enunciado, el contexto y los errores previstos sean adecuados. Los estudiantes solo practican con ejercicios de plantillas aprobadas.</p>
        {error && <p className="error" role="alert">{error}</p>}
        {data && (
          <>
            <p className="muted">Aprobaciones necesarias por plantilla: {data.required_approvals}.</p>
            <table className="table">
              <caption className="sr-only">Estado de revisión y ejercicios aprobados por plantilla</caption>
              <thead><tr><th scope="col">Plantilla</th><th scope="col">Nivel</th><th scope="col">Ejercicios aprobados</th><th scope="col">Estado</th><th scope="col"><span className="sr-only">Acción</span></th></tr></thead>
              <tbody>
                {data.templates.map((t) => (
                  <tr key={t.id}>
                    <th scope="row">{t.id}. {t.title}</th>
                    <td>N{t.level}</td>
                    <td>{t.n_approved} de {t.n_items}</td>
                    <td>{STATUS[t.status]}{t.status === "pendiente" ? ` (${t.approvals} de ${t.required})` : ""}</td>
                    <td>{t.reviewed_by_me ? "Ya la revisaste" : <Link href={`/review/${t.id}`}>Revisar</Link>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
        <div className="actions"><Link className="btn ghost" href="/teacher">Volver al panel</Link></div>
      </section>
    </Shell>
  );
}
