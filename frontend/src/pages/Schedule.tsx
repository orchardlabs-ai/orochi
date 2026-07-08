import { useEffect, useState } from 'react';
import { api } from '../api';
import './Schedule.css';

const DAY_LABELS: Record<string, string> = {
  mon: 'Mon',
  tue: 'Tue',
  wed: 'Wed',
  thu: 'Thu',
  fri: 'Fri',
  sat: 'Sat',
  sun: 'Sun',
};

interface ScheduleProvider {
  provider_id: string;
  name: string;
  color?: string;
}

interface ScheduleData {
  open: string;
  close: string;
  slot_minutes: number;
  weekdays: string[];
  slots: string[];
  providers: ScheduleProvider[];
  // availability keyed by provider_id -> { weekday: [times] }
  availability: Record<string, Record<string, string[]>>;
}

export default function Schedule() {
  const [data, setData] = useState<ScheduleData | null>(null);
  const [providerId, setProviderId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    api
      .get<ScheduleData>('/api/schedule')
      .then((d) => {
        setData(d);
        setProviderId((prev) =>
          prev && d.providers.some((p) => p.provider_id === prev)
            ? prev
            : d.providers[0]?.provider_id ?? '',
        );
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const avail = data && providerId ? data.availability[providerId] ?? {} : {};

  const isOpen = (weekday: string, time: string) =>
    avail[weekday]?.includes(time) ?? false;

  const applyUpdate = (updated: Record<string, string[]>) => {
    setData((prev) =>
      prev
        ? {
            ...prev,
            availability: { ...prev.availability, [providerId]: updated },
          }
        : prev,
    );
  };

  const toggleSlot = async (weekday: string, time: string) => {
    if (!data || !providerId) return;
    const available = !isOpen(weekday, time);
    try {
      const updated = await api.post<Record<string, string[]>>('/api/schedule/slot', {
        provider_id: providerId,
        weekday,
        time,
        available,
      });
      applyUpdate(updated);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const toggleDay = async (weekday: string) => {
    if (!data || !providerId) return;
    // If every slot is open, close the whole day; otherwise open it fully.
    const fullyOpen = data.slots.every((t) => isOpen(weekday, t));
    try {
      const updated = await api.post<Record<string, string[]>>('/api/schedule/day', {
        provider_id: providerId,
        weekday,
        available: !fullyOpen,
      });
      applyUpdate(updated);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const openCount = Object.values(avail).reduce((n, times) => n + times.length, 0);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Schedule</h1>
          <p className="page-sub">
            Mark the times each provider is open for bookings. The voice agent only
            offers patients these slots.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      {data && data.providers.length > 0 && (
        <div className="provider-pills" role="tablist" aria-label="Providers">
          {data.providers.map((p) => (
            <button
              key={p.provider_id}
              type="button"
              role="tab"
              aria-selected={p.provider_id === providerId}
              className={
                'provider-pill' + (p.provider_id === providerId ? ' active' : '')
              }
              onClick={() => setProviderId(p.provider_id)}
            >
              <span
                className="provider-dot"
                style={{ background: p.color ?? 'var(--jade)' }}
                aria-hidden="true"
              />
              {p.name}
            </button>
          ))}
        </div>
      )}

      <section className="panel">
        <div className="panel-head">
          <h2>Weekly availability</h2>
          <span className="count-pill">{openCount}</span>
        </div>
        <p className="panel-note">
          A recurring template for the selected provider. Click a cell to open or
          close a {data ? data.slot_minutes : 45}-minute slot, or a day header to
          toggle the whole column. Slot boundaries are internal and never shown to
          patients.
        </p>

        {loading || !data ? (
          <div className="empty">Loading…</div>
        ) : (
          <div className="sched-scroll">
            <div
              className="sched-grid"
              style={{ gridTemplateColumns: `76px repeat(${data.weekdays.length}, 1fr)` }}
            >
              <div className="sched-corner" aria-hidden="true" />
              {data.weekdays.map((wd) => (
                <button
                  key={wd}
                  type="button"
                  className="sched-daybtn"
                  onClick={() => toggleDay(wd)}
                  title={`Toggle all of ${DAY_LABELS[wd] ?? wd}`}
                >
                  {DAY_LABELS[wd] ?? wd}
                </button>
              ))}

              {data.slots.map((time) => (
                <div className="sched-row" key={time} style={{ display: 'contents' }}>
                  <div className="sched-time">{time}</div>
                  {data.weekdays.map((wd) => {
                    const open = isOpen(wd, time);
                    return (
                      <button
                        key={wd + time}
                        type="button"
                        className={'sched-cell' + (open ? ' available' : '')}
                        onClick={() => toggleSlot(wd, time)}
                        aria-pressed={open}
                        title={`${DAY_LABELS[wd] ?? wd} ${time} — ${open ? 'open' : 'closed'}`}
                      >
                        {open ? '✓' : ''}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="sched-legend">
          <span className="sched-legend-item">
            <span className="sched-swatch available" /> Open for bookings
          </span>
          <span className="sched-legend-item">
            <span className="sched-swatch" /> Closed
          </span>
        </div>
      </section>
    </div>
  );
}
