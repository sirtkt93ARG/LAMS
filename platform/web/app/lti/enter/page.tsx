"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api, messageFor } from "@/lib/api";
import { setAuth } from "@/lib/auth";

function Enter() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) { setError("Falta el acceso desde el aula virtual. Volvé a abrir la actividad desde allí."); return; }
    api.exchange(token)
      .then((out) => { setAuth({ role: out.role, token: out.access_token }); router.replace(out.role === "teacher" ? "/teacher" : "/practice"); })
      .catch((e) => setError(messageFor(e)));
  }, [params, router]);

  return (
    <section className="sheet" aria-live="polite">
      {error ? <p className="error" role="alert">{error}</p> : <p>Abriendo la actividad…</p>}
    </section>
  );
}

export default function LtiEnter() {
  return <Shell showExit={false}><Suspense fallback={null}><Enter /></Suspense></Shell>;
}
