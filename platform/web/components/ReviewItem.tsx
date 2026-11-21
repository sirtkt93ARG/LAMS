import type { ReviewItemData } from "@/lib/types";
import { Stimulus } from "./Stimulus";

const pretty = (tag: string) => tag.replace(/_/g, " ");

export function ReviewItem({ item }: { item: ReviewItemData }) {
  return (
    <article className="review-item">
      <p className="stem">{item.stem}</p>
      <Stimulus s={item.stimulus} />
      {item.kind === "choice" ? (
        <ul className="review-options">
          {item.options.map((o) => {
            const isKey = o.id === item.correct;
            return (
              <li key={o.id} className={isKey ? "key" : ""}>
                <strong>{o.id}.</strong> {o.text}{" "}
                {isKey ? <span className="tagline">Clave correcta</span> : <span className="tagline">Error que modela: {o.tag ? pretty(o.tag) : "sin etiqueta"}</span>}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="key-answer">Respuesta esperada: <strong>{String(item.correct)}</strong></p>
      )}
      {item.explanation && (
        <details className="review-expl"><summary>Resolución paso a paso</summary>
          <ol>{item.explanation.map((x, i) => <li key={i}>{x}</li>)}</ol></details>
      )}
      <p className="muted">Ejemplo {item.id} · nivel objetivo N{item.target_level} · licencia {item.license}</p>
    </article>
  );
}
