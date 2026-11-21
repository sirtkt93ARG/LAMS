/** Convierte lo que escribe el estudiante (200*n, 3/4, 2^3, 1,5) en LaTeX para la vista previa. Solo presentación:
 *  la corrección la hace siempre el servidor. */
export function mathToLatex(src: string): string {
  let s = src.trim().slice(0, 80).replace(/\$/g, "");
  s = s.replace(/(\d)\s*,\s*(\d)/g, "$1{,}$2");
  s = s.replace(/[*×·]/g, " \\cdot ");
  s = s.replace(/(\d+|[a-zA-Z])\s*\/\s*(\d+|[a-zA-Z])/g, "\\frac{$1}{$2}");
  s = s.replace(/\^(\d+|[a-zA-Z])/g, "^{$1}");
  return s;
}
