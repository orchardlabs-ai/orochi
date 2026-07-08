from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import db
from .. import store_catalog
from ..config import settings
from ..deps import current_user
from ..scheduling import WEEKDAYS, slot_times

router = APIRouter(prefix="/schedule", tags=["schedule"])


class SlotUpdate(BaseModel):
    provider_id: str
    weekday: str
    time: str
    available: bool


class DayUpdate(BaseModel):
    provider_id: str
    weekday: str
    available: bool


def _providers() -> list:
    return [
        {"provider_id": p["provider_id"], "name": p["name"], "color": p["color"]}
        for p in store_catalog.list_providers()
    ]


def _schedule_payload() -> dict:
    providers = store_catalog.list_providers()
    availability = {
        p["provider_id"]: db.get_availability(p["provider_id"]) for p in providers
    }
    return {
        "open": settings.CLINIC_OPEN,
        "close": settings.CLINIC_CLOSE,
        "slot_minutes": settings.SLOT_MINUTES,
        "weekdays": WEEKDAYS,
        "slots": slot_times(),
        "providers": [
            {"provider_id": p["provider_id"], "name": p["name"], "color": p["color"]}
            for p in providers
        ],
        "availability": availability,
    }


def _require_provider(provider_id: str):
    if not store_catalog.get_provider(provider_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )


@router.get("")
def get_schedule(user=Depends(current_user)):
    db.ensure_provider_availability_seeded()
    return _schedule_payload()


@router.post("/slot")
def set_slot(body: SlotUpdate, user=Depends(current_user)):
    _require_provider(body.provider_id)
    if body.weekday not in WEEKDAYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid weekday")
    if body.time not in slot_times():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid slot time")
    db.set_slot_availability(body.provider_id, body.weekday, body.time, body.available)
    return _schedule_payload()


@router.post("/day")
def set_day(body: DayUpdate, user=Depends(current_user)):
    _require_provider(body.provider_id)
    if body.weekday not in WEEKDAYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid weekday")
    db.set_day_availability(body.provider_id, body.weekday, body.available)
    return _schedule_payload()
