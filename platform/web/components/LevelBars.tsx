import type { Cohort } from "@/lib/types";

export function LevelBars({ data }: { data: Cohort }) {
  const levels = [8, 7, 6, 5, 4, 3, 2, 1];
  const max = Math.max(1, ...levels.map((l) => data.levels[String(l)] ?? 0));
  return (
    <ul className="bars" aria-label="Estudiantes por nivel">
      {levels.map((l) => {
        const n = data.levels[String(l)] ?? 0;
        return (
          <li key={l} className={l === data.baseline_level ? "baseline" : ""}>
            <span className="lv">N{l}</span>
            <span className="bar-track"><span className="bar-fill" style={{ width: `${(n / max) * 100}%` }} /></span>
            <span className="count">{n}</span>
          </li>
        );
      })}
    </ul>
  );
}
