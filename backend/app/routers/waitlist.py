from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from ..deps import current_user
from ..scheduling import next_available_slot
from ..store_waitlist import add_to_waitlist, list_waitlist, remove_from_waitlist
from ..store_comms import log_communication
from ..integrations.twilio_mock import send_sms

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


class WaitlistCreate(BaseModel):
    patient_uuid: str
    note: Optional[str] = ""


@router.get("")
def get_waitlist(user=Depends(current_user)):
    return list_waitlist()


@router.post("")
def create_waitlist_entry(body: WaitlistCreate, user=Depends(current_user)):
    patient = db.get_patient(body.patient_uuid)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )
    return add_to_waitlist(body.patient_uuid, body.note or "")


@router.delete("/{entry_id}")
def delete_waitlist_entry(entry_id: str, user=Depends(current_user)):
    removed = remove_from_waitlist(entry_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found"
        )
    return {"removed": True, "entry_id": entry_id}


@router.post("/backfill")
def backfill(user=Depends(current_user)):
    """Book the earliest waitlisted patient into the next open, unbooked slot."""
    entries = list_waitlist()
    if not entries:
        return {"filled": False, "message": "The waitlist is empty."}

    slot = next_available_slot("next available", None)
    if not slot:
        return {
            "filled": False,
            "message": "No open availability slot to backfill.",
        }

    date_str, time_str = slot
    datetime_str = f"{date_str}T{time_str}"

    entry = entries[0]
    patient = db.get_patient(entry["patient_uuid"])
    if not patient:
        # Stale entry pointing at a missing patient; drop it.
        remove_from_waitlist(entry["entry_id"])
        return {
            "filled": False,
            "message": "The next waitlisted patient no longer exists; entry removed.",
        }

    appointment = db.create_appointment(
        patient["patient_uuid"], datetime_str, "Main Clinic"
    )
    remove_from_waitlist(entry["entry_id"])

    body = (
        f"Hi {patient['name']}, good news! A slot opened up and we've booked you "
        f"in at Main Clinic on {date_str} at {time_str}. Reply to reschedule."
    )
    sms = send_sms(patient.get("phone") or "", body)
    log_communication(
        patient["patient_uuid"],
        channel="sms",
        direction="outbound",
        body=body,
        status=sms.get("status", "sent"),
        meta={"kind": "waitlist_backfill", "appointment_id": appointment["appointment_id"]},
    )

    return {
        "filled": True,
        "appointment": appointment,
        "patient": patient,
        "message": (
            f"{patient['name']} booked into {date_str} at {time_str} and notified by SMS."
        ),
    }
