import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../api';
import './Catalog.css';

const SLOT_MINUTES = 45;

interface Provider {
  provider_id: string;
  name: string;
  specialty: string;
  color: string;
}

interface Procedure {
  procedure_id: string;
  name: string;
  duration_minutes: number;
  color: string;
}

function slotCount(duration: number): number {
  return Math.max(1, Math.ceil(duration / SLOT_MINUTES));
}

function durationLabel(duration: number): string {
  const n = slotCount(duration);
  return `${duration} min (${n} slot${n === 1 ? '' : 's'})`;
}

export default function Catalog() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [procedures, setProcedures] = useState<Procedure[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [pName, setPName] = useState('');
  const [pSpecialty, setPSpecialty] = useState('');
  const [pColor, setPColor] = useState('#0e8f6a');
  const [savingProvider, setSavingProvider] = useState(false);

  const [prName, setPrName] = useState('');
  const [prDuration, setPrDuration] = useState(45);
  const [prColor, setPrColor] = useState('#2f7fd1');
  const [savingProcedure, setSavingProcedure] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get<Provider[]>('/api/catalog/providers'),
      api.get<Procedure[]>('/api/catalog/procedures'),
    ])
      .then(([pv, pr]) => {
        setProviders(pv);
        setProcedures(pr);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const addProvider = async (e: FormEvent) => {
    e.preventDefault();
    if (!pName.trim()) return;
    setSavingProvider(true);
    setError('');
    try {
      const created = await api.post<Provider>('/api/catalog/providers', {
        name: pName.trim(),
        specialty: pSpecialty.trim(),
        color: pColor,
      });
      setProviders((prev) =>
        [...prev, created].sort((a, b) => a.name.localeCompare(b.name))
      );
      setPName('');
      setPSpecialty('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSavingProvider(false);
    }
  };

  const addProcedure = async (e: FormEvent) => {
    e.preventDefault();
    if (!prName.trim()) return;
    setSavingProcedure(true);
    setError('');
    try {
      const created = await api.post<Procedure>('/api/catalog/procedures', {
        name: prName.trim(),
        duration_minutes: prDuration,
        color: prColor,
      });
      setProcedures((prev) =>
        [...prev, created].sort(
          (a, b) => a.duration_minutes - b.duration_minutes || a.name.localeCompare(b.name)
        )
      );
      setPrName('');
      setPrDuration(45);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSavingProcedure(false);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Providers &amp; procedures</h1>
          <p className="page-sub">
            Manage the clinic catalog. Bookings reserve consecutive 45-minute slots
            based on each procedure&apos;s duration.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Providers</h2>
          <span className="count-pill">{providers.length}</span>
        </div>
        <p className="panel-note">Availability is managed per provider on the Schedule page.</p>

        <form className="inline-form" onSubmit={addProvider}>
          <label className="field">
            <span>Name</span>
            <input
              value={pName}
              onChange={(e) => setPName(e.target.value)}
              placeholder="Dr. Jane Doe"
              required
            />
          </label>
          <label className="field">
            <span>Specialty</span>
            <input
              value={pSpecialty}
              onChange={(e) => setPSpecialty(e.target.value)}
              placeholder="General"
            />
          </label>
          <label className="field">
            <span>Color</span>
            <input
              className="catalog-color"
              type="color"
              value={pColor}
              onChange={(e) => setPColor(e.target.value)}
            />
          </label>
          <button className="btn btn-primary" disabled={savingProvider}>
            {savingProvider ? 'Adding…' : 'Add provider'}
          </button>
        </form>

        {loading ? (
          <div className="empty">Loading…</div>
        ) : providers.length === 0 ? (
          <div className="empty">No providers yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Specialty</th>
                <th>Color</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.provider_id}>
                  <td>{p.name}</td>
                  <td className="muted">{p.specialty || '—'}</td>
                  <td>
                    <span className="catalog-swatch-cell">
                      <span
                        className="catalog-swatch"
                        style={{ background: p.color }}
                      />
                      <span className="mono muted">{p.color}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Procedure types</h2>
          <span className="count-pill">{procedures.length}</span>
        </div>
        <p className="panel-note">
          Durations are multiples of {SLOT_MINUTES} minutes — one slot each.
        </p>

        <form className="inline-form" onSubmit={addProcedure}>
          <label className="field">
            <span>Name</span>
            <input
              value={prName}
              onChange={(e) => setPrName(e.target.value)}
              placeholder="Filling"
              required
            />
          </label>
          <label className="field">
            <span>Duration</span>
            <select
              value={prDuration}
              onChange={(e) => setPrDuration(Number(e.target.value))}
            >
              {[45, 90, 135, 180, 225].map((d) => (
                <option key={d} value={d}>
                  {durationLabel(d)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Color</span>
            <input
              className="catalog-color"
              type="color"
              value={prColor}
              onChange={(e) => setPrColor(e.target.value)}
            />
          </label>
          <button className="btn btn-primary" disabled={savingProcedure}>
            {savingProcedure ? 'Adding…' : 'Add procedure'}
          </button>
        </form>

        {loading ? (
          <div className="empty">Loading…</div>
        ) : procedures.length === 0 ? (
          <div className="empty">No procedure types yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Duration</th>
                <th>Color</th>
              </tr>
            </thead>
            <tbody>
              {procedures.map((p) => (
                <tr key={p.procedure_id}>
                  <td>{p.name}</td>
                  <td className="muted">{durationLabel(p.duration_minutes)}</td>
                  <td>
                    <span className="catalog-swatch-cell">
                      <span
                        className="catalog-swatch"
                        style={{ background: p.color }}
                      />
                      <span className="mono muted">{p.color}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
