"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { ReviewItem } from "@/components/ReviewItem";
import { api, messageFor } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import type { ReviewSample } from "@/lib/types";

const LABELS: Record<string, string> = {
  clave_correcta: "La clave es correcta (hice la cuenta en al menos un ejemplo)",
  enunciado_claro: "El enunciado se entiende sin explicaciones extra",
  contexto_adecuado_15_anios: "El contexto es adecuado para estudiantes de 15 años de la región",
  distractores_plausibles: "Los errores previstos son razonables (o no aplica)",
  sin_sesgos: "No hay sesgos ni estereotipos",
};

export default function ReviewDetail() {
  const { tid } = useParams<{ tid: string }>();
  const router = useRouter();
  const [sample, setSample] = useState<ReviewSample | null>(null);
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const auth = getAuth();
    if (!auth) { router.replace("/"); return; }
    if (auth.role !== "admin") { router.replace("/teacher"); return; }
    api.reviewSample(tid).then(setSample).catch((e) => setError(messageFor(e)));
  }, [tid, router]);

  const allChecked = sample ? sample.checklist.every((k) => checks[k]) : false;

  const submit = async (decision: "aprobar" | "rechazar") => {
    setBusy(true); setError(null);
    try { await api.reviewSubmit(tid, decision, comment, checks); router.push("/review"); }
    catch (e) { setError(messageFor(e)); setBusy(false); }
  };

  return (
    <Shell>
      <section className="sheet">
        <h1>{sample ? `${sample.template}. ${sample.title}` : "Plantilla"}</h1>
        <p className="lead">Estos son {sample?.items.length ?? 5} ejemplos generados con la plantilla. Revisalos y completá la lista de control.</p>
        {error && <p className="error" role="alert">{error}</p>}
        {sample?.items.map((it) => <ReviewItem key={it.id} item={it} />)}

        {sample && (
          <form onSubmit={(e) => e.preventDefault()}>
            <h2>Lista de control</h2>
            <fieldset className="checklist">
              <legend className="sr-only">Lista de control</legend>
              {sample.checklist.map((k) => (
                <label key={k}><input type="checkbox" checked={!!checks[k]} onChange={(e) => setChecks({ ...checks, [k]: e.target.checked })} /> {LABELS[k] ?? k}</label>
              ))}
            </fieldset>
            <label className="field wide"><span>Comentario (obligatorio si rechazás)</span>
              <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
            </label>
            <div className="actions">
              <button className="btn" type="button" disabled={!allChecked || busy} onClick={() => submit("aprobar")}>Aprobar plantilla</button>
              <button className="btn ghost" type="button" disabled={comment.trim().length < 10 || busy} onClick={() => submit("rechazar")}>Rechazar plantilla</button>
              <Link className="btn ghost" href="/review">Cancelar</Link>
            </div>
          </form>
        )}
      </section>
    </Shell>
  );
}
