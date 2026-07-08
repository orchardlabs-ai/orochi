"""Communications log store.

Key namespace:
    comm:{id}          -> hash of a single communication record
    communications     -> set index of all comm ids

A communication record captures an SMS / email / voice message in either
direction (outbound = clinic -> patient, inbound = patient -> clinic).
"""

import json
import time
import uuid
from typing import Optional

from .db import get_redis, get_patient

VALID_CHANNELS = {"sms", "email", "voice"}
VALID_DIRECTIONS = {"inbound", "outbound"}


def _now() -> str:
    return str(int(time.time()))


def log_communication(
    patient_uuid: str,
    channel: str,
    direction: str,
    body: str,
    status: str = "sent",
    meta: Optional[dict] = None,
) -> dict:
    r = get_redis()
    comm_id = str(uuid.uuid4())
    created_at = _now()
    r.hset(
        f"comm:{comm_id}",
        mapping={
            "patient_uuid": patient_uuid or "",
            "channel": channel,
            "direction": direction,
            "body": body,
            "status": status,
            "meta": json.dumps(meta or {}),
            "created_at": created_at,
        },
    )
    r.sadd("communications", comm_id)
    return get_communication(comm_id)


def get_communication(comm_id: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"comm:{comm_id}")
    if not data:
        return None
    try:
        meta = json.loads(data.get("meta") or "{}")
    except (ValueError, TypeError):
        meta = {}
    patient_uuid = data.get("patient_uuid") or ""
    patient = get_patient(patient_uuid) if patient_uuid else None
    return {
        "comm_id": comm_id,
        "patient_uuid": patient_uuid,
        "patient_name": patient["name"] if patient else None,
        "channel": data.get("channel"),
        "direction": data.get("direction"),
        "body": data.get("body"),
        "status": data.get("status"),
        "meta": meta,
        "created_at": data.get("created_at"),
    }


def list_communications() -> list:
    r = get_redis()
    ids = r.smembers("communications")
    comms = [get_communication(cid) for cid in ids]
    comms = [c for c in comms if c]
    comms.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    return comms
