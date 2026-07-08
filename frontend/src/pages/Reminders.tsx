import { useEffect, useState } from 'react';
import { api } from '../api';
import './Reminders.css';

interface CadenceOption {
  key: string;
  label: string;
  days: number;
  enabled: boolean;
}

interface ReminderConfig {
  cadence: string[];
  options: CadenceOption[];
}

interface DueJob {
  appointment_id: string;
  patient_uuid: string;
  patient_name: string | null;
  appointment_datetime: string | null;
  channel: string;
  cadence: string;
  cadence_label: string;
  send_on: string | null;
  status: string;
  sid?: string;
}

interface Run {
  run_id: string;
  sent: number;
  jobs: DueJob[];
  created_at: string;
}

export default function Reminders() {
  const [config, setConfig] = useState<ReminderConfig | null>(null);
  const [due, setDue] = useState<DueJob[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [lastSent, setLastSent] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get<ReminderConfig>('/api/reminders/config'),
      api.get<DueJob[]>('/api/reminders/due'),
      api.get<Run[]>('/api/reminders/history'),
    ])
      .then(([c, d, h]) => {
        setConfig(c);
        setDue(d);
        setRuns(h);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggle = async (key: string) => {
    if (!config || saving) return;
    const current = new Set(config.cadence);
    if (current.has(key)) current.delete(key);
    else current.add(key);
    setSaving(true);
    setError('');
    try {
      const updated = await api.post<ReminderConfig>('/api/reminders/config', {
        cadence: Array.from(current),
      });
      setConfig(updated);
      const d = await api.get<DueJob[]>('/api/reminders/due');
      setDue(d);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const sendAll = async () => {
    setSending(true);
    setError('');
    try {
      const res = await api.post<{ sent: number; jobs: DueJob[] }>(
        '/api/reminders/run',
        {}
      );
      setLastSent(res.sent);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Reminders</h1>
          <p className="page-sub">
            Configure the reminder cadence and dispatch outbound SMS reminders for
            upcoming appointments (offline mock).
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Cadence</h2>
          <span className="panel-note">When reminders fire before an appointment</span>
        </div>
        {config ? (
          <div className="rem-cadence">
            {config.options.map((opt) => (
              <label
                key={opt.key}
                className={`rem-toggle ${opt.enabled ? 'rem-toggle-on' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={opt.enabled}
                  disabled={saving}
                  onChange={() => toggle(opt.key)}
                />
                <span className="rem-toggle-label">{opt.label}</span>
                <span className="muted small">{opt.key}</span>
              </label>
            ))}
          </div>
        ) : (
          <div className="empty">Loading…</div>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Due reminders</h2>
          <span className="count-pill">{due.length}</span>
          <button
            className="btn btn-primary rem-send-btn"
            disabled={sending || due.length === 0}
            onClick={sendAll}
            type="button"
          >
            {sending ? 'Sending…' : `Send all due (${due.length})`}
          </button>
        </div>
        {lastSent !== null && (
          <p className="panel-note">Last run sent {lastSent} reminder{lastSent === 1 ? '' : 's'}.</p>
        )}
        {loading ? (
          <div className="empty">Loading…</div>
        ) : due.length === 0 ? (
          <div className="empty">No reminders due — enable a cadence or add appointments.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Appointment</th>
                <th>Cadence</th>
                <th>Send on</th>
                <th>Channel</th>
              </tr>
            </thead>
            <tbody>
              {due.map((j, i) => (
                <tr key={`${j.appointment_id}-${j.cadence}-${i}`}>
                  <td>{j.patient_name || '—'}</td>
                  <td>{fmt(j.appointment_datetime)}</td>
                  <td><span className="badge">{j.cadence_label}</span></td>
                  <td className="muted">{j.send_on || '—'}</td>
                  <td><span className="badge">{j.channel}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Run history</h2>
          <span className="count-pill">{runs.length}</span>
        </div>
        {runs.length === 0 ? (
          <div className="empty">No reminder runs yet.</div>
        ) : (
          <ul className="rem-runs">
            {runs.map((run) => (
              <li key={run.run_id} className="rem-run">
                <div className="rem-run-main">
                  <b>{run.sent}</b> reminder{run.sent === 1 ? '' : 's'} sent
                </div>
                <span className="muted small">{fmtTime(run.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function fmt(iso?: string | null) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function fmtTime(epoch?: string) {
  if (!epoch) return '—';
  const n = Number(epoch);
  if (!Number.isFinite(n)) return epoch;
  return new Date(n * 1000).toLocaleString();
}
