"""Outbound campaigns: recall / reactivation / missed-call recovery.

Segments are computed read-only from existing patient / appointment / call data.
Running a campaign mocks an outbound touch (SMS) per patient via the shared
Twilio mock, logs it through the shared comms log, and records the run.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from ..deps import current_user
from ..integrations.twilio_mock import send_sms
from ..store_comms import log_communication
from ..store_campaigns import list_campaign_runs, record_campaign_run

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

_ACTIVE_STATUSES = {"scheduled", "confirmed"}

_SEGMENT_LABELS = {
    "recare": "Recare recall",
    "reactivation": "Reactivation",
    "missed_call_recovery": "Missed-call recovery",
}
_SEGMENT_DESCRIPTIONS = {
    "recare": "Patients with no active upcoming appointment — due for a recall.",
    "reactivation": "Lapsed patients (oldest third by record age) to win back.",
    "missed_call_recovery": "Patients who called in but never booked an appointment.",
}
_SEGMENT_MESSAGES = {
    "recare": (
        "Hi {name}, it's your clinic — you're due for a check-up. "
        "Reply or call us to book a convenient time."
    ),
    "reactivation": (
        "Hi {name}, we miss seeing you at the clinic! "
        "Reply to reactivate your care and schedule a visit."
    ),
    "missed_call_recovery": (
        "Hi {name}, we saw you reached out recently. "
        "We'd love to help — reply to finish booking your appointment."
    ),
}


def _patients_with_active_appointment() -> set:
    """Set of patient_uuids that have at least one active upcoming appointment."""
    active = set()
    for appt in db.list_appointments():
        if appt.get("status") in _ACTIVE_STATUSES and appt.get("patient_uuid"):
            active.add(appt["patient_uuid"])
    return active


def _compute_segment(segment: str) -> list:
    """Return the list of patient dicts belonging to a segment."""
    patients = db.list_patients()

    if segment == "recare":
        active = _patients_with_active_appointment()
        return [p for p in patients if p["patient_uuid"] not in active]

    if segment == "reactivation":
        # Oldest third by created_at are treated as lapsed for the demo.
        by_age = sorted(patients, key=lambda p: p.get("created_at", ""))
        third = max(1, len(by_age) // 3) if by_age else 0
        return by_age[:third]

    if segment == "missed_call_recovery":
        active = _patients_with_active_appointment()
        # Patients who have an inbound call but no active appointment.
        inbound_patients = {}
        for call in db.list_calls():
            if call.get("direction") == "inbound" and call.get("patient_uuid"):
                inbound_patients[call["patient_uuid"]] = True
        result = []
        seen = set()
        for p in patients:
            uid = p["patient_uuid"]
            if uid in inbound_patients and uid not in active and uid not in seen:
                seen.add(uid)
                result.append(p)
        return result

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown segment: {segment}"
    )


class CampaignRun(BaseModel):
    segment: str


@router.get("/segments")
def get_segments(user=Depends(current_user)):
    out = []
    for key in ("recare", "reactivation", "missed_call_recovery"):
        members = _compute_segment(key)
        out.append(
            {
                "key": key,
                "label": _SEGMENT_LABELS[key],
                "description": _SEGMENT_DESCRIPTIONS[key],
                "patient_count": len(members),
                "sample": [m["name"] for m in members[:5]],
            }
        )
    return out


@router.post("/run")
def run_campaign(body: CampaignRun, user=Depends(current_user)):
    segment = body.segment
    if segment not in _SEGMENT_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown segment: {segment}",
        )
    members = _compute_segment(segment)
    template = _SEGMENT_MESSAGES[segment]

    communications = []
    for p in members:
        name = p.get("name") or "there"
        phone = p.get("phone") or ""
        body_text = template.format(name=name)
        result = send_sms(to=phone, body=body_text)
        comm = log_communication(
            patient_uuid=p["patient_uuid"],
            channel="sms",
            direction="outbound",
            body=body_text,
            status=result.get("status", "sent"),
            meta={"campaign": segment, "sid": result.get("sid")},
        )
        communications.append(comm)

    run = record_campaign_run(segment, len(communications))
    return {
        "segment": segment,
        "contacted": len(communications),
        "run": run,
        "communications": communications,
    }


@router.get("/history")
def get_history(user=Depends(current_user)):
    return list_campaign_runs()
