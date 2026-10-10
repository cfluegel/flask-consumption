import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../api/client';
import type { DashboardResponse, Meter, Tariff } from '../api/types';
import { deNumber, formatDateDe, parseDeNumber } from '../lib/format';
import { useApi } from '../lib/useApi';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { DataTable } from '../components/DataTable';

interface TariffFormState {
  name: string;
  pricePerUnit: string;
  basePriceMonthly: string;
  validFrom: string;
}

const emptyForm: TariffFormState = { name: '', pricePerUnit: '', basePriceMonthly: '', validFrom: '' };

function MeterTariffSection({ meter }: { meter: Meter }) {
  const [tariffs, setTariffs] = useState<Tariff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<TariffFormState>(emptyForm);
  const [deleteTarget, setDeleteTarget] = useState<Tariff | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<Tariff[]>(`/ui-api/meters/${meter.id}/tariffs`);
      setTariffs(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
    } finally {
      setLoading(false);
    }
  }, [meter.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCreate = () => {
    setEditId(null);
    setForm(emptyForm);
    setFormError(null);
    setShowForm(true);
  };

  const openEdit = (tariff: Tariff) => {
    setEditId(tariff.id);
    setForm({
      name: tariff.name ?? '',
      pricePerUnit: deNumber(tariff.price_per_unit, 4),
      basePriceMonthly: tariff.base_price_monthly !== null ? deNumber(tariff.base_price_monthly) : '',
      validFrom: tariff.valid_from,
    });
    setFormError(null);
    setShowForm(true);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const price = parseDeNumber(form.pricePerUnit);
    const basePrice = form.basePriceMonthly.trim() === '' ? null : parseDeNumber(form.basePriceMonthly);
    if (price === null) {
      setFormError('Bitte einen gültigen Arbeitspreis eingeben.');
      return;
    }
    if (form.basePriceMonthly.trim() !== '' && basePrice === null) {
      setFormError('Bitte einen gültigen Grundpreis eingeben.');
      return;
    }
    if (!form.validFrom) {
      setFormError('Bitte ein Gültigkeitsdatum angeben.');
      return;
    }
    const payload = {
      name: form.name.trim() === '' ? null : form.name.trim(),
      price_per_unit: price,
      base_price_monthly: basePrice,
      valid_from: form.validFrom,
    };
    setSaving(true);
    try {
      if (editId === null) {
        await api.post(`/ui-api/meters/${meter.id}/tariffs`, payload);
      } else {
        await api.put(`/ui-api/tariffs/${editId}`, payload);
      }
      setShowForm(false);
      setFormError(null);
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setFormError('Für dieses Datum existiert bereits ein Tarif');
      } else {
        setFormError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
      }
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.del(`/ui-api/tariffs/${deleteTarget.id}`);
      setDeleteTarget(null);
      await load();
    } catch (err) {
      setDeleteTarget(null);
      setError(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
    }
  };

  return (
    <section className="card">
      <div className="page-header">
        <h2>
          {meter.name} <span className="meter-unit">({meter.unit})</span>
        </h2>
        <button type="button" className="btn btn-primary btn-small" onClick={openCreate}>
          Tarif hinzufügen
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}

      {!loading && !error && (
        tariffs.length === 0 ? (
          <p className="text-secondary">Noch keine Tarife hinterlegt.</p>
        ) : (
          <DataTable>
            <thead>
              <tr>
                <th>Gültig ab</th>
                <th>Name</th>
                <th className="num">Arbeitspreis (€/{meter.unit})</th>
                <th className="num">Grundpreis (€/Monat)</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {tariffs.map((tariff) => (
                <tr key={tariff.id}>
                  <td>{formatDateDe(tariff.valid_from)}</td>
                  <td>{tariff.name ?? '-'}</td>
                  <td className="num">{deNumber(tariff.price_per_unit, 4)}</td>
                  <td className="num">{deNumber(tariff.base_price_monthly)}</td>
                  <td>
                    <div className="actions-cell">
                      <button
                        type="button"
                        className="btn btn-secondary btn-small"
                        onClick={() => openEdit(tariff)}
                      >
                        Bearbeiten
                      </button>
                      <button
                        type="button"
                        className="btn btn-danger btn-small"
                        onClick={() => setDeleteTarget(tariff)}
                      >
                        Löschen
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )
      )}

      {showForm && (
        <form onSubmit={(e) => void submit(e)} className="mt-1">
          <h3>{editId === null ? 'Neuer Tarif' : 'Tarif bearbeiten'}</h3>
          {formError && <ErrorBanner message={formError} />}
          <div className="form-field">
            <label htmlFor={`name-${meter.id}`}>Name (optional)</label>
            <input
              id={`name-${meter.id}`}
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div className="form-field">
            <label htmlFor={`price-${meter.id}`}>Arbeitspreis (€/{meter.unit})</label>
            <input
              id={`price-${meter.id}`}
              type="text"
              inputMode="decimal"
              placeholder="z. B. 0,3245"
              value={form.pricePerUnit}
              onChange={(e) => setForm({ ...form, pricePerUnit: e.target.value })}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor={`base-${meter.id}`}>Grundpreis (€/Monat)</label>
            <input
              id={`base-${meter.id}`}
              type="text"
              inputMode="decimal"
              placeholder="z. B. 9,90"
              value={form.basePriceMonthly}
              onChange={(e) => setForm({ ...form, basePriceMonthly: e.target.value })}
            />
          </div>
          <div className="form-field">
            <label htmlFor={`valid-${meter.id}`}>Gültig ab</label>
            <input
              id={`valid-${meter.id}`}
              type="date"
              value={form.validFrom}
              onChange={(e) => setForm({ ...form, validFrom: e.target.value })}
              required
            />
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Speichern …' : 'Speichern'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
              Abbrechen
            </button>
          </div>
        </form>
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Tarif löschen"
        message={
          deleteTarget
            ? `Tarif gültig ab ${formatDateDe(deleteTarget.valid_from)} wirklich löschen?`
            : ''
        }
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </section>
  );
}

export function TariffsPage() {
  const dashboard = useApi<DashboardResponse>('/ui-api/dashboard');

  if (dashboard.loading) return <LoadingSpinner />;
  if (dashboard.error) return <ErrorBanner message={dashboard.error} onRetry={dashboard.reload} />;
  if (!dashboard.data || dashboard.data.meters.length === 0) {
    return <div className="empty-state">Keine Zähler vorhanden.</div>;
  }

  return (
    <>
      <div className="page-header">
        <h1>Tarife</h1>
      </div>
      {dashboard.data.meters.map((meter) => (
        <MeterTariffSection key={meter.id} meter={meter} />
      ))}
    </>
  );
}
