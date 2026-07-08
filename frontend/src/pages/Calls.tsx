import { useEffect, useState } from 'react';
import { api, type Call } from '../api';

export default function Calls() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get<Call[]>('/api/calls')
      .then((c) =>
        setCalls([...c].sort((a, b) => (b.started_at || '').localeCompare(a.started_at || '')))
      )
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Calls</h1>
          <p className="page-sub">Inbound and outbound calls handled by the agent.</p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Call log</h2>
          <span className="count-pill">{calls.length}</span>
        </div>
        {loading ? (
          <div className="empty">Loading…</div>
        ) : calls.length === 0 ? (
          <div className="empty">No calls yet. Head to the Simulator to generate some.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Direction</th>
                <th>Status</th>
                <th>Started</th>
                <th>Ended</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.call_uuid}>
                  <td>{c.patient_name || '—'}</td>
                  <td><span className={`badge badge-${c.direction}`}>{c.direction}</span></td>
                  <td>{c.status}</td>
                  <td className="muted">{fmt(c.started_at)}</td>
                  <td className="muted">{fmt(c.ended_at)}</td>
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
