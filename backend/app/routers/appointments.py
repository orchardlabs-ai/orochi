from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from ..deps import current_user
from ..scheduling import slot_times, weekday_of

router = APIRouter(prefix="/appointments", tags=["appointments"])

VALID_STATUSES = {"scheduled", "confirmed", "cancelled"}


def _validate_slot(datetime_str: str):
    """Ensure a staff-supplied datetime lands on an open, unbooked 45-min slot."""
    try:
        date_str, time_str = datetime_str.split("T")
        weekday = weekday_of(date_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Datetime must be YYYY-MM-DDTHH:MM aligned to a booking slot.",
        )
    if time_str not in slot_times():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{time_str} is not a 45-minute booking slot.",
        )
    if not db.is_slot_available(weekday, time_str):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The clinic is not open for bookings at {time_str} on {weekday}.",
        )
    if datetime_str in db.booked_slot_datetimes():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That slot is already booked.",
        )


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
    _validate_slot(body.datetime)
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
