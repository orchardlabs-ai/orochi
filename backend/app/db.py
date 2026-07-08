import json
import time
import uuid
from typing import Optional

from .config import settings

_redis = None


def get_redis():
    """Return a shared Redis client, falling back to fakeredis if the real
    Dragonfly/Redis server is unreachable."""
    global _redis
    if _redis is not None:
        return _redis

    try:
        import redis as _redis_lib

        client = _redis_lib.from_url(
            settings.DRAGONFLY_URL, decode_responses=True
        )
        client.ping()
        _redis = client
    except Exception:
        import fakeredis

        _redis = fakeredis.FakeStrictRedis(decode_responses=True)

    return _redis


def _now() -> str:
    return str(int(time.time()))


def clinic_timezone() -> str:
    """Clinic timezone string (safe default; config.py not required)."""
    return getattr(settings, "CLINIC_TZ", "America/New_York")


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------
def create_patient(name: str, phone: str) -> dict:
    r = get_redis()
    existing = r.get(f"phone:{phone}")
    if existing:
        return get_patient(existing)

    patient_uuid = str(uuid.uuid4())
    created_at = _now()
    r.hset(
        f"patient:{patient_uuid}",
        mapping={"name": name, "phone": phone, "created_at": created_at},
    )
    r.set(f"phone:{phone}", patient_uuid)
    r.sadd("patients", patient_uuid)
    return {
        "patient_uuid": patient_uuid,
        "name": name,
        "phone": phone,
        "created_at": created_at,
    }


def get_patient(patient_uuid: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"patient:{patient_uuid}")
    if not data:
        return None
    return {
        "patient_uuid": patient_uuid,
        "name": data.get("name"),
        "phone": data.get("phone"),
        "created_at": data.get("created_at"),
    }


def create_or_get_patient(phone: str, name: str) -> dict:
    """Agent-facing alias: fetch an existing patient by phone or create one.

    Mirrors the contract the LangGraph nodes expect
    (``create_or_get_patient(phone, name) -> patient dict``). ``create_patient``
    already de-duplicates by phone, so this simply reorders the arguments.
    """
    return create_patient(name, phone)


def get_patient_by_phone(phone: str) -> Optional[dict]:
    r = get_redis()
    patient_uuid = r.get(f"phone:{phone}")
    if not patient_uuid:
        return None
    return get_patient(patient_uuid)


def list_patients() -> list:
    r = get_redis()
    uuids = r.smembers("patients")
    patients = [get_patient(u) for u in uuids]
    patients = [p for p in patients if p]
    patients.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return patients


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------
def create_appointment(
    patient_uuid: str,
    datetime_str: str,
    location: str,
    status: str = "scheduled",
    provider_id: Optional[str] = None,
    procedure_id: Optional[str] = None,
    duration_minutes: Optional[int] = None,
) -> dict:
    r = get_redis()
    appointment_id = str(uuid.uuid4())
    created_at = _now()
    r.hset(
        f"appointment:{appointment_id}",
        mapping={
            "patient_uuid": patient_uuid,
            "datetime": datetime_str,
            "location": location,
            "status": status,
            "created_at": created_at,
            "provider_id": provider_id or "",
            "procedure_id": procedure_id or "",
            "duration_minutes": "" if duration_minutes is None else int(duration_minutes),
        },
    )
    r.rpush(f"appointments_by_patient:{patient_uuid}", appointment_id)
    r.sadd("appointments", appointment_id)
    return get_appointment(appointment_id)


def get_appointment(appointment_id: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"appointment:{appointment_id}")
    if not data:
        return None
    raw_duration = data.get("duration_minutes")
    try:
        duration = int(raw_duration) if raw_duration not in (None, "") else None
    except (TypeError, ValueError):
        duration = None
    datetime_str = data.get("datetime")
    end_time = None
    if datetime_str and duration is not None:
        try:
            from .scheduling import compute_end_datetime

            end_time = compute_end_datetime(datetime_str, duration)
        except Exception:
            end_time = None
    return {
        "appointment_id": appointment_id,
        "patient_uuid": data.get("patient_uuid"),
        "datetime": datetime_str,
        "location": data.get("location"),
        "status": data.get("status"),
        "created_at": data.get("created_at"),
        "provider_id": data.get("provider_id") or None,
        "procedure_id": data.get("procedure_id") or None,
        "duration_minutes": duration,
        "end_time": end_time,
        "timezone": clinic_timezone(),
    }


def update_appointment_status(appointment_id: str, status: str) -> Optional[dict]:
    r = get_redis()
    if not r.exists(f"appointment:{appointment_id}"):
        return None
    r.hset(f"appointment:{appointment_id}", "status", status)
    return get_appointment(appointment_id)


def list_appointments() -> list:
    r = get_redis()
    ids = r.smembers("appointments")
    appointments = []
    for aid in ids:
        appt = get_appointment(aid)
        if not appt:
            continue
        patient = get_patient(appt["patient_uuid"])
        appt["patient_name"] = patient["name"] if patient else None
        _enrich_appointment(appt)
        appointments.append(appt)
    appointments.sort(key=lambda a: a.get("datetime", ""))
    return appointments


def _enrich_appointment(appt: dict) -> dict:
    """Add provider_name / procedure_name (None-tolerant) to an appointment dict."""
    from . import store_catalog

    provider_name = None
    procedure_name = None
    if appt.get("provider_id"):
        try:
            provider = store_catalog.get_provider(appt["provider_id"])
            provider_name = provider["name"] if provider else None
        except Exception:
            provider_name = None
    if appt.get("procedure_id"):
        try:
            procedure = store_catalog.get_procedure(appt["procedure_id"])
            procedure_name = procedure["name"] if procedure else None
        except Exception:
            procedure_name = None
    appt["provider_name"] = provider_name
    appt["procedure_name"] = procedure_name
    return appt


def list_upcoming_appointments() -> list:
    """Agent-facing alias: appointments the reminder flow should call about.

    The LangGraph reminder batch expects ``list_upcoming_appointments()``; the
    prototype treats every stored appointment as upcoming.
    """
    return list_appointments()


def list_appointments_for_patient(patient_uuid: str) -> list:
    r = get_redis()
    ids = r.lrange(f"appointments_by_patient:{patient_uuid}", 0, -1)
    appointments = [get_appointment(aid) for aid in ids]
    appointments = [a for a in appointments if a]
    appointments.sort(key=lambda a: a.get("datetime", ""))
    return appointments


# ---------------------------------------------------------------------------
# Calls
# ---------------------------------------------------------------------------
def create_call(
    patient_uuid: str,
    direction: str,
    status: str = "in_progress",
    transcript: Optional[list] = None,
) -> dict:
    r = get_redis()
    call_uuid = str(uuid.uuid4())
    started_at = _now()
    r.hset(
        f"call:{call_uuid}",
        mapping={
            "patient_uuid": patient_uuid or "",
            "direction": direction,
            "status": status,
            "started_at": started_at,
            "ended_at": "",
            "transcript": json.dumps(transcript or []),
        },
    )
    r.sadd("calls", call_uuid)
    return get_call(call_uuid)


def update_call(
    call_uuid: str,
    status: Optional[str] = None,
    transcript: Optional[list] = None,
    ended: bool = False,
    patient_uuid: Optional[str] = None,
) -> Optional[dict]:
    r = get_redis()
    if not r.exists(f"call:{call_uuid}"):
        return None
    mapping = {}
    if status is not None:
        mapping["status"] = status
    if patient_uuid is not None:
        mapping["patient_uuid"] = patient_uuid
    if transcript is not None:
        # Accept either a list (preferred) or an already-serialized string.
        if isinstance(transcript, str):
            mapping["transcript"] = transcript
        else:
            mapping["transcript"] = json.dumps(transcript)
    if ended:
        mapping["ended_at"] = _now()
    if mapping:
        r.hset(f"call:{call_uuid}", mapping=mapping)
    return get_call(call_uuid)


def get_call(call_uuid: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"call:{call_uuid}")
    if not data:
        return None
    try:
        transcript = json.loads(data.get("transcript") or "[]")
    except (ValueError, TypeError):
        transcript = []
    return {
        "call_uuid": call_uuid,
        "patient_uuid": data.get("patient_uuid") or None,
        "direction": data.get("direction"),
        "status": data.get("status"),
        "started_at": data.get("started_at"),
        "ended_at": data.get("ended_at") or None,
        "transcript": transcript,
    }


def list_calls() -> list:
    r = get_redis()
    uuids = r.smembers("calls")
    calls = []
    for cu in uuids:
        call = get_call(cu)
        if not call:
            continue
        patient = get_patient(call["patient_uuid"]) if call["patient_uuid"] else None
        call["patient_name"] = patient["name"] if patient else None
        calls.append(call)
    calls.sort(key=lambda c: c.get("started_at", ""), reverse=True)
    return calls


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def create_user(email: str, password_hash: str) -> dict:
    r = get_redis()
    r.hset(
        f"user:{email}",
        mapping={"email": email, "password_hash": password_hash},
    )
    return {"email": email}


def get_user(email: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(f"user:{email}")
    if not data:
        return None
    return {"email": data.get("email"), "password_hash": data.get("password_hash")}


def user_exists(email: str) -> bool:
    r = get_redis()
    return bool(r.exists(f"user:{email}"))


# ---------------------------------------------------------------------------
# Schedule availability (weekly recurring template)
# ---------------------------------------------------------------------------
# PER-PROVIDER availability: Redis set "schedule:availability:{provider_id}"
# whose members are "{weekday}:{HH:MM}" (e.g. "mon:09:30") for every slot open
# for that provider. The old global set "schedule:availability" is deprecated
# but kept readable for legacy fallback (is_slot_available_global).
_AVAILABILITY_KEY = "schedule:availability"


def _provider_availability_key(provider_id: str) -> str:
    return f"schedule:availability:{provider_id}"


def get_availability(provider_id: str) -> dict:
    """Return one provider's weekly template as {weekday: [sorted HH:MM, ...]}."""
    from .scheduling import WEEKDAYS

    r = get_redis()
    result = {day: [] for day in WEEKDAYS}
    for member in r.smembers(_provider_availability_key(provider_id)):
        weekday, _, time = member.partition(":")
        if weekday in result:
            result[weekday].append(time)
    for day in result:
        result[day].sort()
    return result


def is_slot_available(provider_id: str, weekday: str, time: str) -> bool:
    r = get_redis()
    return bool(
        r.sismember(_provider_availability_key(provider_id), f"{weekday}:{time}")
    )


def set_slot_availability(
    provider_id: str, weekday: str, time: str, available: bool
) -> dict:
    r = get_redis()
    member = f"{weekday}:{time}"
    key = _provider_availability_key(provider_id)
    if available:
        r.sadd(key, member)
    else:
        r.srem(key, member)
    return get_availability(provider_id)


def set_day_availability(provider_id: str, weekday: str, available: bool) -> dict:
    """Toggle an entire weekday column across all slot times for one provider."""
    from .scheduling import slot_times

    r = get_redis()
    key = _provider_availability_key(provider_id)
    members = [f"{weekday}:{t}" for t in slot_times()]
    if available:
        r.sadd(key, *members)
    else:
        r.srem(key, *members)
    return get_availability(provider_id)


# --- Legacy global availability (deprecated; read-only fallback) ------------
def is_slot_available_global(weekday: str, time: str) -> bool:
    r = get_redis()
    return bool(r.sismember(_AVAILABILITY_KEY, f"{weekday}:{time}"))


def availability_is_empty() -> bool:
    r = get_redis()
    return r.scard(_AVAILABILITY_KEY) == 0


def ensure_provider_availability_seeded() -> None:
    """Seed Mon-Fri, all slots, for any provider whose availability set is empty."""
    from .scheduling import slot_times, WEEKDAYS
    from .store_catalog import list_providers, ensure_seeded

    ensure_seeded()
    r = get_redis()
    open_days = WEEKDAYS[:5]
    times = slot_times()
    for provider in list_providers():
        pid = provider["provider_id"]
        key = _provider_availability_key(pid)
        if r.scard(key) == 0:
            members = [f"{wd}:{t}" for wd in open_days for t in times]
            if members:
                r.sadd(key, *members)


def booked_slot_datetimes() -> set:
    """Datetimes ("YYYY-MM-DDThh:mm") of active (non-cancelled) appointments.

    Kept for backward compatibility (does not expand across durations)."""
    return {
        appt["datetime"]
        for appt in list_appointments()
        if appt.get("datetime") and appt.get("status") != "cancelled"
    }


def booked_slots_for_provider(provider_id: str) -> set:
    """All "YYYY-MM-DDThh:mm" slot-instants occupied by one provider's active
    appointments, expanded across each appointment's duration."""
    from datetime import datetime, timedelta

    from .scheduling import slot_times, procedure_slot_count

    slots = slot_times()
    slot_index = {t: i for i, t in enumerate(slots)}
    occupied = set()

    for appt in list_appointments():
        if appt.get("status") == "cancelled":
            continue
        if appt.get("provider_id") != provider_id:
            continue
        dt = appt.get("datetime")
        if not dt or "T" not in dt:
            continue
        date_str, _, time_str = dt.partition("T")
        time_str = time_str[:5]
        count = procedure_slot_count(appt.get("duration_minutes") or 0)
        start_idx = slot_index.get(time_str)
        if start_idx is None:
            # Off-grid start; just occupy the literal instant.
            occupied.add(f"{date_str}T{time_str}")
            continue
        for i in range(start_idx, min(start_idx + count, len(slots))):
            occupied.add(f"{date_str}T{slots[i]}")
    return occupied
