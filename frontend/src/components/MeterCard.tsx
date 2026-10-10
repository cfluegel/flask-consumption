import { Link } from 'react-router-dom';
import type { DashboardMeter, ForecastMethod } from '../api/types';
import { deNumber, euro, formatDateDe } from '../lib/format';
import { StatRow } from './StatRow';

const methodLabels: Record<ForecastMethod, string> = {
  calculated: 'Berechnet',
  seasonal: 'Saison',
  weighted: 'Trend',
};

function withUnit(value: number | null, unit: string): string {
  if (value === null) {
    return '-';
  }
  return `${deNumber(value)} ${unit}`;
}

export function MeterCard({ meter }: { meter: DashboardMeter }) {
  const { stats, last_reading: lastReading } = meter;
  const forecast = stats.forecast_cost;

  return (
    <div className="card meter-card">
      <div className="meter-card-header">
        <h2>{meter.name}</h2>
        <span className="meter-unit">{meter.unit}</span>
      </div>

      <div className="last-reading">
        {lastReading ? (
          <>
            <div className="value">
              {deNumber(lastReading.value)} {meter.unit}
            </div>
            <div className="date">Letzte Ablesung am {formatDateDe(lastReading.reading_date)}</div>
          </>
        ) : (
          <div className="date">Noch keine Ablesungen vorhanden</div>
        )}
      </div>

      <div className="stat-group">
        <div className="stat-group-title">Statistik</div>
        <StatRow label="3-Monats-Ø" value={withUnit(stats.avg_3month, meter.unit)} />
        <StatRow label="Jahresverbrauch" value={withUnit(stats.yearly_consumption, meter.unit)} />
      </div>

      <div className="stat-group">
        <div className="stat-group-title">Prognose</div>
        <StatRow label="Berechnet" value={withUnit(stats.pred_calculated, meter.unit)} />
        <StatRow label="Trend" value={withUnit(stats.pred_weighted, meter.unit)} />
        <StatRow label="Saison" value={withUnit(stats.pred_seasonal, meter.unit)} />
      </div>

      <div className="stat-group">
        <div className="stat-group-title">Kosten</div>
        <StatRow label="Jahreskosten" value={euro(stats.yearly_cost)} />
        <StatRow
          label="Prognose akt. Monat"
          value={euro(forecast?.cost ?? null)}
          {...(forecast && forecast.cost !== null ? { hint: methodLabels[forecast.method] } : {})}
        />
      </div>

      <div className="card-actions">
        <Link to={`/ablesung/neu?meter=${meter.id}`} className="btn btn-primary btn-small">
          Ablesung erfassen
        </Link>
        <Link to={`/zaehler/${meter.id}`} className="btn btn-secondary btn-small">
          Details
        </Link>
        <Link to={`/grafiken/${meter.id}`} className="btn btn-secondary btn-small">
          Grafik
        </Link>
      </div>
    </div>
  );
}
