"""Catalog store: providers and procedure types.

Module-level functions over the shared Redis client (decode_responses=True),
following the same style as ``app.db``: uuid ids and a set index per entity.

Redis layout (per contract):
  provider:{id}   hash  {name, specialty, color};   set "providers"
  procedure:{id}  hash  {name, duration_minutes, color};  set "procedures"
"""

import uuid

from .db import get_redis

# Default seed data (uuid ids assigned at seed time).
_SEED_PROVIDERS = [
    ("Dr. Alice Reyes", "General", "#0e8f6a"),
    ("Dr. Ben Cho", "Hygiene", "#2f7fd1"),
    ("Dr. Mia Chan", "Orthodontics", "#ff6a45"),
]

_SEED_PROCEDURES = [
    ("Checkup", 45, "#0e8f6a"),
    ("Cleaning", 45, "#2f7fd1"),
    ("Filling", 90, "#d9911f"),
    ("Root Canal", 135, "#d94a5f"),
    ("Consultation", 45, "#7a5cff"),
]


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
def create_provider(name: str, specialty: str = "", color: str = "#0e8f6a") -> dict:
    r = get_redis()
    provider_id = str(uuid.uuid4())
    r.hset(
        f"provider:{provider_id}",
        mapping={
            "name": name,
            "specialty": specialty or "",
            "color": color or "#0e8f6a",
        },
    )
    r.sadd("providers", provider_id)
    return get_provider(provider_id)


def get_provider(provider_id: str):
    r = get_redis()
    data = r.hgetall(f"provider:{provider_id}")
    if not data:
        return None
    return {
        "provider_id": provider_id,
        "name": data.get("name"),
        "specialty": data.get("specialty", ""),
        "color": data.get("color", "#0e8f6a"),
    }


def list_providers() -> list:
    r = get_redis()
    ids = r.smembers("providers")
    providers = [get_provider(pid) for pid in ids]
    providers = [p for p in providers if p]
    providers.sort(key=lambda p: (p["name"] or "").lower())
    return providers


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------
def create_procedure(
    name: str, duration_minutes: int = 45, color: str = "#0e8f6a"
) -> dict:
    r = get_redis()
    procedure_id = str(uuid.uuid4())
    r.hset(
        f"procedure:{procedure_id}",
        mapping={
            "name": name,
            "duration_minutes": int(duration_minutes),
            "color": color or "#0e8f6a",
        },
    )
    r.sadd("procedures", procedure_id)
    return get_procedure(procedure_id)


def get_procedure(procedure_id: str):
    r = get_redis()
    data = r.hgetall(f"procedure:{procedure_id}")
    if not data:
        return None
    try:
        duration = int(data.get("duration_minutes") or 45)
    except (TypeError, ValueError):
        duration = 45
    return {
        "procedure_id": procedure_id,
        "name": data.get("name"),
        "duration_minutes": duration,
        "color": data.get("color", "#0e8f6a"),
    }


def list_procedures() -> list:
    r = get_redis()
    ids = r.smembers("procedures")
    procedures = [get_procedure(pid) for pid in ids]
    procedures = [p for p in procedures if p]
    procedures.sort(key=lambda p: (p["duration_minutes"], (p["name"] or "").lower()))
    return procedures


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------
def ensure_seeded() -> None:
    """Seed the default providers & procedures if their sets are empty."""
    r = get_redis()
    if not r.exists("providers") or r.scard("providers") == 0:
        for name, specialty, color in _SEED_PROVIDERS:
            create_provider(name, specialty, color)
    if not r.exists("procedures") or r.scard("procedures") == 0:
        for name, duration, color in _SEED_PROCEDURES:
            create_procedure(name, duration, color)
