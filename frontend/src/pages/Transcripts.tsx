import { useEffect, useState } from 'react';
import {
  getTranscripts,
  getTranscript,
  getTranscriptsOverview,
  type TranscriptListItem,
  type TranscriptDetail,
  type TranscriptsOverview,
} from '../api';
import './Transcripts.css';

function fmt(iso?: string | null) {
  if (!iso) return '—';
  // started_at is unix epoch seconds as a string
  const n = Number(iso);
  const d = !isNaN(n) && iso.trim() !== '' ? new Date(n * 1000) : new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function ThemeList({ title, items }: { title: string; items: { theme: string; count: number }[] }) {
  return (
    <div className="dist-block">
      <h3 className="dist-title">{title}</h3>
      {items.length === 0 ? (
        <p className="muted small">No data yet.</p>
      ) : (
        <ul className="theme-list">
          {items.map((it, i) => (
            <li key={i} className="theme-row">
              <span className="theme-text">{it.theme}</span>
              <span className="theme-count">{it.count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function QualityBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="muted small">—</span>;
  const cls = score >= 4 ? 'quality-good' : score >= 3 ? 'quality-ok' : 'quality-poor';
  return <span className={`quality-pill ${cls}`}>{score}/5</span>;
}

function PendingBadge() {
  return <span className="quality-pill quality-pending">Pending analysis</span>;
}

function exportCsv(items: TranscriptListItem[]) {
  const header = ['Patient', 'Direction', 'Started', 'Quality score', 'Booked', 'Compliance flagged'];
  const rows = items.map((it) => [
    it.patient_name || '',
    it.direction,
    it.started_at,
    it.quality_score === null ? '' : String(it.quality_score),
    it.booked ? 'Yes' : 'No',
    it.has_compliance_flags ? 'Yes' : 'No',
  ]);
  const escape = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const csv = [header, ...rows].map((r) => r.map((c) => escape(String(c))).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `transcripts-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function TranscriptDrilldown({
  callUuid,
  onClose,
}: {
  callUuid: string;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<TranscriptDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    setDetail(null);
    getTranscript(callUuid)
      .then(setDetail)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [callUuid]);

  return (
    <section className="panel transcript-detail">
      <div className="panel-head">
        <h2>Call detail</h2>
        <button className="btn btn-ghost" onClick={onClose}>
          Close
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="empty">Loading transcript…</div>
      ) : (
        detail && (
          <div className="transcript-layout">
            <div className="transcript-turns">
              {detail.transcript.length === 0 ? (
                <div className="empty">No transcript recorded.</div>
              ) : (
                detail.transcript.map((turn, i) => (
                  <div key={i} className={`turn turn-${turn.role}`}>
                    <span className="turn-role">{turn.role}</span>
                    <p className="turn-text">{turn.text}</p>
                  </div>
                ))
              )}
            </div>

            <aside className="transcript-summary">
              <div className="summary-block">
                <h4>Overview</h4>
                <div className="summary-row">
                  <span className="muted small">Patient</span>
                  <span>{detail.patient_name || '—'}</span>
                </div>
                <div className="summary-row">
                  <span className="muted small">Direction</span>
                  <span className={`badge badge-${detail.direction}`}>{detail.direction}</span>
                </div>
                <div className="summary-row">
                  <span className="muted small">Status</span>
                  <span>{detail.status}</span>
                </div>
                <div className="summary-row">
                  <span className="muted small">Started</span>
                  <span>{fmt(detail.started_at)}</span>
                </div>
                <div className="summary-row">
                  <span className="muted small">Ended</span>
                  <span>{fmt(detail.ended_at)}</span>
                </div>
                <div className="summary-row">
                  <span className="muted small">
                    {detail.analyzed ? 'Quality score' : 'Quality signal (sentiment)'}
                  </span>
                  {detail.analyzed ? (
                    <QualityBadge score={detail.judgment.quality_score} />
                  ) : (
                    <span className="quality-pill quality-pending">
                      {detail.judgment.quality_score ?? '—'}/5 (unverified)
                    </span>
                  )}
                </div>
                <div className="summary-row">
                  <span className="muted small">Booked</span>
                  <span>{detail.judgment.booked ? 'Yes' : 'No'}</span>
                </div>
              </div>

              {!detail.analyzed ? (
                <div className="summary-block pending-block">
                  <h4>Not yet analyzed</h4>
                  <p className="muted small">
                    This call hasn&apos;t been through batch AI review yet. Coaching notes, business
                    insights, and compliance flags are not available. The quality score above is a
                    lightweight sentiment-derived signal, not a full judgment.
                  </p>
                  {detail.judgment.summary && (
                    <p className="pending-summary">{detail.judgment.summary}</p>
                  )}
                </div>
              ) : (
                <>
                  <div className="summary-block">
                    <h4>Business owner insights</h4>
                    {detail.judgment.business_owner_insights.length === 0 ? (
                      <p className="muted small">None noted.</p>
                    ) : (
                      <ul className="note-list">
                        {detail.judgment.business_owner_insights.map((n, i) => (
                          <li key={i}>{n}</li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="summary-block">
                    <h4>Receptionist coaching</h4>
                    {detail.judgment.receptionist_coaching.length === 0 ? (
                      <p className="muted small">None noted.</p>
                    ) : (
                      <ul className="note-list coaching-list">
                        {detail.judgment.receptionist_coaching.map((n, i) => (
                          <li key={i}>{n}</li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="summary-block">
                    <h4>Compliance flags</h4>
                    {detail.judgment.compliance_flags.length === 0 ? (
                      <p className="muted small">No flags.</p>
                    ) : (
                      <ul className="note-list flag-list">
                        {detail.judgment.compliance_flags.map((n, i) => (
                          <li key={i}>{n}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </>
              )}
            </aside>
          </div>
        )
      )}
    </section>
  );
}

type QualityFilter = 'all' | 'poor' | 'ok' | 'good';

export default function Transcripts() {
  const [items, setItems] = useState<TranscriptListItem[]>([]);
  const [overview, setOverview] = useState<TranscriptsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [qualityFilter, setQualityFilter] = useState<QualityFilter>('all');

  useEffect(() => {
    setLoading(true);
    Promise.all([getTranscripts(), getTranscriptsOverview()])
      .then(([list, ov]) => {
        setItems([...list].sort((a, b) => (b.started_at || '').localeCompare(a.started_at || '')));
        setOverview(ov);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const avgQuality =
    overview && overview.average_quality_score !== null
      ? overview.average_quality_score.toFixed(1)
      : '—';

  const filteredItems = items.filter((it) => {
    if (search.trim() && !(it.patient_name || '').toLowerCase().includes(search.trim().toLowerCase())) {
      return false;
    }
    if (flaggedOnly && !it.has_compliance_flags) return false;
    if (qualityFilter !== 'all') {
      if (it.quality_score === null) return false;
      if (qualityFilter === 'poor' && !(it.quality_score <= 2)) return false;
      if (qualityFilter === 'ok' && it.quality_score !== 3) return false;
      if (qualityFilter === 'good' && !(it.quality_score >= 4)) return false;
    }
    return true;
  });

  const callsDelta =
    overview && overview.this_week.count !== null && overview.prior_week.count !== null
      ? overview.this_week.count - overview.prior_week.count
      : null;
  const qualityDelta =
    overview &&
    overview.this_week.average_quality_score !== null &&
    overview.prior_week.average_quality_score !== null
      ? overview.this_week.average_quality_score - overview.prior_week.average_quality_score
      : null;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Transcripts</h1>
          <p className="page-sub">
            AI-judged call transcripts: coaching notes, business insights, and compliance flags.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && !overview ? (
        <div className="empty">Loading transcripts…</div>
      ) : (
        overview && (
          <>
            <div className="stat-row">
              <div className="stat-card">
                <span className="stat-label">Calls analyzed</span>
                <span className="stat-value">{overview.total_calls_analyzed}</span>
                {callsDelta !== null && (
                  <span className={`stat-foot small trend-${callsDelta >= 0 ? 'up' : 'down'}`}>
                    {callsDelta >= 0 ? '↑' : '↓'} {Math.abs(callsDelta)}{' '}
                    {Math.abs(callsDelta) === 1 ? 'call' : 'calls'} vs last week
                  </span>
                )}
              </div>
              <div className="stat-card">
                <span className="stat-label">Average quality</span>
                <span className="stat-value">{avgQuality}</span>
                <span className="stat-foot muted small">out of 5</span>
                {qualityDelta !== null && (
                  <span className={`stat-foot small trend-${qualityDelta >= 0 ? 'up' : 'down'}`}>
                    {qualityDelta >= 0 ? '↑' : '↓'} {Math.abs(qualityDelta).toFixed(1)} vs last week
                  </span>
                )}
              </div>
              <div className="stat-card">
                <span className="stat-label">Compliance flags</span>
                <span className="stat-value">{overview.compliance_flagged_count}</span>
                <span className="stat-foot muted small">calls flagged</span>
              </div>
            </div>

            <section className="panel">
              <div className="panel-head">
                <h2>Themes</h2>
                <span className="panel-note">top recurring notes</span>
              </div>
              <div className="dist-grid">
                <ThemeList title="Business owner insights" items={overview.top_business_owner_insights} />
                <ThemeList title="Coaching themes" items={overview.top_coaching_themes} />
              </div>
            </section>
          </>
        )
      )}

      {selected ? (
        <TranscriptDrilldown callUuid={selected} onClose={() => setSelected(null)} />
      ) : (
        <section className="panel">
          <div className="panel-head">
            <h2>Call log</h2>
            <span className="count-pill">{filteredItems.length}</span>
          </div>

          <div className="filter-row">
            <input
              type="text"
              className="filter-input"
              placeholder="Search patient name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <label className="filter-check">
              <input
                type="checkbox"
                checked={flaggedOnly}
                onChange={(e) => setFlaggedOnly(e.target.checked)}
              />
              Compliance flagged only
            </label>
            <select
              className="filter-select"
              value={qualityFilter}
              onChange={(e) => setQualityFilter(e.target.value as QualityFilter)}
            >
              <option value="all">All quality scores</option>
              <option value="poor">1-2 (poor)</option>
              <option value="ok">3 (ok)</option>
              <option value="good">4-5 (good)</option>
            </select>
            <button
              type="button"
              className="btn btn-ghost export-btn"
              onClick={() => exportCsv(filteredItems)}
              disabled={filteredItems.length === 0}
            >
              Export CSV
            </button>
          </div>

          {loading ? (
            <div className="empty">Loading…</div>
          ) : filteredItems.length === 0 ? (
            <div className="empty">
              {items.length === 0 ? 'No analyzed calls yet.' : 'No calls match the current filters.'}
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Direction</th>
                  <th>Started</th>
                  <th>Quality</th>
                  <th>Booked</th>
                  <th>Compliance</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((it) => (
                  <tr
                    key={it.call_uuid}
                    className="row-clickable"
                    onClick={() => setSelected(it.call_uuid)}
                  >
                    <td>{it.patient_name || '—'}</td>
                    <td>
                      <span className={`badge badge-${it.direction}`}>{it.direction}</span>
                    </td>
                    <td className="muted">{fmt(it.started_at)}</td>
                    <td>{it.analyzed ? <QualityBadge score={it.quality_score} /> : <PendingBadge />}</td>
                    <td>{it.booked ? 'Yes' : 'No'}</td>
                    <td>
                      {it.has_compliance_flags ? (
                        <span className="flag-pill">flagged</span>
                      ) : (
                        <span className="muted small">clear</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
