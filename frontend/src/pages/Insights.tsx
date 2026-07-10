import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { getTranscriptsOverview } from '../api';
import './Insights.css';

type Overview = {
  total_calls: number;
  inbound: number;
  outbound: number;
  total_appointments: number;
  booking_conversion: number;
  by_status: { scheduled: number; confirmed: number; cancelled: number };
  sentiment_distribution: { positive: number; neutral: number; negative: number };
};

type RiskRow = {
  appointment_id: string;
  patient_name: string | null;
  datetime: string;
  status: string;
  risk: number;
  band: 'low' | 'medium' | 'high';
};

function fmtWhen(dt: string): string {
  if (!dt) return '—';
  const d = new Date(dt);
  if (isNaN(d.getTime())) return dt;
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

type Bar = { label: string; value: number; cls: string };

function DistBars({ title, bars }: { title: string; bars: Bar[] }) {
  const total = bars.reduce((s, b) => s + b.value, 0) || 1;
  return (
    <div className="dist-block">
      <h3 className="dist-title">{title}</h3>
      <div className="dist-bars">
        {bars.map((b) => {
          const pct = Math.round((b.value / total) * 100);
          return (
            <div className="dist-row" key={b.label}>
              <span className="dist-label">{b.label}</span>
              <div className="dist-track">
                <div className={`dist-fill ${b.cls}`} style={{ width: `${pct}%` }} />
              </div>
              <span className="dist-value">
                {b.value} <span className="muted small">({pct}%)</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Insights() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [risk, setRisk] = useState<RiskRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [complianceFlagged, setComplianceFlagged] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get<Overview>('/api/analytics/overview'),
      api.get<RiskRow[]>('/api/analytics/no-show-risk'),
    ])
      .then(([o, r]) => {
        setOv(o);
        setRisk(r);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));

    getTranscriptsOverview()
      .then((t) => setComplianceFlagged(t.compliance_flagged_count))
      .catch(() => {});
  };

  useEffect(load, []);

  const activeAppts = ov ? ov.by_status.scheduled + ov.by_status.confirmed : 0;
  const conversionPct = ov ? Math.round(ov.booking_conversion * 100) : 0;

  return (
    <div className="page">
      <header className="page-head">
        <h1>Insights</h1>
        <p className="page-sub">
          Call intelligence, booking conversion, and no-show risk across the clinic.
        </p>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && !ov ? (
        <div className="empty">Loading analytics…</div>
      ) : (
        ov && (
          <>
            <div className="stat-row">
              <div className="stat-card">
                <span className="stat-label">Total calls</span>
                <span className="stat-value">{ov.total_calls}</span>
                <span className="stat-foot muted small">
                  {ov.inbound} in · {ov.outbound} out
                </span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Booking conversion</span>
                <span className="stat-value">{conversionPct}%</span>
                <span className="stat-foot muted small">via inbound calls</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Active appointments</span>
                <span className="stat-value">{activeAppts}</span>
                <span className="stat-foot muted small">
                  {ov.total_appointments} total
                </span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Confirmed</span>
                <span className="stat-value">{ov.by_status.confirmed}</span>
                <span className="stat-foot muted small">
                  {ov.by_status.scheduled} awaiting confirm
                </span>
              </div>
              {complianceFlagged !== null && (
                <Link to="/transcripts" className="stat-card stat-card-link">
                  <span className="stat-label">Compliance review</span>
                  <span className="stat-value">{complianceFlagged}</span>
                  <span className="stat-foot muted small">flagged calls · see Transcripts →</span>
                </Link>
              )}
            </div>

            <section className="panel">
              <div className="panel-head">
                <h2>Distribution</h2>
                <span className="panel-note">calls &amp; appointments</span>
              </div>
              <div className="dist-grid">
                <DistBars
                  title="Appointment status"
                  bars={[
                    { label: 'Scheduled', value: ov.by_status.scheduled, cls: 'bar-sky' },
                    { label: 'Confirmed', value: ov.by_status.confirmed, cls: 'bar-jade' },
                    { label: 'Cancelled', value: ov.by_status.cancelled, cls: 'bar-rose' },
                  ]}
                />
                <DistBars
                  title="Call sentiment"
                  bars={[
                    { label: 'Positive', value: ov.sentiment_distribution.positive, cls: 'bar-jade' },
                    { label: 'Neutral', value: ov.sentiment_distribution.neutral, cls: 'bar-amber' },
                    { label: 'Negative', value: ov.sentiment_distribution.negative, cls: 'bar-rose' },
                  ]}
                />
              </div>
            </section>

            <section className="panel">
              <div className="panel-head">
                <h2>No-show risk</h2>
                <span className="count-pill">{risk.length}</span>
              </div>
              {risk.length === 0 ? (
                <div className="empty">No active appointments to score.</div>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Patient</th>
                      <th>When</th>
                      <th>Status</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {risk.map((r) => (
                      <tr key={r.appointment_id}>
                        <td>{r.patient_name || <span className="muted">Unknown</span>}</td>
                        <td>{fmtWhen(r.datetime)}</td>
                        <td>
                          <span className={`badge status-${r.status}`}>{r.status}</span>
                        </td>
                        <td>
                          <span className={`risk-pill risk-${r.band}`}>
                            {r.band} · {Math.round(r.risk * 100)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </>
        )
      )}
    </div>
  );
}
