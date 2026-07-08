import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import './Campaigns.css';

type Category = 'appointments' | 'engagement' | 'payment' | 'reputation' | 'other';

interface Segment {
  key: string;
  label: string;
  category: Category;
  description: string;
  patient_count: number;
  sample: string[];
}

interface CampaignRunResult {
  segment: string;
  category: Category;
  label: string;
  contacted: number;
  communications: unknown[];
}

interface CampaignRunRecord {
  run_id: string;
  segment: string;
  label: string;
  category: Category;
  count: number;
  created_at: string;
}

const CATEGORY_ORDER: Category[] = [
  'appointments',
  'engagement',
  'payment',
  'reputation',
  'other',
];

const CATEGORY_LABELS: Record<Category, string> = {
  appointments: 'Appointments',
  engagement: 'Engagement',
  payment: 'Payment',
  reputation: 'Reputation',
  other: 'Other',
};

const CATEGORY_BLURB: Record<Category, string> = {
  appointments: 'Booking nudges and recall',
  engagement: 'Friendly check-ins and reactivation',
  payment: 'Benefits and billing reminders',
  reputation: 'Reviews and referrals',
  other: 'Everything else',
};

function catClass(category: Category): string {
  return `cat cat-${category}`;
}

export default function Campaigns() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [history, setHistory] = useState<CampaignRunRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, number>>({});
  const [filter, setFilter] = useState<Category | 'all'>('all');

  const refresh = () =>
    Promise.all([
      api.get<Segment[]>('/api/campaigns/segments'),
      api.get<CampaignRunRecord[]>('/api/campaigns/history'),
    ]).then(([segs, hist]) => {
      setSegments(segs);
      setHistory(hist);
    });

  const load = () => {
    setLoading(true);
    refresh()
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
        return refresh();
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setRunning(null));
  };

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: segments.length };
    for (const cat of CATEGORY_ORDER) c[cat] = 0;
    for (const s of segments) c[s.category] = (c[s.category] || 0) + 1;
    return c;
  }, [segments]);

  const grouped = useMemo(() => {
    const g: Record<Category, Segment[]> = {
      appointments: [],
      engagement: [],
      payment: [],
      reputation: [],
      other: [],
    };
    for (const s of segments) (g[s.category] || g.other).push(s);
    return g;
  }, [segments]);

  const chips: (Category | 'all')[] = ['all', ...CATEGORY_ORDER];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Campaigns</h1>
          <p className="page-sub">
            Communication across every patient intent — appointment recall, engagement
            check-ins, payment and benefits reminders, and reputation asks. Each segment is
            computed live from your existing patients, calls, and visits.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      {!loading && (
        <div className="cat-filter" role="tablist" aria-label="Filter by category">
          {chips.map((c) => (
            <button
              key={c}
              type="button"
              className={`cat-chip${filter === c ? ' is-active' : ''}${
                c === 'all' ? '' : ` cat-chip-${c}`
              }`}
              aria-pressed={filter === c}
              onClick={() => setFilter(c)}
            >
              {c === 'all' ? 'All' : CATEGORY_LABELS[c]}
              <span className="cat-chip-count">{counts[c] ?? 0}</span>
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <section className="panel">
          <div className="empty">Loading…</div>
        </section>
      ) : (
        CATEGORY_ORDER.filter((cat) => filter === 'all' || filter === cat).map((cat) => {
          const items = grouped[cat];
          if (items.length === 0) return null;
          return (
            <section className="panel" key={cat}>
              <div className="panel-head">
                <div className="cat-section-head">
                  <span className={catClass(cat)}>{CATEGORY_LABELS[cat]}</span>
                  <span className="panel-note">{CATEGORY_BLURB[cat]}</span>
                </div>
                <span className="count-pill">{items.length}</span>
              </div>
              <div className="campaign-grid">
                {items.map((s) => (
                  <div className="campaign-card" key={s.key}>
                    <div className="campaign-card-top">
                      <span className={catClass(s.category)}>
                        {CATEGORY_LABELS[s.category]}
                      </span>
                      <span className="count-pill">{s.patient_count}</span>
                    </div>
                    <h3 className="campaign-title">{s.label}</h3>
                    <p className="campaign-desc">{s.description}</p>
                    {s.sample.length > 0 && (
                      <p className="campaign-sample muted small">
                        {s.sample.slice(0, 4).join(', ')}
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
            </section>
          );
        })
      )}

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
                <th>Category</th>
                <th>Contacted</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.run_id}>
                  <td>{h.label || h.segment}</td>
                  <td>
                    <span className={catClass(h.category)}>
                      {CATEGORY_LABELS[h.category] || h.category}
                    </span>
                  </td>
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
