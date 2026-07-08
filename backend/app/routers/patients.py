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
