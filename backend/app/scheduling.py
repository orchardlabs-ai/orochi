"""Slot math for clinic scheduling.

Pure(ish) helpers shared by the booking agent and the schedule router so both
enforce the same 45-minute-slot / clinic-hours rules. Availability (which slots
are open for business) and existing bookings live in Redis via ``app.db``; this
module only computes slot boundaries and searches for the next free slot.
"""

from datetime import datetime, timedelta

from .config import settings

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse_hhmm(value: str) -> int:
    """Convert "HH:MM" to minutes since midnight."""
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def slot_times() -> list:
    """Generate the 45-minute grid within clinic hours, e.g. ["08:00", ...].

    A slot is included only if the whole slot fits before closing time.
    """
    open_min = _parse_hhmm(settings.CLINIC_OPEN)
    close_min = _parse_hhmm(settings.CLINIC_CLOSE)
    step = settings.SLOT_MINUTES

    times = []
    cursor = open_min
    while cursor + step <= close_min:
        times.append(f"{cursor // 60:02d}:{cursor % 60:02d}")
        cursor += step
    return times


def weekday_of(date_str: str) -> str:
    """Map an ISO date "YYYY-MM-DD" to a weekday key ("mon".."sun")."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return WEEKDAYS[d.weekday()]


def _today() -> datetime:
    return datetime.now()


def next_available_slot(desired_date, desired_time, horizon_days=None):
    """Find the nearest available + unbooked 45-minute slot.

    Walks forward from the desired datetime (or today when the date is unknown /
    "next available") across dates x slot_times, returning ``(date_str,
    time_str)`` for the first slot that is both marked available in the weekly
    template and not already booked. Returns ``None`` if nothing opens up within
    ``horizon_days``.
    """
    from . import db  # lazy import to avoid a cycle (db has no scheduling dep)

    if horizon_days is None:
        horizon_days = settings.SCHEDULE_HORIZON_DAYS

    slots = slot_times()
    booked = db.booked_slot_datetimes()

    # Resolve the starting point.
    unknown_date = (not desired_date) or desired_date == "next available"
    if unknown_date:
        start_day = _today().date()
        start_time = None
    else:
        try:
            start_day = datetime.strptime(desired_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            start_day = _today().date()
        # Honour any requested time by snapping FORWARD: on the first day we skip
        # slots earlier than it. Works whether or not the time is on-grid, since
        # same-format "HH:MM" strings compare lexicographically ("11:00" > "10:37").
        start_time = desired_time or None

    for offset in range(horizon_days + 1):
        day = start_day + timedelta(days=offset)
        date_str = day.strftime("%Y-%m-%d")
        weekday = WEEKDAYS[day.weekday()]

        for time_str in slots:
            # On the first day, don't offer slots earlier than the requested one.
            if offset == 0 and start_time is not None and time_str < start_time:
                continue
            if not db.is_slot_available(weekday, time_str):
                continue
            if f"{date_str}T{time_str}" in booked:
                continue
            return date_str, time_str

    return None
