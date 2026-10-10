import { useState } from 'react';
import { api, ApiError } from '../api/client';
import type { DashboardMeter, DashboardResponse } from '../api/types';
import { useApi } from '../lib/useApi';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';

function MeterSettingsCard({ meter, onSaved }: { meter: DashboardMeter; onSaved: () => void }) {
  const [name, setName] = useState(meter.name);
  const [serial, setSerial] = useState(meter.serial_number ?? '');
  const [overlay, setOverlay] = useState(meter.weather_overlay);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (name.trim() === '') {
      setError('Der Name darf nicht leer sein.');
      return;
    }
    setSaving(true);
    setSuccess(false);
    try {
      await api.patch(`/ui-api/meters/${meter.id}`, {
        name: name.trim(),
        serial_number: serial.trim(),
      });
      setError(null);
      setSuccess(true);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
    } finally {
      setSaving(false);
    }
  };

  const toggleOverlay = async (checked: boolean) => {
    setOverlay(checked);
    try {
      await api.patch(`/ui-api/meters/${meter.id}`, { weather_overlay: checked });
      setError(null);
    } catch (err) {
      setOverlay(!checked);
      setError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
    }
  };

  return (
    <section className="card">
      <h2>
        {meter.name} <span className="meter-unit">({meter.unit})</span>
      </h2>
      {error && <ErrorBanner message={error} />}
      {success && <div className="success-banner">Gespeichert.</div>}

      <div className="form-field">
        <label htmlFor={`name-${meter.id}`}>Name</label>
        <input
          id={`name-${meter.id}`}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor={`serial-${meter.id}`}>Zählernummer</label>
        <input
          id={`serial-${meter.id}`}
          type="text"
          value={serial}
          onChange={(e) => setSerial(e.target.value)}
        />
      </div>
      <div className="form-field">
        <div className="toggle-row">
          <label htmlFor={`overlay-${meter.id}`} style={{ margin: 0 }}>
            Temperatur-Overlay (Gas)
          </label>
          <span className="switch">
            <input
              id={`overlay-${meter.id}`}
              type="checkbox"
              checked={overlay}
              onChange={(e) => void toggleOverlay(e.target.checked)}
            />
            <span className="slider" aria-hidden="true" />
          </span>
        </div>
      </div>
      <div className="form-actions">
        <button type="button" className="btn btn-primary" onClick={() => void save()} disabled={saving}>
          {saving ? 'Speichern …' : 'Speichern'}
        </button>
      </div>
    </section>
  );
}

export function SettingsPage() {
  const { data, loading, error, reload } = useApi<DashboardResponse>('/ui-api/dashboard');

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data || data.meters.length === 0) {
    return <div className="empty-state">Keine Zähler vorhanden.</div>;
  }

  return (
    <>
      <div className="page-header">
        <h1>Einstellungen</h1>
      </div>

      {data.meters.map((meter) => (
        <MeterSettingsCard key={meter.id} meter={meter} onSaved={() => undefined} />
      ))}

      <section className="card">
        <h2>Weitere Bereiche</h2>
        <ul>
          <li>
            <a href="/admin/">Datenexport/-import (Admin)</a>
          </li>
          <li>
            <a href="/pwa/">Mobile App (PWA)</a>
          </li>
          <li>
            <a href="/apidocs/">API-Dokumentation</a>
          </li>
        </ul>
      </section>
    </>
  );
}
