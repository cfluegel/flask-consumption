import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { ConsumptionResponse, Reading, ReadingsResponse } from '../api/types';
import { deNumber, formatDateDe, parseDeNumber } from '../lib/format';
import { useApi } from '../lib/useApi';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { DataTable } from '../components/DataTable';

const PAGE_SIZE = 12;

export function MeterDetailPage() {
  const { id } = useParams<{ id: string }>();
  const meterId = Number(id);

  const [readings, setReadings] = useState<Reading[]>([]);
  const [total, setTotal] = useState(0);
  const [meterName, setMeterName] = useState('');
  const [meterUnit, setMeterUnit] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Reading | null>(null);
  const [editTarget, setEditTarget] = useState<Reading | null>(null);
  const [editDate, setEditDate] = useState('');
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  const consumption = useApi<ConsumptionResponse>(
    Number.isFinite(meterId) ? `/ui-api/meters/${meterId}/consumption?months=12` : null,
  );

  const loadPage = useCallback(
    async (offset: number, replace: boolean) => {
      try {
        const data = await api.get<ReadingsResponse>(
          `/ui-api/meters/${meterId}/readings?limit=${PAGE_SIZE}&offset=${offset}`,
        );
        setMeterName(data.meter.name);
        setMeterUnit(data.meter.unit);
        setTotal(data.total);
        setReadings((prev) => (replace ? data.readings : [...prev, ...data.readings]));
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
      }
    },
    [meterId],
  );

  const reloadAll = useCallback(() => {
    setLoading(true);
    void loadPage(0, true).finally(() => setLoading(false));
  }, [loadPage]);

  useEffect(() => {
    reloadAll();
  }, [reloadAll]);

  const loadMore = async () => {
    setLoadingMore(true);
    await loadPage(readings.length, false);
    setLoadingMore(false);
  };

  const startEdit = (reading: Reading) => {
    setActionError(null);
    setEditTarget(reading);
    setEditDate(reading.reading_date);
    setEditValue(deNumber(reading.value));
  };

  const saveEdit = async () => {
    if (!editTarget) return;
    const value = parseDeNumber(editValue);
    if (value === null) {
      setActionError('Bitte einen gültigen Zählerstand eingeben.');
      return;
    }
    setSaving(true);
    try {
      await api.put(`/ui-api/readings/${editTarget.id}`, {
        reading_date: editDate,
        value,
      });
      setEditTarget(null);
      setActionError(null);
      reloadAll();
      consumption.reload();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.del(`/ui-api/readings/${deleteTarget.id}`);
      setDeleteTarget(null);
      setActionError(null);
      reloadAll();
      consumption.reload();
    } catch (err) {
      setDeleteTarget(null);
      setActionError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBanner message={error} onRetry={reloadAll} />;

  const monthly = consumption.data ? [...consumption.data.series].reverse() : [];

  return (
    <>
      <div className="page-header">
        <h1>
          {meterName} <span className="meter-unit">({meterUnit})</span>
        </h1>
        <Link to={`/ablesung/neu?meter=${meterId}`} className="btn btn-primary">
          Neue Ablesung
        </Link>
      </div>

      {actionError && <ErrorBanner message={actionError} />}

      <h2>Ablesungen</h2>
      {readings.length === 0 ? (
        <div className="empty-state">Noch keine Ablesungen vorhanden</div>
      ) : (
        <>
          <DataTable>
            <thead>
              <tr>
                <th>Datum</th>
                <th className="num">Zählerstand ({meterUnit})</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {readings.map((reading) =>
                editTarget && editTarget.id === reading.id ? (
                  <tr key={reading.id}>
                    <td>
                      <input
                        type="date"
                        value={editDate}
                        onChange={(e) => setEditDate(e.target.value)}
                        aria-label="Datum"
                      />
                    </td>
                    <td className="num">
                      <input
                        type="text"
                        inputMode="decimal"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        aria-label="Zählerstand"
                      />
                    </td>
                    <td>
                      <div className="actions-cell">
                        <button
                          type="button"
                          className="btn btn-primary btn-small"
                          onClick={() => void saveEdit()}
                          disabled={saving}
                        >
                          Speichern
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-small"
                          onClick={() => setEditTarget(null)}
                        >
                          Abbrechen
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={reading.id}>
                    <td>{formatDateDe(reading.reading_date)}</td>
                    <td className="num">{deNumber(reading.value)}</td>
                    <td>
                      <div className="actions-cell">
                        <button
                          type="button"
                          className="btn btn-secondary btn-small"
                          onClick={() => startEdit(reading)}
                        >
                          Bearbeiten
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger btn-small"
                          onClick={() => setDeleteTarget(reading)}
                        >
                          Löschen
                        </button>
                      </div>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </DataTable>
          {readings.length < total && (
            <div className="mt-1">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => void loadMore()}
                disabled={loadingMore}
              >
                {loadingMore ? 'Lade …' : 'Mehr laden'}
              </button>
            </div>
          )}
        </>
      )}

      <h2 className="mt-1">Monatlicher Verbrauch (letzte 12 Monate)</h2>
      {consumption.loading && <LoadingSpinner />}
      {consumption.error && <ErrorBanner message={consumption.error} onRetry={consumption.reload} />}
      {consumption.data &&
        (monthly.length === 0 ? (
          <div className="empty-state">Keine Verbrauchsdaten vorhanden</div>
        ) : (
          <DataTable>
            <thead>
              <tr>
                <th>Monat</th>
                <th className="num">Verbrauch ({meterUnit})</th>
              </tr>
            </thead>
            <tbody>
              {monthly.map((point) => (
                <tr key={`${point.year}-${point.month}`}>
                  <td>{point.label}</td>
                  <td className="num">{deNumber(point.consumption)}</td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        ))}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Ablesung löschen"
        message={
          deleteTarget
            ? `Ablesung vom ${formatDateDe(deleteTarget.reading_date)} (${deNumber(deleteTarget.value)} ${meterUnit}) wirklich löschen?`
            : ''
        }
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
