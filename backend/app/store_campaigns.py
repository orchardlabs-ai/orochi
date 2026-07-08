"""Campaign segment library + outbound campaign run history.

The segment library is computed READ-ONLY from existing patient / appointment /
call / insurance data. Each segment carries an intent CATEGORY so outreach can
be framed as communication (not only booking).

Run history follows the db.py helper style: module-level functions, uuid ids, a
per-entity hash key ("campaign_run:{id}") plus a set index ("campaign_runs").
"""
import time
import uuid
from datetime import datetime
from typing import Optional

from .db import (
    get_redis,
    list_patients,
    list_appointments,
    list_appointments_for_patient,
    list_calls,
)

_RUNS_KEY = "campaign_runs"

_ACTIVE_STATUSES = {"scheduled", "confirmed"}

# Display labels for the five intent categories.
CATEGORY_LABELS = {
    "appointments": "Appointments",
    "engagement": "Engagement",
    "payment": "Payment",
    "reputation": "Reputation",
    "other": "Other",
}

# Ordered segment metadata. Order controls display order in /segments.
_SEGMENTS = [
    {
        "key": "recare",
        "label": "Recare recall",
        "category": "appointments",
        "description": "Patients with no active upcoming appointment — due for a recall.",
    },
    {
        "key": "hygiene_recall",
        "label": "Hygiene recall",
        "category": "appointments",
        "description": "Past cleaning patients with no active upcoming appointment.",
    },
    {
        "key": "cancellation_followup",
        "label": "Cancellation follow-up",
        "category": "appointments",
        "description": "Patients who cancelled and have not rebooked.",
    },
    {
        "key": "missed_call_recovery",
        "label": "Missed-call recovery",
        "category": "appointments",
        "description": "Patients who called in but never booked an appointment.",
    },
    {
        "key": "reactivation",
        "label": "Reactivation",
        "category": "engagement",
        "description": "Lapsed patients (oldest third by record age) to win back.",
    },
    {
        "key": "post_treatment_checkin",
        "label": "Post-treatment check-in",
        "category": "engagement",
        "description": "Patients with a recent treated visit — check on how they are doing.",
    },
    {
        "key": "new_patient_welcome",
        "label": "New patient welcome",
        "category": "engagement",
        "description": "Newest patients — a warm welcome to the practice.",
    },
    {
        "key": "insurance_expiring",
        "label": "Insurance benefits reminder",
        "category": "payment",
        "description": "Patients with insurance on file — use year-end benefits before they expire.",
    },
    {
        "key": "review_request",
        "label": "Review request",
        "category": "reputation",
        "description": "Patients with a completed visit — ask for an online review.",
    },
    {
        "key": "referral_request",
        "label": "Referral request",
        "category": "reputation",
        "description": "Loyal patients (2+ visits) — ask them to refer friends and family.",
    },
]

_SEGMENTS_BY_KEY = {s["key"]: s for s in _SEGMENTS}

# Per-CATEGORY SMS message templates. {name} is filled per patient.
_CATEGORY_MESSAGES = {
    "appointments": (
        "Hi {name}, it's your clinic — it's time to book your next visit. "
        "Reply or call us and we'll find a convenient time for you."
    ),
    "engagement": (
        "Hi {name}, just checking in from your clinic. We're thinking of you and "
        "here whenever you need us — reply anytime."
    ),
    "payment": (
        "Hi {name}, a friendly reminder from your clinic: your insurance benefits "
        "may reset soon. Reply to make the most of them before they expire."
    ),
    "reputation": (
        "Hi {name}, thank you for trusting your clinic with your care! "
        "We'd love a quick review or a referral to friends and family — reply to help."
    ),
    "other": (
        "Hi {name}, a quick note from your clinic. Reply anytime — we're happy to help."
    ),
}


def _now() -> str:
    return str(int(time.time()))


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, CATEGORY_LABELS["other"])


def message_for_category(category: str, name: str) -> str:
    template = _CATEGORY_MESSAGES.get(category, _CATEGORY_MESSAGES["other"])
    return template.format(name=name or "there")


# ---------------------------------------------------------------------------
# Read-only segment computation
# ---------------------------------------------------------------------------
def _today_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _appt_date(appt: dict) -> str:
    """Date prefix (YYYY-MM-DD) of an appointment datetime, or ''."""
    dt = appt.get("datetime") or ""
    return dt[:10]


def _appointments_by_patient() -> dict:
    """Map patient_uuid -> list of that patient's appointment dicts."""
    by_patient: dict = {}
    for appt in list_appointments():
        uid = appt.get("patient_uuid")
        if not uid:
            continue
        by_patient.setdefault(uid, []).append(appt)
    return by_patient


def _patients_with_active_appointment(by_patient: dict) -> set:
    active = set()
    for uid, appts in by_patient.items():
        for a in appts:
            if a.get("status") in _ACTIVE_STATUSES:
                active.add(uid)
                break
    return active


def _inbound_call_patients() -> set:
    out = set()
    for call in list_calls():
        if call.get("direction") == "inbound" and call.get("patient_uuid"):
            out.add(call["patient_uuid"])
    return out


def _patients_with_insurance(patients: list) -> set:
    from .store_insurance import get_patient_insurance

    out = set()
    for p in patients:
        uid = p.get("patient_uuid")
        if not uid:
            continue
        try:
            if get_patient_insurance(uid):
                out.add(uid)
        except Exception:
            pass
    return out


def segment_patients(key: str) -> list:
    """Return the list of patient dicts belonging to a segment.

    Raises KeyError for an unknown segment key so callers can map to 404.
    """
    if key not in _SEGMENTS_BY_KEY:
        raise KeyError(key)

    patients = list_patients()
    by_patient = _appointments_by_patient()
    today = _today_date()

    def has_active(uid: str) -> bool:
        return any(
            a.get("status") in _ACTIVE_STATUSES for a in by_patient.get(uid, [])
        )

    if key == "recare":
        return [p for p in patients if not has_active(p["patient_uuid"])]

    if key == "hygiene_recall":
        out = []
        for p in patients:
            uid = p["patient_uuid"]
            if has_active(uid):
                continue
            for a in by_patient.get(uid, []):
                pname = (a.get("procedure_name") or "").lower()
                if "cleaning" in pname and _appt_date(a) and _appt_date(a) < today:
                    out.append(p)
                    break
        return out

    if key == "cancellation_followup":
        out = []
        for p in patients:
            uid = p["patient_uuid"]
            if has_active(uid):
                continue
            if any(a.get("status") == "cancelled" for a in by_patient.get(uid, [])):
                out.append(p)
        return out

    if key == "missed_call_recovery":
        inbound = _inbound_call_patients()
        return [
            p
            for p in patients
            if p["patient_uuid"] in inbound and not by_patient.get(p["patient_uuid"])
        ]

    if key == "reactivation":
        by_age = sorted(patients, key=lambda p: p.get("created_at", ""))
        third = max(1, len(by_age) // 3) if by_age else 0
        return by_age[:third]

    if key == "post_treatment_checkin":
        out = []
        for p in patients:
            uid = p["patient_uuid"]
            for a in by_patient.get(uid, []):
                d = _appt_date(a)
                if d and d < today and a.get("procedure_name"):
                    out.append(p)
                    break
        return out

    if key == "new_patient_welcome":
        # list_patients is already newest-first.
        if not patients:
            return []
        top = max(1, round(len(patients) * 0.2))
        return patients[:top]

    if key == "insurance_expiring":
        insured = _patients_with_insurance(patients)
        return [p for p in patients if p["patient_uuid"] in insured]

    if key == "review_request":
        out = []
        for p in patients:
            uid = p["patient_uuid"]
            for a in by_patient.get(uid, []):
                d = _appt_date(a)
                if d and d < today:
                    out.append(p)
                    break
        return out

    if key == "referral_request":
        out = []
        for p in patients:
            uid = p["patient_uuid"]
            if len(by_patient.get(uid, [])) >= 2:
                out.append(p)
        return out

    return []


def list_segments() -> list:
    """Metadata for every segment across all categories.

    Each entry: {key, label, category, description, patient_count, sample}.
    """
    out = []
    for seg in _SEGMENTS:
        try:
            members = segment_patients(seg["key"])
        except Exception:
            members = []
        out.append(
            {
                "key": seg["key"],
                "label": seg["label"],
                "category": seg["category"],
                "description": seg["description"],
                "patient_count": len(members),
                "sample": [m.get("name") for m in members[:4] if m.get("name")],
            }
        )
    return out


def get_segment_meta(key: str) -> Optional[dict]:
    return _SEGMENTS_BY_KEY.get(key)


# ---------------------------------------------------------------------------
# Run history
# ---------------------------------------------------------------------------
def record_campaign_run(
    segment_key: str, label: str, category: str, count: int
) -> dict:
    """Persist a single campaign run and return it."""
    r = get_redis()
    run_id = str(uuid.uuid4())
    created_at = _now()
    r.hset(
        f"campaign_run:{run_id}",
        mapping={
            "run_id": run_id,
            "segment": segment_key,
            "label": label or "",
            "category": category or "",
            "count": str(count),
            "created_at": created_at,
        },
    )
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
        "label": data.get("label") or "",
        "category": data.get("category") or "",
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
