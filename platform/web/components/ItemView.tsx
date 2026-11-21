"use client";
import { useEffect, useId, useRef, useState } from "react";
import type { PublicItem } from "@/lib/types";
import { MathPreview } from "./MathPreview";
import { SpeakButton } from "./SpeakButton";
import { Stimulus } from "./Stimulus";

type Props = { item: PublicItem; busy: boolean; onSubmit: (response: string) => void; onHint?: (level: number) => Promise<string> };

export function ItemView({ item, busy, onSubmit, onHint }: Props) {
  const [value, setValue] = useState("");
  const [hints, setHints] = useState<string[]>([]);
  const uid = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setValue("");
    setHints([]);
    if (item.kind !== "choice") inputRef.current?.focus();
  }, [item.id, item.kind]);

  const ready = value.trim() !== "" && !busy;
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (ready) onSubmit(value.trim());
  };

  return (
    <section className="sheet" aria-labelledby={`${uid}-stem`}>
      <p id={`${uid}-stem`} className="stem">{item.stem}</p>
      <form onSubmit={submit} aria-labelledby={`${uid}-stem`}>

      <Stimulus s={item.stimulus} />

      {item.kind === "choice" && (
        <fieldset className="choices">
          <legend>Elegí una respuesta</legend>
          {item.options.map((o) => (
            <label key={o.id} className={value === o.id ? "choice picked" : "choice"}>
              <input type="radio" name={`${uid}-r`} value={o.id} checked={value === o.id} onChange={() => setValue(o.id)} required />
              <span className="letter" aria-hidden="true">{o.id}</span>
              <span className="choice-text">{o.text}</span>
            </label>
          ))}
        </fieldset>
      )}

      {item.kind === "numeric" && (
        <label className="field" htmlFor={`${uid}-numeric`}>
          <span>Tu respuesta (escribí solo el número)</span>
          <input id={`${uid}-numeric`} ref={inputRef} inputMode="decimal" autoComplete="off" value={value}
            onChange={(e) => setValue(e.target.value)} required name="response" />
        </label>
      )}

      {item.kind === "expression" && (
        <div>
          <label className="field" htmlFor={`${uid}-expression`}>
            <span>Tu expresión (podés escribir 200n o 200*n)</span>
            <input id={`${uid}-expression`} ref={inputRef} autoComplete="off" spellCheck={false} value={value}
              onChange={(e) => setValue(e.target.value)} required name="response" />
          </label>
          <MathPreview source={value} />
        </div>
      )}

      {hints.length > 0 && <ul className="hints" aria-live="polite">{hints.map((h, i) => <li key={i}><strong>Pista {i + 1}:</strong> {h}</li>)}</ul>}

      <div className="actions">
        <button className="btn" type="submit" disabled={!ready}>Responder</button>
        {onHint && hints.length < 2 && (
          <button className="btn ghost" type="button" disabled={busy}
            onClick={async () => { const h = await onHint(hints.length + 1); setHints([...hints, h]); }}>Pista {hints.length + 1}</button>
        )}
        <SpeakButton text={item.stem} />
      </div>
      </form>
    </section>
  );
}
