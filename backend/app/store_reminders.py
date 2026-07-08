"""Configurable reminder cadence + outbound reminder jobs (DEMO).

A cadence offset is one of a small fixed set of "how far before the
appointment" markers:

    "1w"      -> 7 days before
    "2d"      -> 2 days before
    "day-of"  -> 0 days before

The globally-enabled cadence is stored in a Redis hash ``reminder_config``
(one field per known offset, value "1"/"0"). By default all three are enabled.

A reminder JOB is one {appointment, cadence-offset} pair for every active
(scheduled/confirmed) appointment. For the DEMO there is no real clock, so
``compute_due_jobs()`` treats every computed job as "due now".

A RUN is a recorded batch send:

    reminder_run:{id}   -> hash of a single run record
    reminder_runs       -> set index of all run ids
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from .db import get_redis, get_patient, list_appointments

# Known cadence offsets, in send order (earliest first), with day-offsets.
CADENCE_OFFSETS = [
    {"key": "1w", "label": "1 week before", "days": 7},
    {"key": "2d", "label": "2 days before", "days": 2},
    {"key": "day-of", "label": "Day of", "days": 0},
]
_CADENCE_BY_KEY = {c["key"]: c for c in CADENCE_OFFSETS}
_DEFAULT_ENABLED = [c["key"] for c in CADENCE_OFFSETS]

_CONFIG_KEY = "reminder_config"
_ACTIVE_STATUSES = {"scheduled", "confirmed"}


def _now() -> str:
    return str(int(time.time()))


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def get_config() -> dict:
    """Return the cadence config as {"cadence": [enabled offset keys],
    "options": [{key,label,days,enabled}, ...]}."""
    r = get_redis()
    raw = r.hgetall(_CONFIG_KEY)
    if not raw:
        enabled = set(_DEFAULT_ENABLED)
    else:
        enabled = {k for k in _CADENCE_BY_KEY if raw.get(k) == "1"}
    options = [
        {**c, "enabled": c["key"] in enabled} for c in CADENCE_OFFSETS
    ]
    cadence = [c["key"] for c in CADENCE_OFFSETS if c["key"] in enabled]
    return {"cadence": cadence, "options": options}


def set_config(cadence_list: List[str]) -> dict:
    """Persist which cadence offsets are enabled. Unknown keys are ignored."""
    r = get_redis()
    wanted = set(cadence_list or [])
    mapping = {c["key"]: ("1" if c["key"] in wanted else "0") for c in CADENCE_OFFSETS}
    r.hset(_CONFIG_KEY, mapping=mapping)
    return get_config()


# ---------------------------------------------------------------------------
# Due jobs
# ---------------------------------------------------------------------------
def _appt_date(appt: dict) -> Optional[datetime]:
    dt = appt.get("datetime")
    if not dt:
        return None
    try:
        return datetime.strptime(dt[:16], "%Y-%m-%dT%H:%M")
    except (ValueError, TypeError):
        try:
            return datetime.strptime(dt[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None


def compute_due_jobs() -> List[dict]:
    """One job per {active appointment, enabled cadence offset}.

    DEMO: every computed job is considered due now. ``send_on`` is the ideal
    calendar date the reminder would fire (appointment date minus the offset)."""
    config = get_config()
    enabled = config["cadence"]
    jobs = []
    for appt in list_appointments():
        if appt.get("status") not in _ACTIVE_STATUSES:
            continue
        appt_dt = _appt_date(appt)
        for key in enabled:
            offset = _CADENCE_BY_KEY[key]
            send_on = None
            if appt_dt is not None:
                send_on = (appt_dt - timedelta(days=offset["days"])).strftime("%Y-%m-%d")
            jobs.append(
                {
                    "appointment_id": appt.get("appointment_id"),
                    "patient_uuid": appt.get("patient_uuid"),
                    "patient_name": appt.get("patient_name"),
                    "appointment_datetime": appt.get("datetime"),
                    "channel": "sms",
                    "cadence": key,
                    "cadence_label": offset["label"],
                    "send_on": send_on,
                    "status": "due",
                }
            )
    return jobs


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------
def log_run(jobs: List[dict]) -> dict:
    """Record a batch send of ``jobs`` (already-sent job dicts)."""
    r = get_redis()
    run_id = str(uuid.uuid4())
    created_at = _now()
    r.hset(
        f"reminder_run:{run_id}",
        mapping={
            "sent": len(jobs),
            "jobs": json.dumps(jobs or []),
            "created_at": created_at,
        },
    )
    r.sadd("reminder_runs", run_id)
    return get_run(run_id)


def get_run(run_id: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"reminder_run:{run_id}")
    if not data:
        return None
    try:
        jobs = json.loads(data.get("jobs") or "[]")
    except (ValueError, TypeError):
        jobs = []
    try:
        sent = int(data.get("sent") or 0)
    except (TypeError, ValueError):
        sent = len(jobs)
    return {
        "run_id": run_id,
        "sent": sent,
        "jobs": jobs,
        "created_at": data.get("created_at"),
    }


def list_runs() -> List[dict]:
    r = get_redis()
    ids = r.smembers("reminder_runs")
    runs = [get_run(rid) for rid in ids]
    runs = [run for run in runs if run]
    runs.sort(key=lambda run: run.get("created_at", ""), reverse=True)
    return runs
