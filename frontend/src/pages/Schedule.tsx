import { useEffect, useState } from 'react';
import { api, type ScheduleData } from '../api';

const DAY_LABELS: Record<string, string> = {
  mon: 'Mon',
  tue: 'Tue',
  wed: 'Wed',
  thu: 'Thu',
  fri: 'Fri',
  sat: 'Sat',
  sun: 'Sun',
};

export default function Schedule() {
  const [data, setData] = useState<ScheduleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    api
      .get<ScheduleData>('/api/schedule')
      .then(setData)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const isOpen = (weekday: string, time: string) =>
    data?.availability[weekday]?.includes(time) ?? false;

  const toggleSlot = async (weekday: string, time: string) => {
    if (!data) return;
    const available = !isOpen(weekday, time);
    try {
      const updated = await api.post<ScheduleData>('/api/schedule/slot', {
        weekday,
        time,
        available,
      });
      setData(updated);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const toggleDay = async (weekday: string) => {
    if (!data) return;
    // If every slot is open, close the whole day; otherwise open it fully.
    const fullyOpen = data.slots.every((t) => isOpen(weekday, t));
    try {
      const updated = await api.post<ScheduleData>('/api/schedule/day', {
        weekday,
        available: !fullyOpen,
      });
      setData(updated);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const openCount = data
    ? Object.values(data.availability).reduce((n, times) => n + times.length, 0)
    : 0;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Schedule</h1>
          <p className="page-sub">
            Mark the times your clinic is open for bookings. The voice agent only
            offers patients these slots.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Weekly availability</h2>
          <span className="count-pill">{openCount}</span>
        </div>
        <p className="panel-note">
          A recurring template. Click a cell to open or close a{' '}
          {data ? data.slot_minutes : 45}-minute slot, or a day header to toggle the
          whole column. Slot boundaries are internal and never shown to patients.
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
