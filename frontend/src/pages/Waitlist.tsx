import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../api';
import './Waitlist.css';

type Patient = {
  patient_uuid: string;
  name: string;
  phone?: string;
};

type WaitlistEntry = {
  entry_id: string;
  patient_uuid: string;
  patient_name?: string | null;
  note: string;
  created_at?: string;
};

type Appointment = {
  appointment_id: string;
  patient_uuid: string;
  datetime: string;
  location: string;
  status: string;
};

type BackfillResult = {
  filled: boolean;
  appointment?: Appointment;
  patient?: Patient;
  message: string;
};

export default function Waitlist() {
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [patientUuid, setPatientUuid] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  const [backfilling, setBackfilling] = useState(false);
  const [result, setResult] = useState<BackfillResult | null>(null);

  const load = () => {
    setLoading(true);
    api
      .get<WaitlistEntry[]>('/api/waitlist')
      .then(setEntries)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    api
      .get<Patient[]>('/api/patients')
      .then(setPatients)
      .catch((e) => setError((e as Error).message));
  }, []);

  const addEntry = async (e: FormEvent) => {
    e.preventDefault();
    if (!patientUuid) return;
    setSaving(true);
    setError('');
    try {
      await api.post<WaitlistEntry>('/api/waitlist', {
        patient_uuid: patientUuid,
        note,
      });
      setPatientUuid('');
      setNote('');
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const removeEntry = async (id: string) => {
    setError('');
    try {
      await api.del(`/api/waitlist/${id}`);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const runBackfill = async () => {
    setBackfilling(true);
    setError('');
    try {
      const res = await api.post<BackfillResult>('/api/waitlist/backfill', {});
      setResult(res);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBackfilling(false);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Waitlist</h1>
          <p className="page-sub">
            Patients waiting for an earlier slot. Backfill fills the next opening
            from a cancellation.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel waitlist-backfill">
        <div className="panel-head">
          <h2>Fill a cancellation</h2>
        </div>
        <p className="panel-note">
          Books the longest-waiting patient into the next open availability slot
          and notifies them by SMS.
        </p>
        <button
          className="btn btn-primary waitlist-backfill-btn"
          onClick={runBackfill}
          disabled={backfilling || entries.length === 0}
        >
          {backfilling ? 'Backfilling…' : 'Backfill next opening'}
        </button>

        {result && (
          <div
            className={`result-card waitlist-result ${
              result.filled ? 'waitlist-result-ok' : 'waitlist-result-none'
            }`}
          >
            <p className="waitlist-result-msg">{result.message}</p>
            {result.filled && result.appointment && (
              <div className="kv-grid">
                <div>
                  <span>Patient</span>
                  <b>{result.patient?.name}</b>
                </div>
                <div>
                  <span>When</span>
                  <b>{fmtDateTime(result.appointment.datetime)}</b>
                </div>
                <div>
                  <span>Location</span>
                  <b>{result.appointment.location}</b>
                </div>
                <div>
                  <span>Status</span>
                  <b>{result.appointment.status}</b>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Add to waitlist</h2>
        </div>
        <form className="inline-form" onSubmit={addEntry}>
          <label className="field">
            <span>Patient</span>
            <select
              value={patientUuid}
              onChange={(e) => setPatientUuid(e.target.value)}
              required
            >
              <option value="">Select patient…</option>
              {patients.map((p) => (
                <option key={p.patient_uuid} value={p.patient_uuid}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Note</span>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Prefers mornings"
            />
          </label>
          <button className="btn btn-primary" disabled={saving || !patientUuid}>
            {saving ? 'Adding…' : 'Add to waitlist'}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Waiting</h2>
          <span className="count-pill">{entries.length}</span>
        </div>
        {loading ? (
          <div className="empty">Loading…</div>
        ) : entries.length === 0 ? (
          <div className="empty">No one on the waitlist.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Note</th>
                <th>Added</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={e.entry_id}>
                  <td>
                    {i === 0 && <span className="badge badge-inbound">Next</span>}{' '}
                    {e.patient_name || '—'}
                  </td>
                  <td className="muted">{e.note || '—'}</td>
                  <td className="muted">{fmtDate(e.created_at)}</td>
                  <td>
                    <button
                      className="btn btn-ghost"
                      onClick={() => removeEntry(e.entry_id)}
                    >
                      Remove
                    </button>
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

function fmtDate(ts?: string) {
  if (!ts) return '—';
  const n = Number(ts);
  const d = isNaN(n) ? new Date(ts) : new Date(n * 1000);
  return isNaN(d.getTime()) ? ts : d.toLocaleDateString();
}

function fmtDateTime(dt?: string) {
  if (!dt) return '—';
  const d = new Date(dt);
  return isNaN(d.getTime())
    ? dt
    : d.toLocaleString([], {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
}
