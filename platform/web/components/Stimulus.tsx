import type { Stimulus as StimulusT } from "@/lib/types";
import { Chart } from "./Chart";

export function Stimulus({ s }: { s: StimulusT | null }) {
  if (!s) return null;
  if (s.type === "table") {
    return (
      <table className="stimulus">
        <caption className="sr-only">Datos del problema</caption>
        <thead><tr>{s.header.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
        <tbody>{s.rows.map((r, i) => <tr key={i}>{r.map((c, j) => (j === 0 ? <th key={j} scope="row">{c}</th> : <td key={j}>{c}</td>))}</tr>)}</tbody>
      </table>
    );
  }
  if (s.type === "rect") {
    const k = Math.min(240 / s.width, 140 / s.height);
    const w = s.width * k, h = s.height * k;
    return (
      <figure className="chart">
        <svg viewBox="0 0 320 200" role="img" aria-label={`Rectángulo de ${s.width} ${s.unit} de largo por ${s.height} ${s.unit} de ancho`}>
          <rect x={40} y={30} width={w} height={h} className="chart-bar" fillOpacity={0.15} stroke="currentColor" strokeWidth={2} />
          <text x={40 + w / 2} y={22} textAnchor="middle" className="chart-label">{s.width} {s.unit}</text>
          <text x={46 + w} y={30 + h / 2} className="chart-label">{s.height} {s.unit}</text>
        </svg>
      </figure>
    );
  }
  return <Chart s={s} />;
}
