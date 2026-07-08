"""Configurable reminder cadence + outbound reminder jobs (DEMO)."""

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import store_reminders
from ..db import get_patient
from ..deps import current_user
from ..integrations.twilio_mock import send_sms
from ..store_comms import log_communication

router = APIRouter(prefix="/reminders", tags=["reminders"])


class CadenceUpdate(BaseModel):
    cadence: List[str]


@router.get("/config")
def get_config(user=Depends(current_user)):
    return store_reminders.get_config()


@router.post("/config")
def set_config(body: CadenceUpdate, user=Depends(current_user)):
    return store_reminders.set_config(body.cadence)


@router.get("/due")
def due(user=Depends(current_user)):
    """Preview the computed due reminder jobs."""
    return store_reminders.compute_due_jobs()


@router.post("/run")
def run(user=Depends(current_user)):
    """Send a mock SMS for every due job, log each communication, record a run."""
    jobs = store_reminders.compute_due_jobs()
    sent_jobs = []
    for job in jobs:
        patient = get_patient(job.get("patient_uuid")) if job.get("patient_uuid") else None
        phone = patient["phone"] if patient else "unknown"
        name = job.get("patient_name") or (patient["name"] if patient else "there")
        when = job.get("appointment_datetime") or "your upcoming visit"
        body = (
            f"Hi {name}, this is a reminder ({job.get('cadence_label')}) "
            f"for your appointment on {when}. Reply CONFIRM or CANCEL."
        )
        result = send_sms(phone, body)
        log_communication(
            patient_uuid=job.get("patient_uuid") or "",
            channel="sms",
            direction="outbound",
            body=body,
            status=result.get("status", "sent"),
            meta={
                "kind": "reminder",
                "cadence": job.get("cadence"),
                "appointment_id": job.get("appointment_id"),
                "sid": result.get("sid"),
            },
        )
        sent_job = {**job, "status": "sent", "sid": result.get("sid")}
        sent_jobs.append(sent_job)
    store_reminders.log_run(sent_jobs)
    return {"sent": len(sent_jobs), "jobs": sent_jobs}


@router.get("/history")
def history(user=Depends(current_user)):
    return store_reminders.list_runs()
