"use client";
import { useEffect, useState } from "react";

/** Lee el enunciado en voz alta con la síntesis de voz del navegador (si está disponible). */
export function SpeakButton({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    setOk(typeof window !== "undefined" && "speechSynthesis" in window);
    return () => { if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel(); };
  }, [text]);

  if (!ok) return null;
  const toggle = () => {
    const synth = window.speechSynthesis;
    if (speaking) { synth.cancel(); setSpeaking(false); return; }
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "es-AR";
    u.onend = () => setSpeaking(false);
    setSpeaking(true);
    synth.speak(u);
  };
  return <button className="btn ghost small" type="button" onClick={toggle} aria-pressed={speaking}>{speaking ? "Detener lectura" : "Escuchar el enunciado"}</button>;
}
