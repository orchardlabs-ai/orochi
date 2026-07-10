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
                  <span className="muted small">Quality score</span>
                  <QualityBadge score={detail.judgment.quality_score} />
                </div>
                <div className="summary-row">
                  <span className="muted small">Booked</span>
                  <span>{detail.judgment.booked ? 'Yes' : 'No'}</span>
                </div>
              </div>

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
            </aside>
          </div>
        )
      )}
    </section>
  );
}

export default function Transcripts() {
  const [items, setItems] = useState<TranscriptListItem[]>([]);
  const [overview, setOverview] = useState<TranscriptsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

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
              </div>
              <div className="stat-card">
                <span className="stat-label">Average quality</span>
                <span className="stat-value">{avgQuality}</span>
                <span className="stat-foot muted small">out of 5</span>
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
            <span className="count-pill">{items.length}</span>
          </div>
          {loading ? (
            <div className="empty">Loading…</div>
          ) : items.length === 0 ? (
            <div className="empty">No analyzed calls yet.</div>
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
                {items.map((it) => (
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
                    <td>
                      <QualityBadge score={it.quality_score} />
                    </td>
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
