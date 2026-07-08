from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..agent.graph import run_inbound, run_reminders
from ..deps import current_user
from .. import store_escalations

router = APIRouter(prefix="/simulate", tags=["simulator"])


class InboundRequest(BaseModel):
    phone: str
    name: str
    message: Optional[str] = None


@router.post("/inbound")
def simulate_inbound(body: InboundRequest, user=Depends(current_user)):
    result = run_inbound(phone=body.phone, name=body.name, message=body.message or "")

    if result.get("escalated") or result.get("emergency"):
        try:
            call = result.get("call") or {}
            patient_uuid = call.get("patient_uuid")
            call_uuid = call.get("call_uuid")
            store_escalations.enqueue(
                patient_uuid=patient_uuid,
                phone=body.phone,
                reason="emergency",
                summary=result.get("summary") or "",
                call_uuid=call_uuid,
            )
        except Exception:
            pass

    return result


@router.post("/reminders")
def simulate_reminders(user=Depends(current_user)):
    return run_reminders()
