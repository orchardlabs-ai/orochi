from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..agent.graph import run_inbound, run_reminders
from ..deps import current_user

router = APIRouter(prefix="/simulate", tags=["simulator"])


class InboundRequest(BaseModel):
    phone: str
    name: str
    message: Optional[str] = None


@router.post("/inbound")
def simulate_inbound(body: InboundRequest, user=Depends(current_user)):
    return run_inbound(phone=body.phone, name=body.name, message=body.message or "")


@router.post("/reminders")
def simulate_reminders(user=Depends(current_user)):
    return run_reminders()
