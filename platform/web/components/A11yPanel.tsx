"use client";
import { useEffect, useState } from "react";

type Prefs = { text: "md" | "lg" | "xl"; contrast: boolean };
const KEY = "matheval.a11y";

function apply(p: Prefs): void {
  document.documentElement.dataset.text = p.text;
  document.documentElement.dataset.contrast = p.contrast ? "high" : "normal";
}

export function A11yPanel() {
  const [p, setP] = useState<Prefs>({ text: "md", contrast: false });

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(KEY);
      if (raw) { const v = JSON.parse(raw) as Prefs; setP(v); apply(v); }
    } catch { /* sin almacenamiento: se usan los valores por defecto */ }
  }, []);

  const update = (n: Prefs) => {
    setP(n); apply(n);
    try { window.localStorage.setItem(KEY, JSON.stringify(n)); } catch { /* ignorar */ }
  };

  return (
    <details className="a11y">
      <summary>Accesibilidad</summary>
      <div className="a11y-body">
        <fieldset>
          <legend>Tamaño del texto</legend>
          {([["md", "Normal"], ["lg", "Grande"], ["xl", "Muy grande"]] as const).map(([v, label]) => (
            <label key={v}><input type="radio" name="a11y-text" checked={p.text === v} onChange={() => update({ ...p, text: v })} /> {label}</label>
          ))}
        </fieldset>
        <label><input type="checkbox" checked={p.contrast} onChange={(e) => update({ ...p, contrast: e.target.checked })} /> Alto contraste</label>
      </div>
    </details>
  );
}
