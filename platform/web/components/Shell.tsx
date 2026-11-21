"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearAuth, getAuth } from "@/lib/auth";
import { A11yPanel } from "./A11yPanel";

export function Shell({ children, showExit = true }: { children: React.ReactNode; showExit?: boolean }) {
  const router = useRouter();
  const auth = typeof window !== "undefined" ? getAuth() : null;
  const signedIn = !!auth;
  const links: [string, string][] = !auth ? [] : auth.role === "student"
    ? [["/practice", "Práctica"], ["/progress", "Mi progreso"], ["/observatory", "Observatorio"]]
    : auth.role === "network" ? [["/network", "Red"], ["/observatory", "Observatorio"]]
    : auth.role === "admin"
      ? [["/teacher", "Panel"], ["/review", "Curaduría"], ["/analysis", "Análisis"], ["/observatory", "Observatorio"]]
      : [["/teacher", "Panel"], ["/observatory", "Observatorio"]];
  return (
    <>
      <a className="skip" href="#contenido">Saltar al contenido</a>
      <header className="topbar">
        <Link href="/" className="brand">[Nombre del producto]</Link>
        <nav className="topnav" aria-label="Secciones">{links.map(([href, label]) => <Link key={href} href={href}>{label}</Link>)}</nav>
        <div className="topbar-right">
          <A11yPanel />
          {showExit && signedIn && (
            <button className="btn ghost small" type="button" onClick={() => { clearAuth(); router.replace("/"); }}>Salir</button>
          )}
        </div>
      </header>
      <main id="contenido" className="page">{children}</main>
    </>
  );
}
