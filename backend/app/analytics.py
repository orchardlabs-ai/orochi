"""Read-only analytics aggregation over existing calls, appointments, and
patients. No writes; purely derived views for the Insights dashboard."""

from datetime import datetime, timezone

from .db import (
    list_appointments,
    list_calls,
    list_appointments_for_patient,
)

SENTIMENTS = ["positive", "neutral", "negative"]


def _call_sentiment(call: dict) -> str:
    """Read a call's sentiment if present, else default to 'neutral'."""
    val = (call.get("sentiment") or "neutral").lower()
    return val if val in SENTIMENTS else "neutral"


def overview() -> dict:
    calls = list_calls()
    appointments = list_appointments()

    inbound = sum(1 for c in calls if c.get("direction") == "inbound")
    outbound = sum(1 for c in calls if c.get("direction") == "outbound")

    # Booking conversion: appointments created via inbound calls / inbound calls.
    # We approximate "booked via inbound" as appointments belonging to a patient
    # who has at least one inbound call. Deterministic and offline-friendly.
    inbound_patients = {
        c.get("patient_uuid")
        for c in calls
        if c.get("direction") == "inbound" and c.get("patient_uuid")
    }
    booked_via_inbound = sum(
        1
        for a in appointments
        if a.get("patient_uuid") in inbound_patients
    )
    booking_conversion = round(booked_via_inbound / inbound, 4) if inbound else 0.0
    booking_conversion = max(0.0, min(1.0, booking_conversion))

    by_status = {"scheduled": 0, "confirmed": 0, "cancelled": 0}
    for a in appointments:
        st = a.get("status")
        if st in by_status:
            by_status[st] += 1

    sentiment_distribution = {s: 0 for s in SENTIMENTS}
    for c in calls:
        sentiment_distribution[_call_sentiment(c)] += 1

    return {
        "total_calls": len(calls),
        "inbound": inbound,
        "outbound": outbound,
        "total_appointments": len(appointments),
        "booking_conversion": booking_conversion,
        "by_status": by_status,
        "sentiment_distribution": sentiment_distribution,
    }


def _lead_time_days(datetime_str: str) -> float:
    """Days from now until the appointment datetime. Negative if in the past."""
    if not datetime_str:
        return 0.0
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return 0.0
    now = datetime.utcnow()
    return (dt - now).total_seconds() / 86400.0


def _band(risk: float) -> str:
    if risk >= 0.66:
        return "high"
    if risk >= 0.33:
        return "medium"
    return "low"


def no_show_risk() -> list:
    """Heuristic no-show risk per active (non-cancelled) appointment."""
    appointments = list_appointments()
    results = []

    for appt in appointments:
        status = appt.get("status")
        if status == "cancelled":
            continue

        risk = 0.25  # base

        # Not yet confirmed -> higher risk; confirmed -> lower.
        if status == "scheduled":
            risk += 0.30
        elif status == "confirmed":
            risk -= 0.15

        # Prior cancelled appointment for this patient -> higher risk.
        patient_uuid = appt.get("patient_uuid")
        if patient_uuid:
            prior = list_appointments_for_patient(patient_uuid)
            if any(
                p.get("appointment_id") != appt.get("appointment_id")
                and p.get("status") == "cancelled"
                for p in prior
            ):
                risk += 0.25

        # Far-future lead time -> higher risk (more time to forget/change plans).
        lead = _lead_time_days(appt.get("datetime", ""))
        if lead > 14:
            risk += 0.20
        elif lead > 7:
            risk += 0.10
        elif lead < 0:
            risk += 0.05  # overdue / stale

        risk = round(max(0.0, min(1.0, risk)), 3)

        results.append(
            {
                "appointment_id": appt.get("appointment_id"),
                "patient_name": appt.get("patient_name"),
                "datetime": appt.get("datetime"),
                "status": status,
                "risk": risk,
                "band": _band(risk),
            }
        )

    results.sort(key=lambda r: r["risk"], reverse=True)
    return results
