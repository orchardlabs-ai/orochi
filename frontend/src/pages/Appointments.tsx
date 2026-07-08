import { useEffect, useState, type FormEvent } from 'react';
import { api, type Patient } from '../api';

type ApptStatus = 'scheduled' | 'confirmed' | 'cancelled';
const STATUSES: ApptStatus[] = ['scheduled', 'confirmed', 'cancelled'];

interface Appointment {
  appointment_id: string;
  patient_uuid: string;
  patient_name?: string;
  datetime: string;
  location: string;
  status: ApptStatus;
  created_at: string;
  provider_id?: string | null;
  provider_name?: string | null;
  procedure_id?: string | null;
  procedure_name?: string | null;
  duration_minutes?: number | null;
}

interface CatalogProvider {
  provider_id: string;
  name: string;
  specialty?: string;
  color?: string;
}

interface CatalogProcedure {
  procedure_id: string;
  name: string;
  duration_minutes: number;
  color?: string;
}

export default function Appointments() {
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [providers, setProviders] = useState<CatalogProvider[]>([]);
  const [procedures, setProcedures] = useState<CatalogProcedure[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [patientUuid, setPatientUuid] = useState('');
  const [providerId, setProviderId] = useState('');
  const [procedureId, setProcedureId] = useState('');
  const [datetime, setDatetime] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get<Appointment[]>('/api/appointments'),
      api.get<Patient[]>('/api/patients'),
      api.get<CatalogProvider[]>('/api/catalog/providers'),
      api.get<CatalogProcedure[]>('/api/catalog/procedures'),
    ])
      .then(([a, p, prov, proc]) => {
        setAppts(a);
        setPatients(p);
        setProviders(prov);
        setProcedures(proc);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    if (!patientUuid || !providerId || !procedureId || !datetime) return;
    setSaving(true);
    setError('');
    try {
      await api.post<Appointment>('/api/appointments', {
        patient_uuid: patientUuid,
        provider_id: providerId,
        procedure_id: procedureId,
        datetime: new Date(datetime).toISOString(),
      });
      setDatetime('');
      setProcedureId('');
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (id: string, status: ApptStatus) => {
    setError('');
    try {
      const updated = await api.patch<Appointment>(`/api/appointments/${id}`, { status });
      setAppts((prev) => prev.map((a) => (a.appointment_id === id ? { ...a, ...updated } : a)));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Appointments</h1>
          <p className="page-sub">Schedule and manage patient appointments.</p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>New appointment</h2>
        </div>
        <form className="inline-form" onSubmit={create}>
          <label className="field">
            <span>Patient</span>
            <select value={patientUuid} onChange={(e) => setPatientUuid(e.target.value)} required>
              <option value="">Select…</option>
              {patients.map((p) => (
                <option key={p.patient_uuid} value={p.patient_uuid}>{p.name}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Provider</span>
            <select value={providerId} onChange={(e) => setProviderId(e.target.value)} required>
              <option value="">Select…</option>
              {providers.map((p) => (
                <option key={p.provider_id} value={p.provider_id}>{p.name}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Procedure</span>
            <select value={procedureId} onChange={(e) => setProcedureId(e.target.value)} required>
              <option value="">Select…</option>
              {procedures.map((p) => (
                <option key={p.procedure_id} value={p.procedure_id}>
                  {p.name} — {p.duration_minutes} min
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Date &amp; time</span>
            <input type="datetime-local" value={datetime} onChange={(e) => setDatetime(e.target.value)} required />
          </label>
          <button className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Schedule'}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>All appointments</h2>
          <span className="count-pill">{appts.length}</span>
        </div>
        {loading ? (
          <div className="empty">Loading…</div>
        ) : appts.length === 0 ? (
          <div className="empty">No appointments yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Provider</th>
                <th>Procedure</th>
                <th>When</th>
                <th>Location</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {appts.map((a) => (
                <tr key={a.appointment_id}>
                  <td>{a.patient_name || '—'}</td>
                  <td>{a.provider_name || '—'}</td>
                  <td>
                    {a.procedure_name || '—'}
                    {a.duration_minutes ? (
                      <span className="muted"> · {a.duration_minutes} min</span>
                    ) : null}
                  </td>
                  <td className="muted">{fmt(a.datetime)}</td>
                  <td>{a.location}</td>
                  <td>
                    <select
                      className={`status-select status-${a.status}`}
                      value={a.status}
                      onChange={(e) => changeStatus(a.appointment_id, e.target.value as ApptStatus)}
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
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

function fmt(iso?: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString();
}
