from fastapi import APIRouter, Depends

from .. import db
from ..deps import current_user

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("")
def list_calls(user=Depends(current_user)):
    calls = db.list_calls()
    # Omit full transcript from list view for brevity.
    return [
        {
            "call_uuid": c["call_uuid"],
            "patient_uuid": c["patient_uuid"],
            "patient_name": c.get("patient_name"),
            "direction": c["direction"],
            "status": c["status"],
            "started_at": c["started_at"],
            "ended_at": c["ended_at"],
        }
        for c in calls
    ]
