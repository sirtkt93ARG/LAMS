"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { devLogin, keycloakLogin } from "@/lib/auth";
import type { Role } from "@/lib/types";

const DEV = process.env.NEXT_PUBLIC_DEV === "1";

export default function Home() {
  const router = useRouter();
  const [sub, setSub] = useState("alumno-1");
  const [tenant, setTenant] = useState("escuela-1");
  const [role, setRole] = useState<Role>("student");
  const [error, setError] = useState<string | null>(null);

  const go = (r: Role) => router.push(r === "student" ? "/practice" : r === "network" ? "/network" : "/teacher");

  return (
    <Shell showExit={false}>
      <section className="sheet">
        <h1>Practicá matemática con problemas de la vida real</h1>
        <p className="lead">Son 24 preguntas. No hay tiempo límite y las siguientes se ajustan a cómo vas respondiendo. Al final ves tu nivel y qué conviene repasar.</p>

        <div className="actions">
          <button className="btn" type="button" onClick={async () => {
            try { go(await keycloakLogin()); } catch { setError("No pudimos iniciar sesión. Probá de nuevo."); }
          }}>Ingresar</button>
        </div>
        <p className="muted">Si llegaste desde tu aula virtual, abrí la actividad desde allí.</p>
        {error && <p className="error" role="alert">{error}</p>}

        {DEV && (
          <form className="dev" onSubmit={(e) => { e.preventDefault(); devLogin(sub.trim(), tenant.trim(), role); go(role); }}>
            <h2>Ingreso de desarrollo</h2>
            <label className="field"><span>Usuario</span><input value={sub} onChange={(e) => setSub(e.target.value)} /></label>
            <label className="field"><span>Escuela</span><input value={tenant} onChange={(e) => setTenant(e.target.value)} /></label>
            <label className="field"><span>Rol</span>
              <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
                <option value="student">Estudiante</option>
                <option value="teacher">Docente</option>
                <option value="admin">Administrador de contenido</option>
                <option value="network">Red de escuelas (jurisdicción)</option>
              </select>
            </label>
            <div className="actions"><button className="btn ghost" type="submit">Entrar como usuario de prueba</button></div>
          </form>
        )}
      </section>
    </Shell>
  );
}
