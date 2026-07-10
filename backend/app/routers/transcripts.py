"""Transcripts demo feature: batch call-judgment listing, detail, and
aggregate overview. Judgments are precomputed/mocked at seed time (see
app/seed_transcripts.py) — this router is read-only over app/db.py."""

import time
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..deps import current_user
from ..agent import nlu

router = APIRouter(prefix="/transcripts", tags=["transcripts"])

_SENTIMENT_SCORE = {"positive": 4, "neutral": 3, "negative": 2}

_WEEK_SECONDS = 7 * 24 * 60 * 60


def _empty_judgment() -> dict:
    return {
        "receptionist_coaching": [],
        "business_owner_insights": [],
        "compliance_flags": [],
        "quality_score": None,
        "booked": False,
    }


def _unanalyzed_judgment(call: dict) -> dict:
    """Lightweight real signal for calls with no stored judgment (e.g. live
    calls from the Simulator): derive a rough quality proxy from sentiment
    and include a summary, but keep coaching/insights/flags empty since
    those genuinely haven't been produced yet."""
    transcript = call.get("transcript") or []
    sent = nlu.sentiment(transcript)
    return {
        "receptionist_coaching": [],
        "business_owner_insights": [],
        "compliance_flags": [],
        "quality_score": _SENTIMENT_SCORE.get(sent, 3),
        "booked": False,
        "summary": nlu.summary(transcript),
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

    def _bucket(lo: float, hi: float) -> dict:
        """Calls with started_at in (now-hi, now-lo], i.e. lo..hi days ago."""
        bucket_calls = []
        for c in judged:
            try:
                started = float(c.get("started_at") or 0)
            except (TypeError, ValueError):
                continue
            age = now - started
            if lo <= age < hi:
                bucket_calls.append(c)
        bucket_scores = [
            c["judgment"]["quality_score"]
            for c in bucket_calls
            if isinstance(c["judgment"].get("quality_score"), (int, float))
        ]
        return {
            "count": len(bucket_calls),
            "average_quality_score": (
                round(sum(bucket_scores) / len(bucket_scores), 2)
                if bucket_scores
                else None
            ),
        }

    now = time.time()
    this_week = _bucket(0, _WEEK_SECONDS)
    prior_week = _bucket(_WEEK_SECONDS, 2 * _WEEK_SECONDS)

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
        "this_week": this_week,
        "prior_week": prior_week,
    }


@router.get("")
def list_transcripts(user=Depends(current_user)):
    calls = db.list_calls()
    out = []
    for c in calls:
        analyzed = bool(c.get("judgment"))
        judgment = c.get("judgment") or _unanalyzed_judgment(c)
        out.append(
            {
                "call_uuid": c["call_uuid"],
                "started_at": c["started_at"],
                "patient_name": c.get("patient_name"),
                "direction": c["direction"],
                "analyzed": analyzed,
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
    analyzed = bool(call.get("judgment"))
    return {
        "call_uuid": call["call_uuid"],
        "patient_uuid": call["patient_uuid"],
        "patient_name": patient["name"] if patient else None,
        "direction": call["direction"],
        "status": call["status"],
        "started_at": call["started_at"],
        "ended_at": call["ended_at"],
        "transcript": call["transcript"],
        "analyzed": analyzed,
        "judgment": call.get("judgment") or _unanalyzed_judgment(call),
    }
