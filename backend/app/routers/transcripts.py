"""Transcripts demo feature: batch call-judgment listing, detail, and
aggregate overview. Judgments are precomputed/mocked at seed time (see
app/seed_transcripts.py) — this router is read-only over app/db.py."""

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..deps import current_user

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


def _empty_judgment() -> dict:
    return {
        "receptionist_coaching": [],
        "business_owner_insights": [],
        "compliance_flags": [],
        "quality_score": None,
        "booked": False,
    }


@router.get("/overview")
def overview(user=Depends(current_user)):
    """Batch aggregation over all analyzed calls. Registered before
    /{call_uuid} so 'overview' isn't captured as a path param."""
    calls = db.list_calls()
    judged = [c for c in calls if c.get("judgment")]

    total_analyzed = len(judged)
    flagged = [c for c in judged if c["judgment"].get("compliance_flags")]
    scores = [
        c["judgment"]["quality_score"]
        for c in judged
        if isinstance(c["judgment"].get("quality_score"), (int, float))
    ]
    avg_quality_score = round(sum(scores) / len(scores), 2) if scores else None

    insight_counter = Counter()
    coaching_counter = Counter()
    for c in judged:
        for insight in c["judgment"].get("business_owner_insights") or []:
            insight_counter[insight] += 1
        for note in c["judgment"].get("receptionist_coaching") or []:
            coaching_counter[note] += 1

    return {
        "total_calls_analyzed": total_analyzed,
        "compliance_flagged_count": len(flagged),
        "average_quality_score": avg_quality_score,
        "top_business_owner_insights": [
            {"theme": theme, "count": count}
            for theme, count in insight_counter.most_common(5)
        ],
        "top_coaching_themes": [
            {"theme": theme, "count": count}
            for theme, count in coaching_counter.most_common(5)
        ],
    }


@router.get("")
def list_transcripts(user=Depends(current_user)):
    calls = db.list_calls()
    out = []
    for c in calls:
        judgment = c.get("judgment") or _empty_judgment()
        out.append(
            {
                "call_uuid": c["call_uuid"],
                "started_at": c["started_at"],
                "patient_name": c.get("patient_name"),
                "direction": c["direction"],
                "quality_score": judgment.get("quality_score"),
                "has_compliance_flags": bool(judgment.get("compliance_flags")),
                "booked": bool(judgment.get("booked")),
            }
        )
    return out


@router.get("/{call_uuid}")
def get_transcript(call_uuid: str, user=Depends(current_user)):
    call = db.get_call(call_uuid)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    patient = db.get_patient(call["patient_uuid"]) if call["patient_uuid"] else None
    return {
        "call_uuid": call["call_uuid"],
        "patient_uuid": call["patient_uuid"],
        "patient_name": patient["name"] if patient else None,
        "direction": call["direction"],
        "status": call["status"],
        "started_at": call["started_at"],
        "ended_at": call["ended_at"],
        "transcript": call["transcript"],
        "judgment": call.get("judgment") or _empty_judgment(),
    }
