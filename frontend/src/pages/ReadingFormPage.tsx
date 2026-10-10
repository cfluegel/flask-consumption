import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { DashboardResponse, Reading } from '../api/types';
import { deNumber, formatDateDe, parseDeNumber } from '../lib/format';
import { useApi } from '../lib/useApi';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

export function ReadingFormPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useApi<DashboardResponse>('/ui-api/dashboard');

  const [meterId, setMeterId] = useState<string>(searchParams.get('meter') ?? '');
  const [date, setDate] = useState<string>(todayIso());
  const [value, setValue] = useState('');
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (data && meterId === '' && data.meters.length > 0) {
      setMeterId(String(data.meters[0]?.id ?? ''));
    }
  }, [data, meterId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data || data.meters.length === 0) {
    return <div className="empty-state">Keine Zähler vorhanden.</div>;
  }

  const selectedMeter = data.meters.find((m) => String(m.id) === meterId);
  const lastReading: Reading | null = selectedMeter?.last_reading ?? null;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitError(null);
    const numericValue = parseDeNumber(value);
    if (!meterId) {
      setSubmitError('Bitte einen Zähler auswählen.');
      return;
    }
    if (!date) {
      setSubmitError('Bitte ein Datum angeben.');
      return;
    }
    if (numericValue === null) {
      setSubmitError('Bitte einen gültigen Zählerstand eingeben (z. B. 12.345,67).');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/ui-api/readings', {
        meter_id: Number(meterId),
        reading_date: date,
        value: numericValue,
      });
      navigate(`/zaehler/${meterId}`);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h1>Neue Ablesung</h1>
      </div>
      <div className="card">
        {submitError && <ErrorBanner message={submitError} />}
        <form onSubmit={(e) => void handleSubmit(e)}>
          <div className="form-field">
            <label htmlFor="meter">Zähler</label>
            <select id="meter" value={meterId} onChange={(e) => setMeterId(e.target.value)}>
              {data.meters.map((meter) => (
                <option key={meter.id} value={meter.id}>
                  {meter.name} ({meter.unit})
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="date">Datum</label>
            <input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>

          <div className="form-field">
            <label htmlFor="value">Zählerstand {selectedMeter ? `(${selectedMeter.unit})` : ''}</label>
            <input
              id="value"
              type="text"
              inputMode="decimal"
              placeholder="z. B. 12.345,67"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
            />
            {lastReading && (
              <p className="form-hint">
                Letzte Ablesung: {deNumber(lastReading.value)} am {formatDateDe(lastReading.reading_date)}
              </p>
            )}
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Speichern …' : 'Speichern'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>
              Abbrechen
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
