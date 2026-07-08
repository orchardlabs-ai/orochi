import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api';
import { showIncomingCall, showToast } from '../components/Toast';
import './Demo.css';

// ---- Inline types (mirror backend run_inbound / analytics shapes) ----
interface InboundResult {
  appointment?: {
    appointment_id?: string;
    patient_name?: string;
    datetime?: string;
    procedure_name?: string;
    status?: string;
  } | null;
  intent?: string;
  escalated?: boolean;
  emergency?: boolean;
  summary?: string;
  actions?: string[];
}

interface AnalyticsOverview {
  [key: string]: unknown;
}

type StepStatus = 'pending' | 'running' | 'done' | 'skipped' | 'error';

interface LogEntry {
  id: number;
  title: string;
  detail: string;
  status: StepStatus;
  link?: { to: string; label: string };
  stats?: { label: string; value: string }[];
}

const STEP_TITLES = [
  'Inbound call — book a Checkup',
  'Inbound call — dental EMERGENCY',
  'Recare reminder campaign',
  'Waitlist backfill',
  'Analytics overview',
];

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

function humanizeStats(data: AnalyticsOverview): { label: string; value: string }[] {
  const out: { label: string; value: string }[] = [];
  for (const [k, v] of Object.entries(data)) {
    if (v === null || typeof v === 'object') continue;
    const label = k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    out.push({ label, value: String(v) });
    if (out.length >= 8) break;
  }
  return out;
}

export default function Demo() {
  const [log, setLog] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [current, setCurrent] = useState(-1);
  const idRef = useRef(0);
  const cancelRef = useRef(false);

  const push = (entry: Omit<LogEntry, 'id'>): number => {
    const id = ++idRef.current;
    setLog((prev) => [...prev, { ...entry, id }]);
    return id;
  };

  const update = (id: number, patch: Partial<LogEntry>) => {
    setLog((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  };

  const reset = () => {
    cancelRef.current = true;
    setLog([]);
    setCurrent(-1);
    setRunning(false);
  };

  async function runDemo() {
    if (running) return;
    cancelRef.current = false;
    setLog([]);
    setRunning(true);
    setCurrent(0);

    try {
      // ---- Step 1: Checkup booking ----
      {
        setCurrent(0);
        showIncomingCall('Incoming call…', 'New patient — routine checkup');
        const id = push({ title: STEP_TITLES[0], detail: 'Calling…', status: 'running' });
        await wait(900);
        if (cancelRef.current) return;
        try {
          const res = await api.post<InboundResult>('/api/simulate/inbound', {
            phone: '+15551230001',
            name: 'Maya Chen',
            message: 'Hi, I would like to book a check-up appointment next Tuesday afternoon.',
          });
          const appt = res.appointment;
          update(id, {
            status: 'done',
            detail: appt?.appointment_id
              ? `Booked ${appt.procedure_name ?? 'Checkup'} for ${appt.patient_name ?? 'patient'} at ${appt.datetime ?? '—'}.`
              : res.summary ?? 'Call handled.',
            link: appt?.appointment_id
              ? { to: '/appointments', label: 'View in Appointments' }
              : undefined,
          });
        } catch (err) {
          handleStepError(id, err);
        }
        await wait(1200);
      }
      if (cancelRef.current) return;

      // ---- Step 2: Emergency escalation ----
      {
        setCurrent(1);
        showIncomingCall('Incoming call…', 'Possible dental emergency');
        const id = push({ title: STEP_TITLES[1], detail: 'Calling…', status: 'running' });
        await wait(900);
        if (cancelRef.current) return;
        try {
          const res = await api.post<InboundResult>('/api/simulate/inbound', {
            phone: '+15551230002',
            name: 'Tom Reyes',
            message:
              'My tooth got knocked out and my mouth is bleeding a lot, I am in severe pain and need help right now!',
          });
          const escalated = res.escalated || res.emergency;
          if (escalated) {
            showToast({ title: 'Escalated to on-call', subtitle: 'Emergency routed to a human', variant: 'default' });
          }
          update(id, {
            status: 'done',
            detail: escalated
              ? 'Emergency detected — call escalated to the on-call team.'
              : res.summary ?? 'Call handled (no escalation flagged).',
            link: escalated ? { to: '/escalations', label: 'View in Escalations' } : undefined,
          });
        } catch (err) {
          handleStepError(id, err);
        }
        await wait(1200);
      }
      if (cancelRef.current) return;

      // ---- Step 3: Reminders / recare campaign ----
      {
        setCurrent(2);
        const id = push({ title: STEP_TITLES[2], detail: 'Running…', status: 'running' });
        await wait(600);
        if (cancelRef.current) return;
        const ran = await tryFirst(
          [
            { method: 'post' as const, path: '/api/simulate/reminders', body: undefined },
            { method: 'post' as const, path: '/api/reminders/run', body: undefined },
            { method: 'post' as const, path: '/api/campaigns/run', body: { segment: 'recare' } },
          ],
        );
        if (ran.ok) {
          update(id, {
            status: 'done',
            detail: summarizeCount(ran.data, 'reminder(s) sent'),
            link: { to: '/campaigns', label: 'View in Campaigns' },
          });
        } else {
          update(id, { status: 'skipped', detail: 'No reminder endpoint available — skipped.' });
        }
        await wait(1200);
      }
      if (cancelRef.current) return;

      // ---- Step 4: Waitlist backfill ----
      {
        setCurrent(3);
        const id = push({ title: STEP_TITLES[3], detail: 'Running…', status: 'running' });
        await wait(600);
        if (cancelRef.current) return;
        try {
          const res = await api.post<unknown>('/api/waitlist/backfill', {});
          update(id, {
            status: 'done',
            detail: summarizeCount(res, 'slot(s) backfilled from the waitlist'),
            link: { to: '/waitlist', label: 'View in Waitlist' },
          });
        } catch (err) {
          handleStepError(id, err);
        }
        await wait(1200);
      }
      if (cancelRef.current) return;

      // ---- Step 5: Analytics overview ----
      {
        setCurrent(4);
        const id = push({ title: STEP_TITLES[4], detail: 'Loading stats…', status: 'running' });
        await wait(600);
        if (cancelRef.current) return;
        try {
          const res = await api.get<AnalyticsOverview>('/api/analytics/overview');
          update(id, {
            status: 'done',
            detail: 'Clinic snapshot after the demo run:',
            stats: humanizeStats(res),
            link: { to: '/insights', label: 'Open Insights' },
          });
        } catch (err) {
          handleStepError(id, err);
        }
      }

      if (!cancelRef.current) {
        showToast({ title: 'Guided demo complete', subtitle: 'All steps finished', variant: 'default' });
      }
    } finally {
      setCurrent(-1);
      setRunning(false);
    }
  }

  function handleStepError(id: number, err: unknown) {
    if (err instanceof ApiError && err.status === 404) {
      update(id, { status: 'skipped', detail: 'Endpoint not available (404) — skipped.' });
    } else {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      update(id, { status: 'error', detail: `Failed: ${msg}` });
    }
  }

  async function tryFirst(
    attempts: { method: 'post'; path: string; body: unknown }[],
  ): Promise<{ ok: boolean; data?: unknown }> {
    for (const a of attempts) {
      try {
        const data = await api.post<unknown>(a.path, a.body);
        return { ok: true, data };
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) continue;
        // non-404 error: treat as skip but stop trying
        return { ok: false };
      }
    }
    return { ok: false };
  }

  return (
    <div className="page demo-page">
      <div className="page-head">
        <div>
          <h1>Guided demo</h1>
          <p className="page-sub">
            Runs the full Orochi narrative automatically — two live calls, recare reminders, a
            waitlist backfill, and the resulting analytics. Watch for the incoming-call toasts.
          </p>
        </div>
        <div className="demo-actions">
          <button className="btn btn-primary" onClick={runDemo} disabled={running}>
            {running ? 'Running…' : 'Run guided demo'}
          </button>
          <button className="btn btn-ghost" onClick={reset} disabled={!log.length && !running}>
            Reset
          </button>
        </div>
      </div>

      <div className="demo-progress" aria-hidden={!running && current < 0}>
        {STEP_TITLES.map((t, i) => (
          <div
            key={i}
            className={
              'demo-progress-step' +
              (i < current || (i === current && !running) ? ' is-done' : '') +
              (i === current && running ? ' is-active' : '')
            }
            title={t}
          >
            <span className="demo-progress-dot">{i + 1}</span>
          </div>
        ))}
      </div>

      <div className="panel demo-log-panel">
        <div className="panel-head">
          <h2>Timeline</h2>
          {log.length > 0 && <span className="count-pill">{log.length}</span>}
        </div>
        {log.length === 0 ? (
          <div className="empty">
            Press <strong>Run guided demo</strong> to play the product story end to end.
          </div>
        ) : (
          <ol className="demo-log">
            {log.map((e) => (
              <li key={e.id} className={`demo-log-item status-${e.status}`}>
                <span className="demo-log-marker" aria-hidden="true">
                  {e.status === 'running'
                    ? '◐'
                    : e.status === 'done'
                    ? '✓'
                    : e.status === 'skipped'
                    ? '–'
                    : e.status === 'error'
                    ? '!'
                    : '○'}
                </span>
                <div className="demo-log-content">
                  <div className="demo-log-title">
                    {e.title}
                    <span className={`badge demo-badge-${e.status}`}>{e.status}</span>
                  </div>
                  <div className="demo-log-detail">{e.detail}</div>
                  {e.stats && e.stats.length > 0 && (
                    <div className="stat-grid demo-stats">
                      {e.stats.map((s) => (
                        <div className="stat-card" key={s.label}>
                          <div className="stat-value">{s.value}</div>
                          <div className="stat-label">{s.label}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {e.link && (
                    <Link className="demo-log-link" to={e.link.to}>
                      {e.link.label} →
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

function summarizeCount(data: unknown, noun: string): string {
  if (Array.isArray(data)) return `${data.length} ${noun}.`;
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>;
    for (const key of ['count', 'sent', 'filled', 'backfilled', 'total', 'reminders']) {
      if (typeof obj[key] === 'number') return `${obj[key]} ${noun}.`;
    }
    for (const v of Object.values(obj)) {
      if (Array.isArray(v)) return `${v.length} ${noun}.`;
    }
  }
  return `Done — ${noun}.`;
}
