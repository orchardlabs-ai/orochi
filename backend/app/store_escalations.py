"""Human-escalation queue store.

When the voice agent detects a situation that needs a human (e.g. a dental
emergency), it enqueues an escalation here. Front-desk staff work the queue and
resolve entries.

Keys:
  escalation:{id}   hash {patient_uuid, phone, reason, summary, call_uuid,
                          status, created_at}
  escalations       set index of all escalation ids
"""

import time
import uuid
from typing import Optional

from .db import get_redis, get_patient


def _now() -> str:
    return str(int(time.time()))


def enqueue(
    patient_uuid: Optional[str],
    phone: str,
    reason: str,
    summary: str = "",
    call_uuid: Optional[str] = None,
) -> dict:
    r = get_redis()
    escalation_id = str(uuid.uuid4())
    r.hset(
        f"escalation:{escalation_id}",
        mapping={
            "patient_uuid": patient_uuid or "",
            "phone": phone or "",
            "reason": reason or "",
            "summary": summary or "",
            "call_uuid": call_uuid or "",
            "status": "open",
            "created_at": _now(),
        },
    )
    r.sadd("escalations", escalation_id)
    return get_escalation(escalation_id)


def get_escalation(escalation_id: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"escalation:{escalation_id}")
    if not data:
        return None
    patient_uuid = data.get("patient_uuid") or ""
    patient = get_patient(patient_uuid) if patient_uuid else None
    return {
        "id": escalation_id,
        "patient_uuid": patient_uuid or None,
        "patient_name": patient["name"] if patient else None,
        "phone": data.get("phone") or "",
        "reason": data.get("reason") or "",
        "summary": data.get("summary") or "",
        "call_uuid": data.get("call_uuid") or None,
        "status": data.get("status") or "open",
        "created_at": data.get("created_at"),
    }


def list_escalations() -> list:
    """Return escalations newest-first, joined with patient_name."""
    r = get_redis()
    ids = r.smembers("escalations")
    items = [get_escalation(i) for i in ids]
    items = [e for e in items if e]
    items.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    return items


def resolve(escalation_id: str) -> Optional[dict]:
    r = get_redis()
    if not r.exists(f"escalation:{escalation_id}"):
        return None
    r.hset(f"escalation:{escalation_id}", "status", "resolved")
    return get_escalation(escalation_id)


def open_count() -> int:
    return sum(1 for e in list_escalations() if e.get("status") == "open")
