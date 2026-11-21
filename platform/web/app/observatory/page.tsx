"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { MultiLineChart, type LineSeries } from "@/components/MultiLineChart";
import { GapPanel } from "@/components/GapPanel";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import type { CompareRow, Focus, GapRow, ObsMeta, ObsSeriesOut } from "@/lib/types";

const PALETTE = ["#005A8D", "#A33D00", "#006B50", "#7A2E6D", "#7A4B00", "#006D9C", "#5A3A78", "#333333"];
const GROUPS: Record<string, string> = { "America Latina": "América Latina", Referencia: "Países de referencia", "Promedio OCDE": "Promedio de la OCDE" };
const num = (x: number | null | undefined, d = 0) => (x === null || x === undefined ? "—" : x.toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const sign = (x: number) => (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toLocaleString("es-AR");

export default function Observatory() {
  const router = useRouter();
  const [meta, setMeta] = useState<ObsMeta | null>(null);
  const [domain, setDomain] = useState("matematica");
  const [chosen, setChosen] = useState<string[]>(["Argentina", "OCDE (promedio de tendencia)", "Chile", "Brasil"]);
  const [cycle, setCycle] = useState(2022);
  const [data, setData] = useState<ObsSeriesOut | null>(null);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [focus, setFocus] = useState<Focus | null>(null);
  const [gaps, setGaps] = useState<{ has_data: boolean; rows: GapRow[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuth()) { router.replace("/"); return; }
    Promise.all([api.obsMeta(), api.obsFocus("Argentina")]).then(([m, f]) => { setMeta(m); setFocus(f); }).catch((e) => setError(messageFor(e)));
  }, [router]);
  useEffect(() => { if (meta) api.obsSeries(domain, chosen).then(setData).catch((e) => setError(messageFor(e))); }, [meta, domain, chosen]);
  useEffect(() => { if (meta) api.obsGaps("Argentina", domain).then(setGaps).catch((e) => setError(messageFor(e))); }, [meta, domain]);
  useEffect(() => { if (meta) api.obsCompare(domain, cycle).then((r) => setRows(r.rows)).catch((e) => setError(messageFor(e))); }, [meta, domain, cycle]);

  const available = useMemo(() => new Set(meta?.entities.map((e) => e.entity)), [meta]);
  const lines: LineSeries[] = (data?.series ?? []).map((s, i) => ({
    name: s.entity, points: s.points, bold: s.entity === "Argentina", dashed: s.group === "Promedio OCDE",
    color: s.entity === "Argentina" ? "#1F4FD8" : s.group === "Promedio OCDE" ? "#4A5B73" : PALETTE[(i + 1) % PALETTE.length],
    ci: (s.se ?? []).flatMap(([c, se], k) => (se === null ? [] : [[c, s.points[k][1] - 1.96 * se, s.points[k][1] + 1.96 * se] as [number, number, number]])),
  }));
  const changes = (data?.series ?? []).filter((s) => s.changes && s.changes.length > 0);
  const f = focus?.domains[domain];
  const toggle = (e: string) => setChosen((c) => (c.includes(e) ? c.filter((x) => x !== e) : c.length >= 8 ? c : [...c, e]));
  const barMin = 300, barMax = 650;

  return (
    <Shell>
      <section className="sheet">
        <h1>Observatorio de resultados</h1>
        <p className="lead">Cómo evolucionaron los resultados de PISA en Argentina y en otros países desde 2000, con la fuente de cada dato. Sirve de contexto: no se compara con los niveles de esta plataforma.</p>
        {error && <p className="error" role="alert">{error}</p>}

        <fieldset className="controls">
          <legend>Dominio</legend>
          {meta && Object.entries(meta.domains).map(([k, v]) => (
            <label key={k}><input type="radio" name="dom" checked={domain === k} onChange={() => setDomain(k)} /> {v}</label>
          ))}
        </fieldset>

        {f && (
          <>
            <h2>Argentina en foco</h2>
            <ul className="cards">
              <li><span className="k">Último dato ({f.last_cycle})</span><span className="v">{num(f.last)}</span></li>
              <li><span className="k">Cambio desde {f.first_cycle}</span><span className="v">{sign(f.total_change)}</span></li>
              <li><span className="k">Cambio desde {f.short_from}</span><span className="v">{sign(f.short_change)}</span></li>
              <li><span className="k">Brecha con la OCDE</span><span className="v">{f.gap_vs_oecd === null ? "—" : sign(f.gap_vs_oecd)}</span>
                {f.years_vs_oecd !== null && <span className="muted">≈ {num(Math.abs(f.years_vs_oecd), 1)} años de escolaridad (regla orientativa: {meta?.points_per_year} puntos por año)</span>}</li>
            </ul>
            {f.gaps.length > 0 && <p className="muted">Sin dato nacional entre {f.gaps.map(([a, b]) => `${a} y ${b}`).join("; ")} (línea punteada).</p>}
          </>
        )}

        <h2>Evolución</h2>
        <fieldset className="controls">
          <legend>Elegí hasta 8 países o promedios</legend>
          {Object.entries(GROUPS).map(([g, label]) => (
            <div key={g} className="group"><strong>{label}</strong>
              {meta?.entities.filter((e) => e.group === g && available.has(e.entity)).map((e) => (
                <label key={e.entity}><input type="checkbox" checked={chosen.includes(e.entity)} onChange={() => toggle(e.entity)} /> {e.entity}</label>
              ))}
            </div>
          ))}
        </fieldset>
        {data && <MultiLineChart title={`Puntaje promedio en ${meta?.domains[domain]?.toLowerCase()}`} series={lines} xLabel="Ciclo de PISA" yLabel="Puntos"
          note={meta?.has_se ? "Las bandas son intervalos de confianza del 95 %. Los tramos punteados unen ciclos sin dato." : "Los tramos punteados unen ciclos sin dato. Estas series no traen errores estándar: no se afirma que una diferencia sea significativa."} />}
        {changes.length > 0 && (
          <>
            <h3>Cambios entre ciclos</h3>
            <ul className="advice">{changes.flatMap((s) => (s.changes ?? []).map((c) => (
              <li key={s.entity + c.from}><strong>{s.entity}</strong> {c.from}→{c.to}: {sign(c.diff)} puntos ({c.significant ? "diferencia significativa" : "diferencia no significativa"}).</li>
            )))}</ul>
            <p className="muted">La prueba usa los errores estándar de cada ciclo y no incluye el error de vinculación que publica la OCDE para comparar ciclos: con ese error, algunos cambios dejan de ser significativos.</p>
          </>
        )}

        <h2>Comparación en un ciclo</h2>
        <label className="field"><span>Ciclo</span>
          <select value={cycle} onChange={(e) => setCycle(Number(e.target.value))}>
            {meta?.cycles.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        {rows.length === 0 ? <p>No hay datos para este ciclo y dominio.</p> : (
          <ul className="bars compare" aria-label="Comparación de puntajes">
            {rows.map((r) => (
              <li key={r.entity} className={r.entity === "Argentina" ? "me" : ""}>
                <span className="lv wide">{r.entity}</span>
                <span className="bar-track"><span className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, ((r.mean - barMin) / (barMax - barMin)) * 100))}%` }} /></span>
                <span className="count wide">{num(r.mean)}{r.quality === "secundaria" ? " *" : ""}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="muted">Las barras empiezan en {barMin} puntos para que se vean las diferencias. * Fuente secundaria: contrastar con la tabla oficial.</p>

        {gaps && (gaps.has_data
          ? <GapPanel rows={gaps.rows} domainLabel={meta?.domains[domain] ?? domain} entity="Argentina" />
          : <><h2>Brechas por nivel socioeconómico y género</h2><p className="muted">Todavía no se cargaron microdatos de PISA, así que esta sección está vacía. Se completa con <code>scripts/pisa_ingest.py</code> (ver <code>docs/MICRODATOS_PISA.md</code>).</p></>)}

        {focus && focus.below_level2.length > 0 && (
          <>
            <h2>Argentina: estudiantes por debajo del nivel mínimo en matemática</h2>
            <MultiLineChart title="Porcentaje de estudiantes bajo el nivel 2" yDomain={[0, 100]}
              series={[{ name: "Argentina", color: "#1F4FD8", bold: true, points: focus.below_level2.map((b) => [b.cycle, b.value]) }]}
              xLabel="Ciclo de PISA" yLabel="% de estudiantes" note="Fuente secundaria: informes de prensa que citan a la OCDE. Verificar con las tablas oficiales." />
          </>
        )}

        <h2>Fuentes y límites</h2>
        <ul className="advice">
          {data?.provenance.map((p) => (
            <li key={p.source + p.url}><strong>{p.quality === "oficial_ocde" ? "Oficial" : "Secundaria (verificar)"}:</strong> {p.source}{" "}
              <a href={p.url} target="_blank" rel="noreferrer">ver fuente</a></li>
          ))}
          {meta?.notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      </section>
    </Shell>
  );
}
