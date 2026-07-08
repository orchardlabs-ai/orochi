from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import store_catalog
from ..deps import current_user

router = APIRouter(prefix="/catalog", tags=["catalog"])


class ProviderCreate(BaseModel):
    name: str
    specialty: str = ""
    color: str = "#0e8f6a"


class ProcedureCreate(BaseModel):
    name: str
    duration_minutes: int = 45
    color: str = "#0e8f6a"


@router.get("/providers")
def get_providers(user=Depends(current_user)):
    store_catalog.ensure_seeded()
    return store_catalog.list_providers()


@router.post("/providers")
def post_provider(body: ProviderCreate, user=Depends(current_user)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Name is required")
    return store_catalog.create_provider(name, body.specialty, body.color)


@router.get("/procedures")
def get_procedures(user=Depends(current_user)):
    store_catalog.ensure_seeded()
    return store_catalog.list_procedures()


@router.post("/procedures")
def post_procedure(body: ProcedureCreate, user=Depends(current_user)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Name is required")
    if body.duration_minutes <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Duration must be positive"
        )
    return store_catalog.create_procedure(name, body.duration_minutes, body.color)
