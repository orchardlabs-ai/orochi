import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import CallPop from '../components/CallPop';
import './Escalations.css';

type Escalation = {
  id: string;
  patient_uuid: string | null;
  patient_name?: string | null;
  phone: string;
  reason: string;
  summary: string;
  call_uuid: string | null;
  status: 'open' | 'resolved';
  created_at?: string;
};

export default function Escalations() {
  const [items, setItems] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showResolved, setShowResolved] = useState(false);
  const [selected, setSelected] = useState<Escalation | null>(null);
  const [resolving, setResolving] = useState('');

  const load = () => {
    setLoading(true);
    api
      .get<Escalation[]>('/api/escalations')
      .then(setItems)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const resolve = async (id: string) => {
    setResolving(id);
    setError('');
    try {
      await api.post<Escalation>(`/api/escalations/${id}/resolve`, {});
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setResolving('');
    }
  };

  const open = items.filter((e) => e.status === 'open');
  const resolved = items.filter((e) => e.status === 'resolved');
  const rows = showResolved ? resolved : open;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Escalations</h1>
          <p className="page-sub">
            Calls the AI handed off to a human. Resolve each once handled.
          </p>
        </div>
        <span className="count-pill">{open.length} open</span>
      </header>

      <p className="page-sub esc-transcripts-link">
        Reviewing an escalated call? See AI coaching notes and compliance flags in{' '}
        <Link to="/transcripts">Transcripts →</Link>
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="esc-layout">
        <section className="panel esc-queue">
          <div className="panel-head">
            <h2>{showResolved ? 'Resolved' : 'Open queue'}</h2>
            <div className="esc-toggle">
              <button
                className={`btn btn-ghost ${!showResolved ? 'esc-active' : ''}`}
                onClick={() => setShowResolved(false)}
              >
                Open ({open.length})
              </button>
              <button
                className={`btn btn-ghost ${showResolved ? 'esc-active' : ''}`}
                onClick={() => setShowResolved(true)}
              >
                Resolved ({resolved.length})
              </button>
            </div>
          </div>

          {loading ? (
            <div className="empty">Loading…</div>
          ) : rows.length === 0 ? (
            <div className="empty">
              {showResolved ? 'Nothing resolved yet.' : 'No open escalations.'}
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Reason</th>
                  <th>Summary</th>
                  <th>When</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr
                    key={e.id}
                    onClick={() => setSelected(e)}
                    className={
                      selected?.id === e.id ? 'esc-row esc-selected' : 'esc-row'
                    }
                  >
                    <td>
                      <b>{e.patient_name || 'Unknown'}</b>
                      <div className="muted small mono">{e.phone}</div>
                    </td>
                    <td>
                      <span className={reasonClass(e.reason)}>{e.reason}</span>
                    </td>
                    <td className="muted esc-summary">{e.summary || '—'}</td>
                    <td className="muted small">{fmtDate(e.created_at)}</td>
                    <td>
                      {e.status === 'open' ? (
                        <button
                          className="btn btn-primary"
                          disabled={resolving === e.id}
                          onClick={(ev) => {
                            ev.stopPropagation();
                            resolve(e.id);
                          }}
                        >
                          {resolving === e.id ? 'Resolving…' : 'Resolve'}
                        </button>
                      ) : (
                        <span className="badge badge-inbound">resolved</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <aside className="esc-pop">
          {selected && selected.patient_uuid ? (
            <CallPop patientUuid={selected.patient_uuid} />
          ) : (
            <div className="panel empty">
              Select an escalation to see the patient timeline.
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function reasonClass(reason: string) {
  if (reason === 'emergency') return 'badge esc-reason-emergency';
  return 'badge';
}

function fmtDate(ts?: string) {
  if (!ts) return '—';
  const n = Number(ts);
  const d = isNaN(n) ? new Date(ts) : new Date(n * 1000);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
}
