from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from ..deps import current_user
from ..integrations.insurance_mock import verify_eligibility
from ..store_insurance import (
    get_last_verification,
    get_patient_insurance,
    save_verification,
    set_patient_insurance,
)

router = APIRouter(prefix="/insurance", tags=["insurance"])


class InsuranceOnFile(BaseModel):
    payer: str
    member_id: str


class VerifyRequest(BaseModel):
    payer: Optional[str] = None
    member_id: Optional[str] = None


def _require_patient(patient_uuid: str) -> dict:
    patient = db.get_patient(patient_uuid)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )
    return patient


@router.get("/{patient_uuid}")
def get_insurance(patient_uuid: str, user=Depends(current_user)):
    _require_patient(patient_uuid)
    return {
        "insurance_on_file": get_patient_insurance(patient_uuid),
        "last_verification": get_last_verification(patient_uuid),
    }


@router.post("/{patient_uuid}")
def put_insurance(
    patient_uuid: str, body: InsuranceOnFile, user=Depends(current_user)
):
    _require_patient(patient_uuid)
    if not body.payer.strip() or not body.member_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payer and member_id are required.",
        )
    return set_patient_insurance(
        patient_uuid, body.payer.strip(), body.member_id.strip()
    )


@router.post("/{patient_uuid}/verify")
def verify(
    patient_uuid: str,
    body: Optional[VerifyRequest] = None,
    user=Depends(current_user),
):
    """Verify eligibility for the on-file member (or a provided override) and
    persist the result. This is the "verify during the call" action."""
    _require_patient(patient_uuid)

    on_file = get_patient_insurance(patient_uuid)
    payer = (body.payer if body and body.payer else None) or (
        on_file["payer"] if on_file else None
    )
    member_id = (body.member_id if body and body.member_id else None) or (
        on_file["member_id"] if on_file else None
    )

    if not payer or not member_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No insurance on file. Provide payer and member_id to verify.",
        )

    # If an override was provided, keep the on-file record in sync.
    if body and (body.payer or body.member_id):
        set_patient_insurance(patient_uuid, payer, member_id)

    result = verify_eligibility(member_id, payer)
    save_verification(patient_uuid, result)
    return result
