import { useEffect, useState } from 'react';
import { api } from '../api';
import './CallPop.css';

type Patient = {
  patient_uuid: string;
  name: string;
  phone?: string;
};

type Appointment = {
  appointment_id: string;
  datetime: string;
  location?: string;
  status: string;
  provider_name?: string;
  procedure_name?: string;
};

type Call = {
  call_uuid: string;
  direction: string;
  status: string;
  started_at?: string;
};

type Communication = {
  comm_id: string;
  channel: string;
  direction: string;
  body: string;
  created_at?: string;
};

type Context = {
  patient: Patient;
  appointments: Appointment[];
  calls: Call[];
  communications: Communication[];
};

export default function CallPop({ patientUuid }: { patientUuid: string }) {
  const [ctx, setCtx] = useState<Context | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    setCtx(null);
    api
      .get<Context>(`/api/patients/${patientUuid}/context`)
      .then(setCtx)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [patientUuid]);

  if (loading) return <div className="empty">Loading patient…</div>;
  if (error) return <div className="alert alert-error">{error}</div>;
  if (!ctx) return null;

  const now = Date.now();
  const upcoming = ctx.appointments
    .filter((a) => {
      const t = new Date(a.datetime).getTime();
      return isNaN(t) ? true : t >= now;
    })
    .slice(0, 4);
  const recentCalls = ctx.calls.slice(0, 4);
  const recentMessages = ctx.communications.slice(0, 4);

  return (
    <div className="callpop">
      <div className="callpop-head">
        <div>
          <h3 className="callpop-name">{ctx.patient.name}</h3>
          <span className="callpop-phone mono">{ctx.patient.phone || '—'}</span>
        </div>
      </div>

      <section className="callpop-section">
        <h4>Upcoming appointments</h4>
        {upcoming.length === 0 ? (
          <p className="muted small">None scheduled.</p>
        ) : (
          <ul className="callpop-list">
            {upcoming.map((a) => (
              <li key={a.appointment_id}>
                <b>{fmtDateTime(a.datetime)}</b>
                <span className="muted small">
                  {[a.procedure_name, a.provider_name, a.location]
                    .filter(Boolean)
                    .join(' · ') || a.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="callpop-section">
        <h4>Recent calls</h4>
        {recentCalls.length === 0 ? (
          <p className="muted small">No calls on record.</p>
        ) : (
          <ul className="callpop-list">
            {recentCalls.map((c) => (
              <li key={c.call_uuid}>
                <b>
                  <span className={`badge badge-${c.direction}`}>
                    {c.direction}
                  </span>{' '}
                  {c.status}
                </b>
                <span className="muted small">{fmtDate(c.started_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="callpop-section">
        <h4>Recent messages</h4>
        {recentMessages.length === 0 ? (
          <p className="muted small">No messages on record.</p>
        ) : (
          <ul className="callpop-list">
            {recentMessages.map((m) => (
              <li key={m.comm_id}>
                <b>
                  <span className={`badge badge-${m.direction}`}>
                    {m.channel}
                  </span>{' '}
                  {fmtDate(m.created_at)}
                </b>
                <span className="muted small callpop-body">{m.body}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function fmtDate(ts?: string) {
  if (!ts) return '—';
  const n = Number(ts);
  const d = isNaN(n) ? new Date(ts) : new Date(n * 1000);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
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
