export function LoadingSpinner({ text = 'Lade Daten …' }: { text?: string }) {
  return (
    <div className="spinner-wrap" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}
