export function Explanation({ steps }: { steps: string[] }) {
  return (
    <section className="explanation" aria-label="Cómo se resuelve">
      <h3>Cómo se resuelve</h3>
      <ol>{steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
    </section>
  );
}
