"""Storage for outbound campaign runs (recall / reactivation / missed-call recovery).

Follows the db.py helper style: module-level functions, uuid ids, a per-entity
hash key ("campaign_run:{id}") plus a set index ("campaign_runs").
"""
import time
import uuid
from typing import Optional

from .db import get_redis

_RUNS_KEY = "campaign_runs"


def _now() -> str:
    return str(int(time.time()))


def record_campaign_run(segment: str, count: int, meta: Optional[dict] = None) -> dict:
    """Persist a single campaign run and return it."""
    r = get_redis()
    run_id = str(uuid.uuid4())
    created_at = _now()
    mapping = {
        "run_id": run_id,
        "segment": segment,
        "count": str(count),
        "created_at": created_at,
    }
    if meta:
        for k, v in meta.items():
            mapping[f"meta_{k}"] = str(v)
    r.hset(f"campaign_run:{run_id}", mapping=mapping)
    r.sadd(_RUNS_KEY, run_id)
    return get_campaign_run(run_id)


def get_campaign_run(run_id: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"campaign_run:{run_id}")
    if not data:
        return None
    return {
        "run_id": run_id,
        "segment": data.get("segment"),
        "count": int(data.get("count") or 0),
        "created_at": data.get("created_at"),
    }


def list_campaign_runs() -> list:
    """All recorded runs, newest first."""
    r = get_redis()
    ids = r.smembers(_RUNS_KEY)
    runs = [get_campaign_run(rid) for rid in ids]
    runs = [run for run in runs if run]
    runs.sort(key=lambda run: run.get("created_at", ""), reverse=True)
    return runs
