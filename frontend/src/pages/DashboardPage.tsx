import type { DashboardResponse } from '../api/types';
import { useApi } from '../lib/useApi';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';
import { MeterCard } from '../components/MeterCard';

export function DashboardPage() {
  const { data, loading, error, reload } = useApi<DashboardResponse>('/ui-api/dashboard');

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data || data.meters.length === 0) {
    return <div className="empty-state">Keine Zähler vorhanden.</div>;
  }

  return (
    <>
      <div className="page-header">
        <h1>Übersicht</h1>
      </div>
      <div className="card-grid">
        {data.meters.map((meter) => (
          <MeterCard key={meter.id} meter={meter} />
        ))}
      </div>
    </>
  );
}
