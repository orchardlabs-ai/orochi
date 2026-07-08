from fastapi import APIRouter, Depends, HTTPException, status

from .. import store_escalations
from ..deps import current_user

router = APIRouter(prefix="/escalations", tags=["escalations"])


@router.get("")
def list_escalations(user=Depends(current_user)):
    return store_escalations.list_escalations()


@router.get("/open-count")
def open_count(user=Depends(current_user)):
    return {"count": store_escalations.open_count()}


@router.post("/{escalation_id}/resolve")
def resolve_escalation(escalation_id: str, user=Depends(current_user)):
    updated = store_escalations.resolve(escalation_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found"
        )
    return updated
