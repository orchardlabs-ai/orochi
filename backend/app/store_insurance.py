"""Insurance-on-file and verification store.

Keys:
  patient_insurance:{uuid}      hash {payer, member_id, updated_at}
  insurance_verification:{uuid} hash {result (json), verified_at}
"""

import json
import time
from typing import Optional

from .db import get_redis


def _now() -> str:
    return str(int(time.time()))


def set_patient_insurance(patient_uuid: str, payer: str, member_id: str) -> dict:
    r = get_redis()
    updated_at = _now()
    r.hset(
        f"patient_insurance:{patient_uuid}",
        mapping={
            "payer": payer or "",
            "member_id": member_id or "",
            "updated_at": updated_at,
        },
    )
    return get_patient_insurance(patient_uuid)


def get_patient_insurance(patient_uuid: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"patient_insurance:{patient_uuid}")
    if not data:
        return None
    return {
        "patient_uuid": patient_uuid,
        "payer": data.get("payer") or "",
        "member_id": data.get("member_id") or "",
        "updated_at": data.get("updated_at"),
    }


def save_verification(patient_uuid: str, result: dict) -> dict:
    r = get_redis()
    r.hset(
        f"insurance_verification:{patient_uuid}",
        mapping={
            "result": json.dumps(result),
            "verified_at": result.get("verified_at") or _now(),
        },
    )
    return result


def get_last_verification(patient_uuid: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"insurance_verification:{patient_uuid}")
    if not data or not data.get("result"):
        return None
    try:
        return json.loads(data["result"])
    except (ValueError, TypeError):
        return None
