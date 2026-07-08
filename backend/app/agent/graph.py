"""LangGraph wiring for the Orochi clinic voice agent.

Two flows share one graph, routed by ``state["intent"]`` via
``add_conditional_edges`` (per the contract — NOT set_router):

    intent == "create_appointment":
        entry -> identify_patient -> collect_appointment_details -> END
    intent == "reminder_flow":
        entry -> reminder_script -> END

Node functions call storage helpers from ``app.db`` and the LLM via
``app.agent.llm.kimi_chat``.

STORAGE ASSUMPTIONS (documented for backend-core):
    The nodes rely on the following helper names in ``app.db``. If backend-core
    named them differently, add thin aliases there:

        create_or_get_patient(phone, name)  -> patient dict incl. "patient_uuid"
        create_appointment(patient_uuid, datetime, location) -> appointment dict incl. "appointment_id"
        list_upcoming_appointments() -> list of appointment dicts (each with
            "appointment_id", "patient_uuid", "datetime", "location",
            and optionally "patient_name"/"phone")
        create_call(patient_uuid, direction, status, ...) -> call dict incl. "call_uuid"
        update_call(call_uuid, **fields) -> updated call dict
        get_patient(patient_uuid) -> patient dict  (optional; used to enrich reminders)

    All db helpers are imported lazily inside the nodes so this module imports
    cleanly even before backend-core finishes app.db.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from langgraph.graph import StateGraph, END

from .state import CallState
from .llm import kimi_chat, parse_appointment_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _combine_datetime(date: str, time: str) -> str:
    """Combine a date + time into an ISO-ish datetime string.

    ``date`` may be a literal like "next available"; in that case we keep it
    human-readable rather than fabricating a timestamp.
    """
    if not date or date == "next available":
        return f"next available {time}".strip()
    return f"{date}T{time}" if time else date


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def identify_patient(state: CallState) -> CallState:
    """Resolve (or create) the patient record for the caller."""
    from app import db  # lazy import — backend-core owns app.db

    actions = list(state.get("actions", []))
    transcript = list(state.get("transcript", []))

    phone = state.get("caller_phone", "")
    name = state.get("patient_name") or "Unknown Caller"

    patient = db.create_or_get_patient(phone, name)
    patient_uuid = patient.get("patient_uuid") or patient.get("uuid") or patient.get("id")

    actions.append(f"Identified patient {name} ({phone}) -> {patient_uuid}")
    transcript.append({
        "role": "agent",
        "text": f"Thanks {name}, I've pulled up your record.",
    })

    return {
        **state,
        "patient_uuid": patient_uuid,
        "patient_name": patient.get("name", name),
        "actions": actions,
        "transcript": transcript,
    }


def collect_appointment_details(state: CallState) -> CallState:
    """Ask the LLM to extract {date,time,location} then persist an appointment."""
    from app import db  # lazy import

    actions = list(state.get("actions", []))
    transcript = list(state.get("transcript", []))
    message = state.get("message", "")

    system = (
        "You are a clinic scheduling assistant. Extract the requested "
        "appointment date, time and clinic location from the caller's message. "
        "Respond ONLY with a JSON object with keys \"date\" (YYYY-MM-DD or "
        "'next available'), \"time\" (HH:MM 24h) and \"location\"."
    )
    llm_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]
    raw = kimi_chat(llm_messages)
    details = parse_appointment_json(raw)

    date = details.get("date", "next available")
    time = details.get("time", "09:00")
    location = details.get("location", "Main Clinic")
    appt_dt = _combine_datetime(date, time)

    transcript.append({"role": "caller", "text": message})
    actions.append(f"LLM extracted appointment details: {json.dumps(details)}")

    appointment = db.create_appointment(
        state.get("patient_uuid"), appt_dt, location
    )
    appointment_id = (
        appointment.get("appointment_id")
        or appointment.get("id")
        or appointment.get("uuid")
    )

    actions.append(
        f"Created appointment {appointment_id} for {appt_dt} at {location}"
    )
    transcript.append({
        "role": "agent",
        "text": f"You're booked for {appt_dt} at {location}. See you then!",
    })

    return {
        **state,
        "appointment_id": appointment_id,
        "actions": actions,
        "transcript": transcript,
    }


def reminder_script(state: CallState) -> CallState:
    """Produce a spoken reminder script for a single appointment."""
    actions = list(state.get("actions", []))
    transcript = list(state.get("transcript", []))

    name = state.get("patient_name") or "there"
    appt_dt = state.get("message", "your upcoming appointment")

    script = (
        f"Hello {name}, this is Orochi Clinic calling with a friendly reminder "
        f"about your appointment on {appt_dt}. Please reply or call us back to "
        f"confirm or reschedule."
    )

    actions.append(f"Generated reminder script for {name}")
    transcript.append({"role": "agent", "text": script})

    return {
        **state,
        "actions": actions,
        "transcript": transcript,
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_intent(state: CallState) -> str:
    """Conditional-edge selector from the virtual entry router."""
    if state.get("intent") == "reminder_flow":
        return "reminder_flow"
    return "create_appointment"


def _entry(state: CallState) -> CallState:
    """No-op entry node; exists so add_conditional_edges has a source."""
    return state


def build_graph():
    """Construct and compile the Orochi LangGraph."""
    graph = StateGraph(CallState)

    graph.add_node("entry", _entry)
    graph.add_node("identify_patient", identify_patient)
    graph.add_node("collect_appointment_details", collect_appointment_details)
    graph.add_node("reminder_script", reminder_script)

    graph.set_entry_point("entry")

    # Contract: use add_conditional_edges (NOT set_router) for routing.
    graph.add_conditional_edges(
        "entry",
        _route_intent,
        {
            "create_appointment": "identify_patient",
            "reminder_flow": "reminder_script",
        },
    )

    # create_appointment: identify -> collect -> END
    graph.add_edge("identify_patient", "collect_appointment_details")
    graph.add_edge("collect_appointment_details", END)

    # reminder_flow: reminder_script -> END
    graph.add_edge("reminder_script", END)

    return graph.compile()


# Compile once at import so callers reuse a single graph instance.
_COMPILED_GRAPH = None


def _get_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_graph()
    return _COMPILED_GRAPH


# ---------------------------------------------------------------------------
# High-level entrypoints used by the FastAPI simulate routes
# ---------------------------------------------------------------------------

def run_inbound(phone: str, name: str, message: Optional[str] = None) -> dict:
    """Run the inbound scheduling flow for a simulated call.

    Creates a call record, drives the create_appointment path through the graph,
    finalizes the call with the accumulated transcript, and returns:

        {"call": {...}, "actions": [...], "appointment": {...}|None}
    """
    from app import db  # lazy import

    message = message or "I'd like to book an appointment at the next available time."

    call = db.create_call(
        patient_uuid=None,
        direction="inbound",
        status="in_progress",
    )
    call_uuid = call.get("call_uuid") or call.get("uuid") or call.get("id")

    init: CallState = {
        "call_uuid": call_uuid,
        "caller_phone": phone,
        "patient_name": name,
        "intent": "create_appointment",
        "message": message,
        "actions": [f"Inbound call started from {phone}"],
        "transcript": [{"role": "caller", "text": message}],
    }

    final = _get_graph().invoke(init)

    updated_call = db.update_call(
        call_uuid,
        patient_uuid=final.get("patient_uuid"),
        status="completed",
        ended=True,
        transcript=final.get("transcript", []),
    )

    appointment = None
    appt_id = final.get("appointment_id")
    if appt_id:
        appointment = {
            "appointment_id": appt_id,
            "patient_uuid": final.get("patient_uuid"),
        }
        # Enrich from storage if a getter is available.
        getter = getattr(db, "get_appointment", None)
        if callable(getter):
            try:
                appointment = getter(appt_id) or appointment
            except Exception:
                pass

    return {
        "call": updated_call or {"call_uuid": call_uuid},
        "actions": final.get("actions", []),
        "appointment": appointment,
    }


def run_reminders() -> dict:
    """Run the reminder batch over all upcoming appointments.

    For each upcoming appointment: creates an outbound call, runs the
    reminder_flow path, records the script in the call transcript, and returns:

        {"results": [{"appointment_id", "script", "call_uuid"}, ...]}
    """
    from app import db  # lazy import

    upcoming = db.list_upcoming_appointments() or []
    results = []

    for appt in upcoming:
        appt_id = (
            appt.get("appointment_id") or appt.get("id") or appt.get("uuid")
        )
        patient_uuid = appt.get("patient_uuid")
        appt_dt = appt.get("datetime", "your upcoming appointment")

        # Resolve patient name for a friendlier script.
        name = appt.get("patient_name")
        if not name and patient_uuid:
            getter = getattr(db, "get_patient", None)
            if callable(getter):
                try:
                    p = getter(patient_uuid) or {}
                    name = p.get("name")
                except Exception:
                    name = None
        name = name or "there"

        call = db.create_call(
            patient_uuid=patient_uuid,
            direction="outbound",
            status="in_progress",
        )
        call_uuid = call.get("call_uuid") or call.get("uuid") or call.get("id")

        init: CallState = {
            "call_uuid": call_uuid,
            "patient_uuid": patient_uuid,
            "patient_name": name,
            "appointment_id": appt_id,
            "intent": "reminder_flow",
            "message": appt_dt,
            "actions": [f"Reminder call queued for appointment {appt_id}"],
            "transcript": [],
        }

        final = _get_graph().invoke(init)

        transcript = final.get("transcript", [])
        script = transcript[-1]["text"] if transcript else ""

        db.update_call(
            call_uuid,
            status="completed",
            ended=True,
            transcript=transcript,
        )

        results.append({
            "appointment_id": appt_id,
            "script": script,
            "call_uuid": call_uuid,
        })

    return {"results": results}
