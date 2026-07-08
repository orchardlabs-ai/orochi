import { useEffect, useState } from 'react';
import { api } from '../api';
import './Campaigns.css';

interface Segment {
  key: string;
  label: string;
  description: string;
  patient_count: number;
  sample: string[];
}

interface CampaignRunResult {
  segment: string;
  contacted: number;
  run: CampaignRunRecord;
  communications: unknown[];
}

interface CampaignRunRecord {
  run_id: string;
  segment: string;
  count: number;
  created_at: string;
}

const LABELS: Record<string, string> = {
  recare: 'Recare recall',
  reactivation: 'Reactivation',
  missed_call_recovery: 'Missed-call recovery',
};

export default function Campaigns() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [history, setHistory] = useState<CampaignRunRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, number>>({});

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get<Segment[]>('/api/campaigns/segments'),
      api.get<CampaignRunRecord[]>('/api/campaigns/history'),
    ])
      .then(([segs, hist]) => {
        setSegments(segs);
        setHistory(hist);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const run = (key: string) => {
    setRunning(key);
    setError('');
    api
      .post<CampaignRunResult>('/api/campaigns/run', { segment: key })
      .then((res) => {
        setResults((prev) => ({ ...prev, [key]: res.contacted }));
        return Promise.all([
          api.get<Segment[]>('/api/campaigns/segments'),
          api.get<CampaignRunRecord[]>('/api/campaigns/history'),
        ]);
      })
      .then(([segs, hist]) => {
        setSegments(segs);
        setHistory(hist);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setRunning(null));
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Campaigns</h1>
          <p className="page-sub">
            Outbound recall, reactivation, and missed-call recovery — segments computed
            from your existing patients and calls.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Segments</h2>
          <span className="count-pill">{segments.length}</span>
        </div>
        {loading ? (
          <div className="empty">Loading…</div>
        ) : (
          <div className="campaign-grid">
            {segments.map((s) => (
              <div className="campaign-card" key={s.key}>
                <div className="campaign-card-head">
                  <h3>{s.label}</h3>
                  <span className="count-pill">{s.patient_count}</span>
                </div>
                <p className="campaign-desc">{s.description}</p>
                {s.sample.length > 0 && (
                  <p className="campaign-sample muted small">
                    e.g. {s.sample.join(', ')}
                  </p>
                )}
                {results[s.key] !== undefined && (
                  <div className="campaign-result">
                    Contacted {results[s.key]} patient
                    {results[s.key] === 1 ? '' : 's'}.
                  </div>
                )}
                <button
                  className="btn btn-primary campaign-run"
                  disabled={running === s.key || s.patient_count === 0}
                  onClick={() => run(s.key)}
                >
                  {running === s.key
                    ? 'Running…'
                    : s.patient_count === 0
                    ? 'No patients'
                    : 'Run campaign'}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Run history</h2>
          <span className="count-pill">{history.length}</span>
        </div>
        {history.length === 0 ? (
          <div className="empty">No campaigns run yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Segment</th>
                <th>Contacted</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.run_id}>
                  <td>{LABELS[h.segment] || h.segment}</td>
                  <td>{h.count}</td>
                  <td className="muted">{fmt(h.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function fmt(ts?: string) {
  if (!ts) return '—';
  const n = Number(ts);
  const d = new Date(isNaN(n) ? ts : n * 1000);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
}
