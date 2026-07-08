import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../api';
import './Communications.css';

type Channel = 'sms' | 'email' | 'voice';
type Direction = 'inbound' | 'outbound';

interface Patient {
  patient_uuid: string;
  name: string;
  phone?: string;
}

interface Communication {
  comm_id: string;
  patient_uuid: string;
  patient_name: string | null;
  channel: Channel;
  direction: Direction;
  body: string;
  status: string;
  meta: Record<string, unknown>;
  created_at: string;
}

interface Appointment {
  appointment_id: string;
  patient_uuid: string;
  patient_name?: string | null;
  datetime: string;
  location: string;
  status: 'scheduled' | 'confirmed' | 'cancelled';
}

const CHANNELS: Channel[] = ['sms', 'email', 'voice'];

export default function Communications() {
  const [comms, setComms] = useState<Communication[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Send form
  const [patientUuid, setPatientUuid] = useState('');
  const [channel, setChannel] = useState<Channel>('sms');
  const [body, setBody] = useState('');
  const [sending, setSending] = useState(false);

  // Two-way confirmation demo
  const [apptId, setApptId] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [lastConfirm, setLastConfirm] = useState<Appointment | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get<Communication[]>('/api/comms'),
      api.get<Patient[]>('/api/patients'),
      api.get<Appointment[]>('/api/appointments'),
    ])
      .then(([c, p, a]) => {
        setComms(c);
        setPatients(p);
        setAppts(a);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    if (!patientUuid || !body.trim()) return;
    setSending(true);
    setError('');
    try {
      await api.post<Communication>('/api/comms/send', {
        patient_uuid: patientUuid,
        channel,
        body,
      });
      setBody('');
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  };

  const react = async (action: 'confirm' | 'cancel') => {
    if (!apptId) return;
    setConfirming(true);
    setError('');
    try {
      const res = await api.post<{ appointment: Appointment; communication: Communication }>(
        '/api/comms/confirm',
        { appointment_id: apptId, action }
      );
      setLastConfirm(res.appointment);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Messages</h1>
          <p className="page-sub">
            Two-way SMS, email and voice — all delivered by the mock Twilio bridge (offline demo).
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Send message</h2>
        </div>
        <form className="inline-form" onSubmit={send}>
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
            <span>Channel</span>
            <select value={channel} onChange={(e) => setChannel(e.target.value as Channel)}>
              {CHANNELS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="field comm-body-field">
            <span>Message</span>
            <input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Type a message…" required />
          </label>
          <button className="btn btn-primary" disabled={sending}>
            {sending ? 'Sending…' : 'Send'}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Two-way confirmation</h2>
          <span className="panel-note">Simulate a patient replying to a reminder</span>
        </div>
        <div className="comm-confirm">
          <label className="field">
            <span>Appointment</span>
            <select value={apptId} onChange={(e) => setApptId(e.target.value)}>
              <option value="">Select…</option>
              {appts.map((a) => (
                <option key={a.appointment_id} value={a.appointment_id}>
                  {(a.patient_name || 'Unknown')} — {fmt(a.datetime)} ({a.status})
                </option>
              ))}
            </select>
          </label>
          <div className="comm-confirm-actions">
            <button
              className="btn btn-primary"
              disabled={!apptId || confirming}
              onClick={() => react('confirm')}
              type="button"
            >
              Reply “Confirm”
            </button>
            <button
              className="btn btn-secondary"
              disabled={!apptId || confirming}
              onClick={() => react('cancel')}
              type="button"
            >
              Reply “Cancel”
            </button>
          </div>
        </div>
        {lastConfirm && (
          <div className="result-card comm-result">
            <div className="kv-grid">
              <div><span>Patient</span><b>{lastConfirm.patient_name || '—'}</b></div>
              <div><span>When</span><b>{fmt(lastConfirm.datetime)}</b></div>
              <div>
                <span>Status</span>
                <b><span className={`badge status-${lastConfirm.status}`}>{lastConfirm.status}</span></b>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Communications log</h2>
          <span className="count-pill">{comms.length}</span>
        </div>
        {loading ? (
          <div className="empty">Loading…</div>
        ) : comms.length === 0 ? (
          <div className="empty">No communications yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Channel</th>
                <th>Direction</th>
                <th>Patient</th>
                <th>Message</th>
                <th>Status</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {comms.map((c) => (
                <tr key={c.comm_id}>
                  <td><span className={`badge comm-channel comm-channel-${c.channel}`}>{c.channel}</span></td>
                  <td><span className={`badge badge-${c.direction}`}>{c.direction}</span></td>
                  <td>{c.patient_name || '—'}</td>
                  <td className="comm-msg">{c.body}</td>
                  <td className="muted">{c.status}</td>
                  <td className="muted small">{fmtTime(c.created_at)}</td>
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

function fmtTime(epoch?: string) {
  if (!epoch) return '—';
  const n = Number(epoch);
  if (!Number.isFinite(n)) return epoch;
  return new Date(n * 1000).toLocaleString();
}
