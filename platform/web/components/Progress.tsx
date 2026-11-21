export function Progress({ answered, total }: { answered: number; total: number }) {
  const pct = total ? Math.round((answered / total) * 100) : 0;
  return (
    <div className="progress">
      <p>Pregunta {Math.min(answered + 1, total)} de {total}</p>
      <div className="track" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={answered} aria-label="Avance de la práctica">
        <div className="fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
