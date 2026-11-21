import type { LadderStep } from "@/lib/types";

export function LevelLadder({ ladder, level, baseline }: { ladder: LadderStep[]; level: number; baseline: number }) {
  return (
    <ol className="ladder" aria-label="Niveles de desempeño">
      {[...ladder].reverse().map((s) => (
        <li key={s.level} className={[s.level === level ? "current" : "", s.level === baseline ? "baseline" : ""].join(" ").trim()}
          aria-current={s.level === level ? "step" : undefined}>
          <span className="lv">N{s.level}</span>
          <span>
            {s.descriptor}
            {s.level === level && <strong className="here"> Estás acá.</strong>}
            {s.level === baseline && <span className="note"> Nivel mínimo propuesto (provisorio).</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}
