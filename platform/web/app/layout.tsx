import type { Metadata } from "next";
import { Atkinson_Hyperlegible } from "next/font/google";
import "katex/dist/katex.min.css";
import "./globals.css";

const ui = Atkinson_Hyperlegible({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-ui", display: "swap" });

export const metadata: Metadata = {
  title: { default: "matheval — evaluación adaptativa de matemática", template: "%s | matheval" },
  description: "Practicá matemática con problemas de la vida real y conocé tu nivel.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR" className={ui.variable}>
      <body>{children}</body>
    </html>
  );
}
