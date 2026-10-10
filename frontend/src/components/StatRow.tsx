import type { ReactNode } from 'react';

export function StatRow({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="stat-row">
      <span className="stat-label">{label}</span>
      <span className="stat-value">
        {value}
        {hint && <span className="stat-hint"> ({hint})</span>}
      </span>
    </div>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="stat-tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {hint && <div className="tile-hint">{hint}</div>}
    </div>
  );
}
