import { useEffect, useState, type FormEvent } from 'react';
import { api, type Appointment, type Patient } from '../api';

const STATUSES: Appointment['status'][] = ['scheduled', 'confirmed', 'cancelled'];

export default function Appointments() {
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [patientUuid, setPatientUuid] = useState('');
  const [datetime, setDatetime] = useState('');
  const [location, setLocation] = useState('Main Clinic');
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get<Appointment[]>('/api/appointments'),
      api.get<Patient[]>('/api/patients'),
    ])
      .then(([a, p]) => {
        setAppts(a);
        setPatients(p);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    if (!patientUuid || !datetime) return;
    setSaving(true);
    setError('');
    try {
      await api.post<Appointment>('/api/appointments', {
        patient_uuid: patientUuid,
        datetime: new Date(datetime).toISOString(),
        location,
      });
      setDatetime('');
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (id: string, status: Appointment['status']) => {
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
            <span>Date &amp; time</span>
            <input type="datetime-local" value={datetime} onChange={(e) => setDatetime(e.target.value)} required />
          </label>
          <label className="field">
            <span>Location</span>
            <input value={location} onChange={(e) => setLocation(e.target.value)} required />
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
                <th>When</th>
                <th>Location</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {appts.map((a) => (
                <tr key={a.appointment_id}>
                  <td>{a.patient_name || '—'}</td>
                  <td className="muted">{fmt(a.datetime)}</td>
                  <td>{a.location}</td>
                  <td>
                    <select
                      className={`status-select status-${a.status}`}
                      value={a.status}
                      onChange={(e) => changeStatus(a.appointment_id, e.target.value as Appointment['status'])}
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
