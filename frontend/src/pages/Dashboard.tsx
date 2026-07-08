import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Patient, type Appointment, type Call } from '../api';

export default function Dashboard() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      api.get<Patient[]>('/api/patients'),
      api.get<Appointment[]>('/api/appointments'),
      api.get<Call[]>('/api/calls'),
    ])
      .then(([p, a, c]) => {
        setPatients(p);
        setAppointments(a);
        setCalls(c);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const upcoming = appointments.filter((a) => a.status !== 'cancelled').length;
  const recentCalls = [...calls]
    .sort((a, b) => (b.started_at || '').localeCompare(a.started_at || ''))
    .slice(0, 6);

  const stats = [
    { label: 'Patients', value: patients.length, to: '/patients', icon: '🧑‍⚕️' },
    { label: 'Active appointments', value: upcoming, to: '/appointments', icon: '📅' },
    { label: 'Calls handled', value: calls.length, to: '/calls', icon: '📞' },
  ];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="page-sub">Overview of clinic activity handled by the agent.</p>
        </div>
        <Link to="/simulator" className="btn btn-primary">Run simulation</Link>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="stat-grid">
        {stats.map((s) => (
          <Link to={s.to} key={s.label} className="stat-card">
            <span className="stat-icon" aria-hidden="true">{s.icon}</span>
            <div className="stat-value">{loading ? '—' : s.value}</div>
            <div className="stat-label">{s.label}</div>
          </Link>
        ))}
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2>Recent calls</h2>
          <Link to="/calls" className="link">View all</Link>
        </div>
        {loading ? (
          <div className="empty">Loading…</div>
        ) : recentCalls.length === 0 ? (
          <div className="empty">No calls yet. Try the Simulator.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Direction</th>
                <th>Status</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {recentCalls.map((c) => (
                <tr key={c.call_uuid}>
                  <td>{c.patient_name || '—'}</td>
                  <td>
                    <span className={`badge badge-${c.direction}`}>{c.direction}</span>
                  </td>
                  <td>{c.status}</td>
                  <td className="muted">{fmt(c.started_at)}</td>
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
