import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Chart } from 'react-chartjs-2';
import type { ChartData, ChartDataset, ChartOptions } from 'chart.js';
import type { ConsumptionResponse, WeatherResponse } from '../api/types';
import { deNumber } from '../lib/format';
import { chartColors } from '../lib/chart';
import { useApi } from '../lib/useApi';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';

export function GraphDetailPage() {
  const { id } = useParams<{ id: string }>();
  const meterId = Number(id);
  const [perHgt, setPerHgt] = useState(false);

  const consumption = useApi<ConsumptionResponse>(
    Number.isFinite(meterId) ? `/ui-api/meters/${meterId}/consumption?months=36` : null,
  );
  const weatherEnabled = consumption.data?.meter.weather_overlay === true;
  const weather = useApi<WeatherResponse>(
    weatherEnabled ? `/ui-api/meters/${meterId}/weather?months=36` : null,
  );

  if (consumption.loading) return <LoadingSpinner />;
  if (consumption.error) {
    return <ErrorBanner message={consumption.error} onRetry={consumption.reload} />;
  }
  if (!consumption.data) {
    return <div className="empty-state">Keine Daten vorhanden</div>;
  }

  const meter = consumption.data.meter;
  const unit = meter.unit;
  const series = consumption.data.series;
  const weatherSeries = weather.data?.series ?? [];
  const hasWeatherData = weatherSeries.some(
    (p) => p.temp_avg !== null || p.consumption_per_hgt !== null,
  );
  const hasHgtData = weatherSeries.some((p) => p.consumption_per_hgt !== null);
  const showToggle = weatherEnabled && hasHgtData;

  let chartData: ChartData<'bar' | 'line', (number | null)[], string>;
  let yTitle: string;

  if (perHgt && showToggle) {
    yTitle = `${unit}/HGT`;
    chartData = {
      labels: weatherSeries.map((p) => p.label),
      datasets: [
        {
          type: 'bar' as const,
          label: 'Verbrauch je Heizgradtag',
          data: weatherSeries.map((p) => p.consumption_per_hgt),
          backgroundColor: chartColors.sandAccent,
          yAxisID: 'y',
        },
      ],
    };
  } else {
    yTitle = unit;
    const datasets: ChartDataset<'bar' | 'line', (number | null)[]>[] = [
      {
        type: 'bar' as const,
        label: 'Verbrauch',
        data: series.map((p) => p.consumption),
        backgroundColor: chartColors.sandDark,
        hoverBackgroundColor: chartColors.sandAccent,
        yAxisID: 'y',
      },
    ];
    if (weatherEnabled && hasWeatherData) {
      datasets.push({
        type: 'line' as const,
        label: 'Ø Temperatur',
        data: weatherSeries.map((p) => p.temp_avg),
        borderColor: chartColors.temperature,
        backgroundColor: chartColors.temperature,
        pointRadius: 2,
        tension: 0.3,
        yAxisID: 'yTemp',
        spanGaps: true,
      });
    }
    chartData = {
      labels: series.map((p) => p.label),
      datasets,
    };
  }

  const options: ChartOptions<'bar' | 'line'> = {
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const suffix = ctx.dataset.yAxisID === 'yTemp' ? '°C' : perHgt ? `${unit}/HGT` : unit;
            return `${ctx.dataset.label ?? ''}: ${deNumber(ctx.parsed.y)} ${suffix}`;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        position: 'left',
        title: { display: true, text: yTitle },
      },
      ...(!perHgt && weatherEnabled && hasWeatherData
        ? {
            yTemp: {
              position: 'right' as const,
              title: { display: true, text: '°C' },
              grid: { drawOnChartArea: false },
            },
          }
        : {}),
    },
  };

  return (
    <>
      <div className="page-header">
        <h1>
          Grafik: {meter.name} <span className="meter-unit">({unit})</span>
        </h1>
      </div>

      {weather.error && <ErrorBanner message={weather.error} onRetry={weather.reload} />}
      {weather.loading && <LoadingSpinner text="Lade Wetterdaten …" />}

      {showToggle && (
        <div className="card">
          <div className="toggle-row">
            <label htmlFor="hgt-toggle" style={{ margin: 0 }}>
              Witterungsbereinigt
            </label>
            <span className="switch">
              <input
                id="hgt-toggle"
                type="checkbox"
                checked={perHgt}
                onChange={(e) => setPerHgt(e.target.checked)}
              />
              <span className="slider" aria-hidden="true" />
            </span>
          </div>
          {perHgt && (
            <p className="form-hint">Verbrauch je Heizgradtag (Basis 15 °C)</p>
          )}
        </div>
      )}

      {series.length === 0 ? (
        <div className="empty-state">Noch keine Verbrauchsdaten vorhanden</div>
      ) : (
        <div className="chart-container">
          <Chart type="bar" data={chartData} options={options} />
        </div>
      )}
    </>
  );
}
