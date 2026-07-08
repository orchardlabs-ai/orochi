from fastapi import APIRouter, Depends

from .. import analytics
from ..deps import current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def get_overview(user=Depends(current_user)):
    return analytics.overview()


@router.get("/no-show-risk")
def get_no_show_risk(user=Depends(current_user)):
    return analytics.no_show_risk()
