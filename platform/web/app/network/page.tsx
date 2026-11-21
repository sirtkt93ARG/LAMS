"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import type { NetworkSummary } from "@/lib/types";

export default function NetworkPage() {
  const router = useRouter();
  const [data, setData] = useState<NetworkSummary | null>(null);
  const [school, setSchool] = useState("");
  const [schoolInvalid, setSchoolInvalid] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => api.networkSummary().then(setData).catch((e) => setError(messageFor(e))), []);
  useEffect(() => {
    const auth = getAuth();
    if (!auth) { router.replace("/"); return; }
    if (auth.role !== "network" && auth.role !== "admin") { router.replace("/teacher"); return; }
    load();
  }, [router, load]);

  const add = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!school.trim()) { setSchoolInvalid(true); return; }
    setBusy(true); setError(null); setNotice(null);
    try {
      await api.networkAdd(school.trim());
      setSchool(""); setSchoolInvalid(false);
      setNotice("Invitación enviada. La escuela debe aceptarla antes de compartir resultados.");
      await load();
    } catch (e) { setError(messageFor(e)); }
    finally { setBusy(false); }
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
        {notice && <p className="ok" role="status">{notice}</p>}
        {data && (data.schools.length === 0 && !data.others ? <p>Todavía no hay escuelas con suficientes estudiantes para mostrar.</p> : (
          <div className="table-wrapper" role="region" aria-labelledby="network-results-caption" tabIndex={0}>
            <table className="table">
            <caption id="network-results-caption">Resultados agregados de las escuelas que aceptaron compartir datos</caption>
            <thead><tr><th scope="col">Escuela</th><th scope="col">Estudiantes</th><th scope="col">Nivel promedio</th><th scope="col">Alcanzan N{data.baseline_level} o más</th></tr></thead>
            <tbody>{data.schools.map(row)}{data.others && row(data.others)}{data.total && row({ school: "Total", ...data.total })}</tbody>
          </table>
          </div>
        ))}
        {data && data.pending_tenants.length > 0 && (
          <div className="notice">
            <h2>Invitaciones pendientes ({data.pending_invitations})</h2>
            <p>Estas escuelas todavía no aceptaron compartir sus resultados agregados:</p>
            <ul>{data.pending_tenants.map((tenant) => <li key={tenant}>{tenant}</li>)}</ul>
          </div>
        )}
        {data && <p className="muted">{data.note}</p>}
        <form aria-labelledby="invite-school-heading" onSubmit={add}>
          <h2 id="invite-school-heading">Invitar una escuela</h2>
          <label className="field" htmlFor="school-tenant-id"><span>Identificador de la escuela</span>
            <input id="school-tenant-id" name="tenant_id" type="text" autoComplete="off" required maxLength={128}
              pattern=".*\S.*" value={school} aria-invalid={schoolInvalid}
              aria-describedby={schoolInvalid ? "school-tenant-help school-tenant-error" : "school-tenant-help"}
              onBlur={(e) => setSchoolInvalid(!e.currentTarget.validity.valid)}
              onInvalid={() => setSchoolInvalid(true)}
              onChange={(e) => { setSchool(e.target.value); if (e.currentTarget.validity.valid) setSchoolInvalid(false); }} />
            {schoolInvalid && <span className="field-error" id="school-tenant-error">Error: ingresá un identificador de escuela que no esté vacío ni contenga solo espacios.</span>}
          </label>
          <p className="muted" id="school-tenant-help">La escuela recibirá una invitación y decidirá si comparte sus resultados agregados. Máximo 128 caracteres.</p>
          <div className="actions"><button className="btn ghost" type="submit" disabled={busy}>{busy ? "Enviando…" : "Enviar invitación"}</button></div>
        </form>
      </section>
    </Shell>
  );
}
