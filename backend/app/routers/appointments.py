from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from ..deps import current_user

router = APIRouter(prefix="/appointments", tags=["appointments"])

VALID_STATUSES = {"scheduled", "confirmed", "cancelled"}


class AppointmentCreate(BaseModel):
    patient_uuid: str
    datetime: str
    location: str


class AppointmentUpdate(BaseModel):
    status: str


@router.get("")
def list_appointments(user=Depends(current_user)):
    return db.list_appointments()


@router.post("")
def create_appointment(body: AppointmentCreate, user=Depends(current_user)):
    if not db.get_patient(body.patient_uuid):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )
    appt = db.create_appointment(body.patient_uuid, body.datetime, body.location)
    patient = db.get_patient(body.patient_uuid)
    appt["patient_name"] = patient["name"] if patient else None
    return appt


@router.patch("/{appointment_id}")
def update_appointment(
    appointment_id: str, body: AppointmentUpdate, user=Depends(current_user)
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status"
        )
    appt = db.update_appointment_status(appointment_id, body.status)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )
    patient = db.get_patient(appt["patient_uuid"])
    appt["patient_name"] = patient["name"] if patient else None
    return appt
