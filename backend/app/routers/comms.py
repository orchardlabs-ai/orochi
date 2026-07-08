from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from ..deps import current_user
from ..integrations import twilio_mock
from ..store_comms import log_communication, list_communications

router = APIRouter(prefix="/comms", tags=["comms"])

VALID_CHANNELS = {"sms", "email", "voice"}


class SendMessage(BaseModel):
    patient_uuid: str
    channel: str
    body: str


class ConfirmReply(BaseModel):
    appointment_id: str
    action: str


@router.get("")
def list_comms(user=Depends(current_user)):
    return list_communications()


@router.post("/send")
def send_message(body: SendMessage, user=Depends(current_user)):
    if body.channel not in VALID_CHANNELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"channel must be one of {sorted(VALID_CHANNELS)}",
        )
    patient = db.get_patient(body.patient_uuid)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )
    to = patient.get("phone") or ""

    if body.channel == "sms":
        result = twilio_mock.send_sms(to, body.body)
    elif body.channel == "email":
        result = twilio_mock.send_email(to, "A message from your clinic", body.body)
    else:  # voice
        result = twilio_mock.place_call(to, body.body)

    record = log_communication(
        patient_uuid=body.patient_uuid,
        channel=body.channel,
        direction="outbound",
        body=body.body,
        status=result.get("status", "sent"),
        meta={"sid": result.get("sid"), "to": to},
    )
    return record


@router.post("/confirm")
def confirm_reply(body: ConfirmReply, user=Depends(current_user)):
    """Simulate a patient replying to an appointment reminder."""
    if body.action not in ("confirm", "cancel"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action must be 'confirm' or 'cancel'",
        )
    new_status = "confirmed" if body.action == "confirm" else "cancelled"
    appt = db.update_appointment_status(body.appointment_id, new_status)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )
    patient = db.get_patient(appt["patient_uuid"])
    appt["patient_name"] = patient["name"] if patient else None

    reply_text = "YES" if body.action == "confirm" else "CANCEL"
    comm = log_communication(
        patient_uuid=appt["patient_uuid"],
        channel="sms",
        direction="inbound",
        body=reply_text,
        status="received",
        meta={"appointment_id": body.appointment_id, "action": body.action},
    )
    return {"appointment": appt, "communication": comm}
