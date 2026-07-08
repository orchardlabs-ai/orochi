from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from ..config import settings
from ..deps import current_user
from ..scheduling import WEEKDAYS, slot_times

router = APIRouter(prefix="/schedule", tags=["schedule"])


class SlotUpdate(BaseModel):
    weekday: str
    time: str
    available: bool


class DayUpdate(BaseModel):
    weekday: str
    available: bool


def _schedule_payload() -> dict:
    return {
        "open": settings.CLINIC_OPEN,
        "close": settings.CLINIC_CLOSE,
        "slot_minutes": settings.SLOT_MINUTES,
        "weekdays": WEEKDAYS,
        "slots": slot_times(),
        "availability": db.get_availability(),
    }


@router.get("")
def get_schedule(user=Depends(current_user)):
    return _schedule_payload()


@router.post("/slot")
def set_slot(body: SlotUpdate, user=Depends(current_user)):
    if body.weekday not in WEEKDAYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid weekday")
    if body.time not in slot_times():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid slot time")
    availability = db.set_slot_availability(body.weekday, body.time, body.available)
    return {**_schedule_payload(), "availability": availability}


@router.post("/day")
def set_day(body: DayUpdate, user=Depends(current_user)):
    if body.weekday not in WEEKDAYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid weekday")
    availability = db.set_day_availability(body.weekday, body.available)
    return {**_schedule_payload(), "availability": availability}
