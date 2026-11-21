export type LineSeries = {
  name: string; points: [number, number][]; color: string; dashed?: boolean; bold?: boolean;
  ci?: [number, number, number][];      // [x, límite inferior, límite superior]: intervalo de confianza del 95 %
};

type Props = {
  title: string; series: LineSeries[]; xLabel: string; yLabel: string;
  categories?: string[];            // si se indica, x son índices 0..n-1 con estas etiquetas
  yDomain?: [number, number]; gapAfter?: number; note?: string;
};

function niceStep(range: number, ticks = 5): number {
  const raw = range / ticks, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
}

/** Separa etiquetas verticalmente para que no se pisen. */
function spread(ys: number[], min: number): number[] {
  const idx = ys.map((y, i) => [y, i] as const).sort((a, b) => a[0] - b[0]);
  const out = [...ys];
  let prev = -Infinity;
  for (const [y, i] of idx) { out[i] = Math.max(y, prev + min); prev = out[i]; }
  return out;
}

export function MultiLineChart({ title, series, xLabel, yLabel, categories, yDomain, gapAfter = 3.5, note }: Props) {
  const W = 600, H = 340, L = 54, R = 128, T = 30, B = 52;
  const all = series.flatMap((s) => [...s.points, ...(s.ci ?? []).flatMap(([x, lo, hi]) => [[x, lo], [x, hi]] as [number, number][])]);
  if (all.length === 0) return <p className="muted">No hay datos para mostrar.</p>;
  const xs = categories ? categories.map((_, i) => i) : [...new Set(all.map((p) => p[0]))].sort((a, b) => a - b);
  const xMin = Math.min(...xs), xMax = Math.max(...xs, xMin + 1);
  let [y0, y1] = yDomain ?? [Math.min(...all.map((p) => p[1])), Math.max(...all.map((p) => p[1]))];
  if (!yDomain) { const step = niceStep(Math.max(y1 - y0, 10)); y0 = Math.floor((y0 - step / 2) / step) * step; y1 = Math.ceil((y1 + step / 2) / step) * step; }
  const step = niceStep(y1 - y0);
  const yTicks: number[] = []; for (let t = Math.ceil(y0 / step) * step; t <= y1 + 1e-9; t += step) yTicks.push(Math.round(t * 100) / 100);
  const X = (x: number) => L + ((x - xMin) / (xMax - xMin)) * (W - L - R);
  const Y = (y: number) => T + (1 - (y - y0) / (y1 - y0)) * (H - T - B);
  const ends = series.map((s) => (s.points.length ? Y(s.points[s.points.length - 1][1]) : 0));
  const labelY = spread(ends, 13);
  const summary = `${title}. ` + series.map((s) => `${s.name}: ` + s.points.map(([x, y]) => `${categories ? categories[x] : x} ${y}`).join(", ")).join(". ");
  return (
    <figure className="chart wide">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary}>
        <text x={W / 2} y={16} textAnchor="middle" className="chart-title">{title}</text>
        {yTicks.map((t) => (
          <g key={t}><line x1={L} x2={W - R} y1={Y(t)} y2={Y(t)} className="chart-grid" /><text x={L - 6} y={Y(t) + 4} textAnchor="end" className="chart-tick">{t}</text></g>
        ))}
        <line x1={L} x2={L} y1={T} y2={H - B} className="chart-axis" />
        <line x1={L} x2={W - R} y1={H - B} y2={H - B} className="chart-axis" />
        {xs.map((x) => <text key={x} x={X(x)} y={H - B + 16} textAnchor="middle" className="chart-tick">{categories ? categories[x] : x}</text>)}
        {series.filter((s) => s.ci && s.ci.length > 1).map((s) => (
          <polygon key={s.name + "-ci"} fill={s.color} fillOpacity={0.15} stroke="none"
            points={[...s.ci!.map(([x, , hi]) => `${X(x)},${Y(hi)}`), ...[...s.ci!].reverse().map(([x, lo]) => `${X(x)},${Y(lo)}`)].join(" ")} />
        ))}
        {series.map((s) => (
          <g key={s.name} stroke={s.color} fill={s.color}>
            {s.points.slice(1).map((p, i) => {
              const a = s.points[i], bridge = !categories && p[0] - a[0] > gapAfter;
              return <line key={i} x1={X(a[0])} y1={Y(a[1])} x2={X(p[0])} y2={Y(p[1])} fill="none"
                strokeWidth={s.bold ? 4 : 2.5} strokeDasharray={bridge ? "2 5" : s.dashed ? "7 4" : undefined} opacity={bridge ? 0.7 : 1} />;
            })}
            {s.points.map(([x, y]) => <circle key={x} cx={X(x)} cy={Y(y)} r={s.bold ? 4.5 : 3.5} stroke="none" />)}
          </g>
        ))}
        {series.map((s, i) => <text key={s.name} x={W - R + 8} y={labelY[i] + 4} className="chart-value" fill={s.color} style={{ fontWeight: s.bold ? 700 : 400 }}>{s.name.length > 20 ? s.name.slice(0, 19) + "…" : s.name}</text>)}
        <text x={(L + W - R) / 2} y={H - 8} textAnchor="middle" className="chart-label">{xLabel}</text>
        <text x={12} y={(T + H - B) / 2} textAnchor="middle" className="chart-label" transform={`rotate(-90 12 ${(T + H - B) / 2})`}>{yLabel}</text>
      </svg>
      {note && <figcaption className="muted">{note}</figcaption>}
      <details className="chart-data">
        <summary>Ver los datos en una tabla</summary>
        <div className="scroll">
          <table className="stimulus">
            <thead><tr><th scope="col">{xLabel}</th>{series.map((s) => <th key={s.name} scope="col">{s.name}</th>)}</tr></thead>
            <tbody>{xs.map((x) => (
              <tr key={x}><th scope="row">{categories ? categories[x] : x}</th>
                {series.map((s) => <td key={s.name}>{s.points.find((p) => p[0] === x)?.[1] ?? "—"}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
