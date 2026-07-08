"""Slot math for clinic scheduling.

Pure(ish) helpers shared by the booking agent and the schedule router so both
enforce the same 45-minute-slot / clinic-hours rules. Availability (which slots
are open for business) and existing bookings live in Redis via ``app.db``; this
module only computes slot boundaries and searches for the next free slot.
"""

from datetime import datetime, timedelta
from typing import Optional

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


def procedure_slot_count(duration_minutes) -> int:
    """Number of consecutive 45-min slots a procedure needs (ceil, min 1)."""
    try:
        minutes = int(duration_minutes)
    except (TypeError, ValueError):
        minutes = 0
    step = settings.SLOT_MINUTES
    if minutes <= 0 or step <= 0:
        return 1
    count = (minutes + step - 1) // step
    return max(1, count)


def slot_end_time(start_hhmm, duration_minutes) -> Optional[str]:
    """Return the "HH:MM" end of the booking block that starts at ``start_hhmm``.

    The block spans ``procedure_slot_count(duration_minutes)`` consecutive
    45-minute slots, so the end is ``start + slot_count * SLOT_MINUTES``.
    Returns None when the start time can't be parsed or duration is missing.
    """
    if not start_hhmm or ":" not in str(start_hhmm):
        return None
    try:
        start_min = _parse_hhmm(str(start_hhmm)[:5])
    except (ValueError, TypeError):
        return None
    count = procedure_slot_count(duration_minutes)
    end_min = start_min + count * settings.SLOT_MINUTES
    return f"{(end_min // 60) % 24:02d}:{end_min % 60:02d}"


def compute_end_datetime(datetime_str, duration_minutes) -> Optional[str]:
    """Return the "YYYY-MM-DDThh:mm" end instant for a stored slot datetime.

    None-tolerant: returns None when the datetime or duration is missing or the
    datetime isn't the expected "YYYY-MM-DDThh:mm" shape.
    """
    if not datetime_str or "T" not in str(datetime_str):
        return None
    if duration_minutes in (None, ""):
        return None
    date_str, _, time_str = str(datetime_str).partition("T")
    end = slot_end_time(time_str[:5], duration_minutes)
    if end is None:
        return None
    return f"{date_str}T{end}"


def next_available_slot(
    desired_date,
    desired_time,
    horizon_days=None,
    provider_id=None,
    procedure_slots=1,
):
    """Find the nearest available + unbooked slot (start of a contiguous block).

    Walks forward from the desired datetime (or today when the date is unknown /
    "next available") across dates x slot_times, returning ``(date_str,
    time_str)`` for the first slot where ``procedure_slots`` CONSECUTIVE slot
    times (starting there, same day, no gaps) are all open + unbooked.

    Backward compatible: ``next_available_slot("next available", None)`` still
    works. When ``provider_id`` is None the search spans all providers (the slot
    must be open for *some* provider and unbooked for that provider). When a
    ``provider_id`` is given, availability + bookings are checked against THAT
    provider only.
    """
    from . import db  # lazy import to avoid a cycle (db has no scheduling dep)
    from .store_catalog import list_providers

    if horizon_days is None:
        horizon_days = settings.SCHEDULE_HORIZON_DAYS

    try:
        need = max(1, int(procedure_slots))
    except (TypeError, ValueError):
        need = 1

    slots = slot_times()

    # Candidate providers to check the block against.
    if provider_id is not None:
        provider_ids = [provider_id]
    else:
        provider_ids = [p["provider_id"] for p in list_providers()]
        if not provider_ids:
            provider_ids = [None]  # fall back to global availability template

    # Pre-fetch booked sets + availability per provider for the search.
    booked_by_provider = {}
    for pid in provider_ids:
        if pid is None:
            booked_by_provider[pid] = db.booked_slot_datetimes()
        else:
            booked_by_provider[pid] = db.booked_slots_for_provider(pid)

    def _avail(pid, weekday, time_str) -> bool:
        if pid is None:
            return db.is_slot_available_global(weekday, time_str)
        return db.is_slot_available(pid, weekday, time_str)

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

        for idx, time_str in enumerate(slots):
            # On the first day, don't offer slots earlier than the requested one.
            if offset == 0 and start_time is not None and time_str < start_time:
                continue
            # A block of `need` consecutive slots must fit within the day's grid.
            if idx + need > len(slots):
                continue
            block = slots[idx:idx + need]

            for pid in provider_ids:
                booked = booked_by_provider[pid]
                ok = True
                for bt in block:
                    if not _avail(pid, weekday, bt):
                        ok = False
                        break
                    if f"{date_str}T{bt}" in booked:
                        ok = False
                        break
                if ok:
                    return date_str, time_str

    return None
