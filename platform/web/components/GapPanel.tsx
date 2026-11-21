import { MultiLineChart, type LineSeries } from "./MultiLineChart";
import type { GapRow } from "@/lib/types";

const fmt = (x: number, d = 0) => x.toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d });
const sign = (x: number, d = 0) => (x > 0 ? "+" : x < 0 ? "−" : "") + fmt(Math.abs(x), d);
const COLORS = ["#B8352E", "#E69F00", "#56B4E9", "#009E73"];

export function GapPanel({ rows, domainLabel, entity }: { rows: GapRow[]; domainLabel: string; entity: string }) {
  const by = (dim: string) => rows.filter((r) => r.dimension === dim);
  const genderGap = by("genero_brecha").sort((a, b) => a.cycle - b.cycle);
  const gradient = by("escs_pendiente").sort((a, b) => a.cycle - b.cycle);
  const escsGap = by("escs_brecha").sort((a, b) => a.cycle - b.cycle);
  const lines: LineSeries[] = ["Q1", "Q2", "Q3", "Q4"].map((q, i) => {
    const pts = by("escs_cuartil").filter((r) => r.group === q).sort((a, b) => a.cycle - b.cycle);
    return { name: i === 0 ? "Q1 (menor ESCS)" : i === 3 ? "Q4 (mayor ESCS)" : q, color: COLORS[i], bold: false,
      points: pts.map((r) => [r.cycle, r.value] as [number, number]),
      ci: pts.filter((r) => r.se !== null).map((r) => [r.cycle, r.value - 1.96 * (r.se as number), r.value + 1.96 * (r.se as number)] as [number, number, number]) };
  });
  const last = <T,>(a: T[]) => a[a.length - 1];
  const sig = (r: GapRow) => (r.se !== null && Math.abs(r.value) > 1.96 * r.se ? "diferencia significativa" : "diferencia no significativa");
  return (
    <>
      <h2>Brechas en {domainLabel.toLowerCase()}: {entity}</h2>
      <ul className="cards">
        {last(escsGap) && <li><span className="k">Brecha entre cuartiles de ESCS ({last(escsGap).cycle})</span><span className="v">{sign(last(escsGap).value)}</span><span className="muted">Q4 menos Q1, en puntos · {sig(last(escsGap))}</span></li>}
        {last(gradient) && <li><span className="k">Puntos por unidad de ESCS ({last(gradient).cycle})</span><span className="v">{fmt(last(gradient).value, 1)}</span><span className="muted">gradiente socioeconómico</span></li>}
        {last(genderGap) && <li><span className="k">Mujeres menos varones ({last(genderGap).cycle})</span><span className="v">{sign(last(genderGap).value, 1)}</span><span className="muted">en puntos · {sig(last(genderGap))}</span></li>}
      </ul>
      {by("escs_cuartil").length > 0 && (
        <MultiLineChart title="Puntaje promedio según cuartil del índice socioeconómico (ESCS)" series={lines} xLabel="Ciclo de PISA" yLabel="Puntos"
          note="Las bandas son intervalos de confianza del 95 %. Calculado con los microdatos de la OCDE (replicación y valores plausibles)." />
      )}
      {genderGap.length > 0 && (
        <details className="chart-data" open>
          <summary>Brecha de género por ciclo</summary>
          <table className="stimulus"><thead><tr><th scope="col">Ciclo</th><th scope="col">Mujeres menos varones</th><th scope="col">Error estándar</th><th scope="col">Lectura</th></tr></thead>
            <tbody>{genderGap.map((r) => <tr key={r.cycle}><th scope="row">{r.cycle}</th><td>{sign(r.value, 1)}</td><td>{r.se === null ? "—" : fmt(r.se, 1)}</td><td>{sig(r)}</td></tr>)}</tbody></table>
        </details>
      )}
    </>
  );
}
