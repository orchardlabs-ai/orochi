"""Outbound campaigns: a category-tagged segment library.

Segments are computed read-only from existing patient / appointment / call /
insurance data (see store_campaigns). Running a campaign mocks a
category-appropriate outbound SMS per patient via the shared Twilio mock, logs
each touch through the shared comms log, and records the run.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..deps import current_user
from ..integrations.twilio_mock import send_sms
from ..store_comms import log_communication
from ..store_campaigns import (
    list_segments,
    segment_patients,
    get_segment_meta,
    message_for_category,
    record_campaign_run,
    list_campaign_runs,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignRun(BaseModel):
    segment: str


@router.get("/segments")
def get_segments(user=Depends(current_user)):
    return list_segments()


@router.post("/run")
def run_campaign(body: CampaignRun, user=Depends(current_user)):
    segment = body.segment
    meta = get_segment_meta(segment)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown segment: {segment}",
        )

    category = meta["category"]
    label = meta["label"]

    try:
        members = segment_patients(segment)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown segment: {segment}",
        )

    communications = []
    for p in members:
        name = p.get("name") or "there"
        phone = p.get("phone") or ""
        body_text = message_for_category(category, name)
        result = send_sms(to=phone, body=body_text)
        comm = log_communication(
            patient_uuid=p["patient_uuid"],
            channel="sms",
            direction="outbound",
            body=body_text,
            status=result.get("status", "sent"),
            meta={
                "campaign": segment,
                "category": category,
                "sid": result.get("sid"),
            },
        )
        communications.append(comm)

    record_campaign_run(segment, label, category, len(communications))
    return {
        "segment": segment,
        "category": category,
        "label": label,
        "contacted": len(communications),
        "communications": communications,
    }


@router.get("/history")
def get_history(user=Depends(current_user)):
    return list_campaign_runs()
