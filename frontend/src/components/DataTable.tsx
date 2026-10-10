import type { ReactNode } from 'react';

/** Wraps a table in a horizontally scrollable container. */
export function DataTable({ children }: { children: ReactNode }) {
  return (
    <div className="table-wrap">
      <table>{children}</table>
    </div>
  );
}
