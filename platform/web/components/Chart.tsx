import type { ChartStimulus } from "@/lib/types";

function niceCeil(v: number): number {
  const p = Math.pow(10, Math.floor(Math.log10(Math.max(v, 1))));
  const m = v / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
}

export function Chart({ s }: { s: ChartStimulus }) {
  const W = 440, H = 260, L = 52, R = 14, T = 30, B = 46;
  const top = niceCeil(Math.max(...s.values));
  const n = s.categories.length;
  const band = (W - L - R) / n;
  const y = (v: number) => T + (H - T - B) * (1 - v / top);
  const x = (i: number) => L + band * (i + 0.5);
  const ticks = [0, 1, 2, 3, 4, 5].map((k) => (top / 5) * k);
  const summary = `${s.title}. ` + s.categories.map((c, i) => `${c}: ${s.values[i]}`).join("; ") + ".";
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary}>
        <text x={W / 2} y={16} textAnchor="middle" className="chart-title">{s.title}</text>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="chart-grid" />
            <text x={L - 6} y={y(t) + 4} textAnchor="end" className="chart-tick">{Number.isInteger(t) ? t : t.toFixed(1)}</text>
          </g>
        ))}
        <line x1={L} x2={L} y1={T} y2={H - B} className="chart-axis" />
        <line x1={L} x2={W - R} y1={H - B} y2={H - B} className="chart-axis" />
        {s.type === "bar_chart" && s.values.map((v, i) => (
          <g key={i}>
            <rect x={x(i) - band * 0.3} y={y(v)} width={band * 0.6} height={H - B - y(v)} className="chart-bar" />
            <text x={x(i)} y={y(v) - 5} textAnchor="middle" className="chart-value">{v}</text>
          </g>
        ))}
        {s.type === "line_chart" && (
          <g>
            <polyline className="chart-line" points={s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ")} />
            {s.values.map((v, i) => (
              <g key={i}>
                <circle cx={x(i)} cy={y(v)} r={4} className="chart-dot" />
                <text x={x(i)} y={y(v) - 9} textAnchor="middle" className="chart-value">{v}</text>
              </g>
            ))}
          </g>
        )}
        {s.categories.map((c, i) => <text key={c} x={x(i)} y={H - B + 16} textAnchor="middle" className="chart-tick">{c}</text>)}
        <text x={(L + W - R) / 2} y={H - 6} textAnchor="middle" className="chart-label">{s.x_label}</text>
        <text x={12} y={(T + H - B) / 2} textAnchor="middle" className="chart-label" transform={`rotate(-90 12 ${(T + H - B) / 2})`}>{s.y_label}</text>
      </svg>
      <details className="chart-data">
        <summary>Ver los datos en una tabla</summary>
        <table className="stimulus">
          <thead><tr><th scope="col">{s.x_label}</th><th scope="col">{s.y_label}</th></tr></thead>
          <tbody>{s.categories.map((c, i) => <tr key={c}><th scope="row">{c}</th><td>{s.values[i]}</td></tr>)}</tbody>
        </table>
      </details>
    </figure>
  );
}
