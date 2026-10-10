import { useEffect, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import type { DashboardResponse, YearComparisonResponse } from '../api/types';
import { deNumber } from '../lib/format';
import { chartColors } from '../lib/chart';
import { useApi } from '../lib/useApi';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';
import { DataTable } from '../components/DataTable';
import { MeterTabs } from '../components/MeterTabs';

function deviationCell(pct: number | null): React.ReactNode {
  if (pct === null) {
    return '-';
  }
  const className = pct > 0 ? 'deviation-pos' : pct < 0 ? 'deviation-neg' : '';
  const sign = pct > 0 ? '+' : '';
  return <span className={className}>{`${sign}${deNumber(pct, 1)} %`}</span>;
}

export function YearComparisonPage() {
  const dashboard = useApi<DashboardResponse>('/ui-api/dashboard');
  const currentYear = new Date().getFullYear();
  const [meterId, setMeterId] = useState<number | null>(null);
  const [year, setYear] = useState<number>(currentYear);

  useEffect(() => {
    if (dashboard.data && meterId === null && dashboard.data.meters.length > 0) {
      setMeterId(dashboard.data.meters[0]?.id ?? null);
    }
  }, [dashboard.data, meterId]);

  const comparison = useApi<YearComparisonResponse>(
    meterId !== null ? `/ui-api/meters/${meterId}/year-comparison?year=${year}` : null,
  );

  if (dashboard.loading) return <LoadingSpinner />;
  if (dashboard.error) return <ErrorBanner message={dashboard.error} onRetry={dashboard.reload} />;
  if (!dashboard.data || dashboard.data.meters.length === 0) {
    return <div className="empty-state">Keine Zähler vorhanden.</div>;
  }

  const years = Array.from({ length: 6 }, (_, i) => currentYear - i);
  const data = comparison.data;
  const unit = data?.meter.unit ?? '';

  return (
    <>
      <div className="page-header">
        <h1>Jahresvergleich</h1>
      </div>

      <MeterTabs meters={dashboard.data.meters} selectedId={meterId} onSelect={setMeterId} />

      <div className="selector-row">
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          aria-label="Jahr auswählen"
        >
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>

      {comparison.loading && <LoadingSpinner />}
      {comparison.error && <ErrorBanner message={comparison.error} onRetry={comparison.reload} />}

      {data && (
        <>
          <div className="chart-container">
            <Bar
              data={{
                labels: data.months.map((m) => m.label_short),
                datasets: [
                  {
                    label: String(data.previous_year),
                    data: data.months.map((m) => m.previous.consumption),
                    backgroundColor: chartColors.sandMedium,
                  },
                  {
                    label: String(data.year),
                    data: data.months.map((m) => m.current.consumption),
                    backgroundColor: chartColors.sandAccent,
                  },
                ],
              }}
              options={{
                plugins: {
                  tooltip: {
                    callbacks: {
                      label: (ctx) =>
                        `${ctx.dataset.label ?? ''}: ${deNumber(ctx.parsed.y)} ${unit}`,
                    },
                  },
                },
                scales: {
                  y: { beginAtZero: true },
                },
              }}
            />
          </div>

          <DataTable>
            <thead>
              <tr>
                <th>Monat</th>
                <th className="num">
                  Vorjahr ({data.previous_year}, {unit})
                </th>
                <th className="num">
                  Aktuell ({data.year}, {unit})
                </th>
                <th className="num">Abweichung</th>
              </tr>
            </thead>
            <tbody>
              {data.months.map((m) => (
                <tr key={m.month} className={m.is_current_month ? 'muted' : ''}>
                  <td>
                    {m.label_short}
                    {m.is_current_month ? ' (laufend)' : ''}
                  </td>
                  <td className="num">{deNumber(m.previous.consumption)}</td>
                  <td className="num">{deNumber(m.current.consumption)}</td>
                  <td className="num">{deviationCell(m.deviation_pct)}</td>
                </tr>
              ))}
              <tr className="totals">
                <td>Gesamt</td>
                <td className="num">{deNumber(data.totals.previous)}</td>
                <td className="num">{deNumber(data.totals.current)}</td>
                <td className="num">{deviationCell(data.totals.deviation_pct)}</td>
              </tr>
            </tbody>
          </DataTable>
        </>
      )}
    </>
  );
}
