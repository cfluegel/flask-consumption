import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar } from 'react-chartjs-2';
import type { CostsResponse, DashboardResponse, ForecastMethod } from '../api/types';
import { deNumber, euro } from '../lib/format';
import { chartColors } from '../lib/chart';
import { useApi } from '../lib/useApi';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';
import { StatTile } from '../components/StatRow';
import { DataTable } from '../components/DataTable';
import { MeterTabs } from '../components/MeterTabs';

const methodLabels: Record<ForecastMethod, string> = {
  calculated: 'berechnet',
  seasonal: 'saisonal',
  weighted: 'gewichtet',
};

export function CostsPage() {
  const dashboard = useApi<DashboardResponse>('/ui-api/dashboard');
  const [meterId, setMeterId] = useState<number | null>(null);

  useEffect(() => {
    if (dashboard.data && meterId === null && dashboard.data.meters.length > 0) {
      setMeterId(dashboard.data.meters[0]?.id ?? null);
    }
  }, [dashboard.data, meterId]);

  const costs = useApi<CostsResponse>(
    meterId !== null ? `/ui-api/meters/${meterId}/costs?months=24` : null,
  );

  if (dashboard.loading) return <LoadingSpinner />;
  if (dashboard.error) return <ErrorBanner message={dashboard.error} onRetry={dashboard.reload} />;
  if (!dashboard.data || dashboard.data.meters.length === 0) {
    return <div className="empty-state">Keine Zähler vorhanden.</div>;
  }

  const data = costs.data;
  const unit = data?.meter.unit ?? '';
  const hasTariff = data ? data.series.some((p) => p.tariff_id !== null) : true;
  const chartPoints = data ? data.series.filter((p) => p.cost !== null) : [];

  return (
    <>
      <div className="page-header">
        <h1>Kosten</h1>
      </div>

      <MeterTabs meters={dashboard.data.meters} selectedId={meterId} onSelect={setMeterId} />

      {costs.loading && <LoadingSpinner />}
      {costs.error && <ErrorBanner message={costs.error} onRetry={costs.reload} />}

      {data && (
        <>
          {!hasTariff && (
            <div className="error-banner">
              <span>
                Keine Tarife hinterlegt – unter <Link to="/tarife">Tarife</Link> anlegen.
              </span>
            </div>
          )}

          <div className="stat-tiles">
            <StatTile label="Jahreskosten" value={euro(data.yearly_cost)} />
            <StatTile
              label="Monats-Prognose"
              value={euro(data.forecast?.cost ?? null)}
              {...(data.forecast ? { hint: `Methode: ${methodLabels[data.forecast.method]}` } : {})}
            />
          </div>

          {chartPoints.length > 0 && (
            <div className="chart-container">
              <Bar
                data={{
                  labels: chartPoints.map((p) => p.label),
                  datasets: [
                    {
                      label: 'Kosten',
                      data: chartPoints.map((p) => p.cost),
                      backgroundColor: chartColors.sandDark,
                      hoverBackgroundColor: chartColors.sandAccent,
                    },
                  ],
                }}
                options={{
                  plugins: {
                    legend: { display: false },
                    tooltip: {
                      callbacks: {
                        label: (ctx) => `Kosten: ${euro(ctx.parsed.y)}`,
                      },
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                      ticks: { callback: (v) => `${deNumber(Number(v), 0)} €` },
                    },
                  },
                }}
              />
            </div>
          )}

          {data.series.length === 0 ? (
            <div className="empty-state">Keine Kostendaten vorhanden</div>
          ) : (
            <DataTable>
              <thead>
                <tr>
                  <th>Monat</th>
                  <th className="num">Verbrauch ({unit})</th>
                  <th className="num">Arbeitspreis (€/{unit})</th>
                  <th className="num">Grundpreis (€/Monat)</th>
                  <th className="num">Kosten</th>
                </tr>
              </thead>
              <tbody>
                {[...data.series].reverse().map((point) => (
                  <tr key={`${point.year}-${point.month}`}>
                    <td>{point.label}</td>
                    <td className="num">{deNumber(point.consumption)}</td>
                    <td className="num">{deNumber(point.price_per_unit, 4)}</td>
                    <td className="num">{deNumber(point.base_price_monthly)}</td>
                    <td className="num">{euro(point.cost)}</td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </>
      )}
    </>
  );
}
