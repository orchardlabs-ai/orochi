import { useState, type FormEvent } from 'react';
import { api } from '../api';
import './Simulator.css';

interface TranscriptTurn {
  role: string;
  text: string;
}

interface CallRecord {
  call_uuid?: string;
  direction?: string;
  status?: string;
  transcript?: TranscriptTurn[];
}

interface Appointment {
  appointment_id?: string;
  datetime?: string;
  location?: string;
  status?: string;
}

interface SimulateInboundResult {
  call?: CallRecord;
  actions?: string[];
  appointment?: Appointment | null;
  intent?: string;
  language?: string;
  sentiment?: string;
  summary?: string;
  escalated?: boolean;
  emergency?: boolean;
  faq_answer?: string | null;
}

interface ReminderResult {
  appointment_id: string;
  script: string;
  call_uuid: string;
}

type Example = {
  label: string;
  emoji: string;
  message: string;
};

const EXAMPLES: Example[] = [
  {
    label: 'Book',
    emoji: '📅',
    message: 'Hi, I would like to book a check-up appointment next Tuesday afternoon.',
  },
  {
    label: 'Reschedule',
    emoji: '🔁',
    message: 'I need to reschedule my appointment to next Friday morning instead.',
  },
  {
    label: 'Cancel',
    emoji: '❌',
    message: "I can't make it anymore — please cancel my appointment.",
  },
  {
    label: 'Hours',
    emoji: '🕗',
    message: 'What are your office hours, and are you open on weekends?',
  },
  {
    label: 'Emergency',
    emoji: '🚨',
    message: "I knocked out a tooth and it won't stop bleeding, I'm in severe pain!",
  },
];

const INTENT_LABELS: Record<string, string> = {
  book: 'Book',
  reschedule: 'Reschedule',
  cancel: 'Cancel',
  hours: 'Hours',
  insurance: 'Insurance',
  emergency: 'Emergency',
  other: 'General',
};

export default function Simulator() {
  const [phone, setPhone] = useState('+15551234567');
  const [name, setName] = useState('Jane Doe');
  const [message, setMessage] = useState(EXAMPLES[0].message);

  const [inboundBusy, setInboundBusy] = useState(false);
  const [reminderBusy, setReminderBusy] = useState(false);
  const [error, setError] = useState('');

  const [inbound, setInbound] = useState<SimulateInboundResult | null>(null);
  const [reminders, setReminders] = useState<ReminderResult[] | null>(null);

  const runInbound = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setInboundBusy(true);
    try {
      const result = await api.post<SimulateInboundResult>('/api/simulate/inbound', {
        phone,
        name,
        message,
      });
      setInbound(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setInboundBusy(false);
    }
  };

  const runReminders = async () => {
    setError('');
    setReminderBusy(true);
    try {
      const result = await api.post<{ results: ReminderResult[] }>(
        '/api/simulate/reminders'
      );
      setReminders(result.results);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setReminderBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Agent Simulator</h1>
          <p className="page-sub">
            Drive the LangGraph voice agent offline — intent routing, triage,
            multi-language, and post-call intelligence, no telephony required.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="sim-grid">
        <section className="panel">
          <div className="panel-head">
            <h2>📞 Inbound call</h2>
          </div>

          <div className="example-row">
            {EXAMPLES.map((ex) => (
              <button
                type="button"
                key={ex.label}
                className="btn btn-ghost example-btn"
                onClick={() => setMessage(ex.message)}
                title={ex.message}
              >
                <span aria-hidden>{ex.emoji}</span> {ex.label}
              </button>
            ))}
          </div>

          <form className="stacked-form" onSubmit={runInbound}>
            <label className="field">
              <span>Caller phone</span>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} required />
            </label>
            <label className="field">
              <span>Caller name</span>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <label className="field">
              <span>Message</span>
              <textarea
                rows={4}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What does the caller want?"
              />
            </label>
            <button className="btn btn-primary" disabled={inboundBusy}>
              {inboundBusy ? 'Running agent…' : 'Simulate inbound call'}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>🔔 Reminder batch</h2>
          </div>
          <p className="panel-note">
            Runs the reminder flow over all upcoming appointments and generates an
            outbound script for each.
          </p>
          <button
            className="btn btn-secondary"
            onClick={runReminders}
            disabled={reminderBusy}
          >
            {reminderBusy ? 'Running batch…' : 'Run reminder batch'}
          </button>
        </section>
      </div>

      {inbound && (
        <section className="panel">
          <div className="panel-head">
            <h2>Inbound result</h2>
            <span className={`badge badge-${inbound.call?.direction || 'inbound'}`}>
              {inbound.call?.status || 'completed'}
            </span>
          </div>

          {inbound.escalated && (
            <div className="alert alert-error emergency-banner">
              🚨 <b>Emergency escalated.</b> The caller was connected to the on-call
              provider — no appointment was booked.
            </div>
          )}

          <div className="chip-row">
            {inbound.intent && (
              <span className={`intent-badge intent-${inbound.intent}`}>
                {INTENT_LABELS[inbound.intent] || inbound.intent}
              </span>
            )}
            {inbound.language && (
              <span className="sim-chip lang-chip">
                {inbound.language === 'es' ? '🇪🇸 Español' : '🇺🇸 English'}
              </span>
            )}
            {inbound.sentiment && (
              <span className={`sim-chip sentiment-${inbound.sentiment}`}>
                {sentimentEmoji(inbound.sentiment)} {cap(inbound.sentiment)}
              </span>
            )}
          </div>

          {inbound.summary && (
            <div className="result-card summary-card">
              <div className="result-card-title">📝 Post-call summary</div>
              <p className="summary-text">{inbound.summary}</p>
            </div>
          )}

          {inbound.faq_answer && (
            <div className="result-card faq-card">
              <div className="result-card-title">💬 Knowledge base answer</div>
              <p className="summary-text">{inbound.faq_answer}</p>
            </div>
          )}

          {inbound.appointment && (
            <div className="result-card result-card-success">
              <div className="result-card-title">✅ Appointment</div>
              <div className="kv-grid">
                <div>
                  <span>When</span>
                  <b>{fmt(inbound.appointment.datetime)}</b>
                </div>
                <div>
                  <span>Location</span>
                  <b>{inbound.appointment.location}</b>
                </div>
                <div>
                  <span>Status</span>
                  <b>{inbound.appointment.status}</b>
                </div>
              </div>
            </div>
          )}

          <ActionList actions={inbound.actions} />
          <Transcript turns={inbound.call?.transcript} />
        </section>
      )}

      {reminders && (
        <section className="panel">
          <div className="panel-head">
            <h2>Reminder results</h2>
            <span className="count-pill">{reminders.length}</span>
          </div>
          {reminders.length === 0 ? (
            <div className="empty">No upcoming appointments to remind.</div>
          ) : (
            <div className="reminder-list">
              {reminders.map((r) => (
                <div className="result-card" key={r.appointment_id}>
                  <div className="result-card-title">
                    Appointment <code>{r.appointment_id}</code>
                  </div>
                  <p className="script">{r.script}</p>
                  <div className="muted small">call: {r.call_uuid}</div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function ActionList({ actions }: { actions?: string[] }) {
  if (!actions || actions.length === 0) return null;
  return (
    <div className="result-block">
      <h3 className="result-heading">Agent actions</h3>
      <ol className="action-list">
        {actions.map((a, i) => (
          <li key={i}>
            <span className="step-dot">{i + 1}</span>
            <span>{a}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Transcript({ turns }: { turns?: TranscriptTurn[] }) {
  if (!turns || turns.length === 0) return null;
  return (
    <div className="result-block">
      <h3 className="result-heading">Transcript</h3>
      <div className="transcript">
        {turns.map((t, i) => (
          <div key={i} className={`turn turn-${(t.role || 'agent').toLowerCase()}`}>
            <div className="turn-role">{t.role}</div>
            <div className="turn-text">{t.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function fmt(iso?: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function sentimentEmoji(s: string) {
  if (s === 'positive') return '😊';
  if (s === 'negative') return '😟';
  return '😐';
}
