from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from .. import store_catalog
from ..deps import current_user
from ..scheduling import slot_times, weekday_of, procedure_slot_count

router = APIRouter(prefix="/appointments", tags=["appointments"])

VALID_STATUSES = {"scheduled", "confirmed", "cancelled"}


def _validate_block(provider_id: str, datetime_str: str, slot_count: int):
    """Ensure ``slot_count`` consecutive slots from ``datetime_str`` are open +
    unbooked for the given provider; raise 409 with a clear detail otherwise."""
    try:
        date_str, time_str = datetime_str.split("T")
        time_str = time_str[:5]
        weekday = weekday_of(date_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Datetime must be YYYY-MM-DDTHH:MM aligned to a booking slot.",
        )

    slots = slot_times()
    if time_str not in slots:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{time_str} is not a 45-minute booking slot.",
        )

    start_idx = slots.index(time_str)
    if start_idx + slot_count > len(slots):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This procedure needs {slot_count} consecutive slots, which "
                f"run past closing time when started at {time_str}."
            ),
        )

    booked = db.booked_slots_for_provider(provider_id)
    block = slots[start_idx:start_idx + slot_count]
    for bt in block:
        if not db.is_slot_available(provider_id, weekday, bt):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"The provider is not open for bookings at {bt} on {weekday}."
                ),
            )
        if f"{date_str}T{bt}" in booked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The slot at {bt} is already booked for this provider.",
            )


class AppointmentCreate(BaseModel):
    patient_uuid: str
    datetime: str
    provider_id: str
    procedure_id: str
    location: Optional[str] = "Main Clinic"


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

    provider = store_catalog.get_provider(body.provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )
    procedure = store_catalog.get_procedure(body.procedure_id)
    if not procedure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found"
        )

    duration_minutes = procedure["duration_minutes"]
    slot_count = procedure_slot_count(duration_minutes)

    _validate_block(body.provider_id, body.datetime, slot_count)

    appt = db.create_appointment(
        body.patient_uuid,
        body.datetime,
        body.location or "Main Clinic",
        provider_id=body.provider_id,
        procedure_id=body.procedure_id,
        duration_minutes=duration_minutes,
    )
    patient = db.get_patient(body.patient_uuid)
    appt["patient_name"] = patient["name"] if patient else None
    db._enrich_appointment(appt)
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
    db._enrich_appointment(appt)
    return appt
