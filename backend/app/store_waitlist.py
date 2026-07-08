"""Waitlist store for cancellation-backfill.

Patients who want an earlier appointment sit on a waitlist. When a slot opens
(e.g. a cancellation), the earliest waitlist entry can be backfilled into the
next open, unbooked availability slot.

Keys:
  waitlist:{id}   hash {patient_uuid, note, created_at}
  waitlist        set of ids
"""

import time
import uuid
from typing import Optional

from .db import get_redis, get_patient


def _now() -> str:
    return str(int(time.time()))


def add_to_waitlist(patient_uuid: str, note: str = "") -> dict:
    r = get_redis()
    entry_id = str(uuid.uuid4())
    created_at = _now()
    r.hset(
        f"waitlist:{entry_id}",
        mapping={
            "patient_uuid": patient_uuid,
            "note": note or "",
            "created_at": created_at,
        },
    )
    r.sadd("waitlist", entry_id)
    return get_waitlist_entry(entry_id)


def get_waitlist_entry(entry_id: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"waitlist:{entry_id}")
    if not data:
        return None
    patient = get_patient(data.get("patient_uuid")) if data.get("patient_uuid") else None
    return {
        "entry_id": entry_id,
        "patient_uuid": data.get("patient_uuid"),
        "patient_name": patient["name"] if patient else None,
        "note": data.get("note") or "",
        "created_at": data.get("created_at"),
    }


def list_waitlist() -> list:
    """Return waitlist entries oldest-first (FIFO) joined with patient_name."""
    r = get_redis()
    ids = r.smembers("waitlist")
    entries = [get_waitlist_entry(i) for i in ids]
    entries = [e for e in entries if e]
    entries.sort(key=lambda e: e.get("created_at", ""))
    return entries


def remove_from_waitlist(entry_id: str) -> bool:
    r = get_redis()
    existed = bool(r.exists(f"waitlist:{entry_id}"))
    r.delete(f"waitlist:{entry_id}")
    r.srem("waitlist", entry_id)
    return existed
