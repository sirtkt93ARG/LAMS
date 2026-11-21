"use client";
import { useMemo } from "react";
import katex from "katex";
import { mathToLatex } from "@/lib/mathToLatex";

export function MathPreview({ source }: { source: string }) {
  const html = useMemo(() => {
    if (!source.trim()) return "";
    return katex.renderToString(mathToLatex(source), { throwOnError: false, output: "html", trust: false });
  }, [source]);
  if (!html) return null;
  return (
    <div className="preview" aria-live="polite">
      <span className="preview-label">Así se ve lo que escribiste:</span>
      <span dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
