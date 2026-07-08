from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from ..deps import current_user

router = APIRouter(prefix="/patients", tags=["patients"])


class PatientCreate(BaseModel):
    name: str
    phone: str


@router.get("")
def list_patients(user=Depends(current_user)):
    return db.list_patients()


@router.post("")
def create_patient(body: PatientCreate, user=Depends(current_user)):
    return db.create_patient(body.name, body.phone)


@router.get("/{patient_uuid}")
def get_patient(patient_uuid: str, user=Depends(current_user)):
    patient = db.get_patient(patient_uuid)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )
    patient["appointments"] = db.list_appointments_for_patient(patient_uuid)
    return patient


@router.get("/{patient_uuid}/context")
def patient_context(patient_uuid: str, user=Depends(current_user)):
    """Call-pop timeline: patient + their appointments, calls, communications."""
    from .. import store_comms

    patient = db.get_patient(patient_uuid)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    appointments = db.list_appointments_for_patient(patient_uuid)
    calls = [c for c in db.list_calls() if c.get("patient_uuid") == patient_uuid]
    communications = [
        c
        for c in store_comms.list_communications()
        if c.get("patient_uuid") == patient_uuid
    ]

    return {
        "patient": patient,
        "appointments": appointments,
        "calls": calls,
        "communications": communications,
    }
