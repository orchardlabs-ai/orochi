"""LangGraph wiring for the Orochi clinic voice agent.

One graph, routed by ``state["intent"]`` via ``add_conditional_edges``:

    intent == "book":        entry -> identify_patient -> collect_appointment_details -> END
    intent == "reschedule":  entry -> identify_patient -> reschedule_appointment    -> END
    intent == "cancel":      entry -> identify_patient -> cancel_appointment        -> END
    intent in (hours,insurance,other): entry -> faq_node -> END
    intent == "emergency":   entry -> triage_emergency -> END
    intent == "reminder_flow": entry -> reminder_script -> END

Node functions call storage helpers from ``app.db``, scheduling from
``app.scheduling``, NLU from ``app.agent.nlu``, and the KB from
``app.knowledge``. All imports of app.db are lazy so this module imports cleanly.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from langgraph.graph import StateGraph, END

from .state import CallState
from .llm import kimi_chat, parse_appointment_json
from . import nlu
from .. import knowledge


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _combine_datetime(date: str, time: str) -> str:
    if not date or date == "next available":
        return f"next available {time}".strip()
    return f"{date}T{time}" if time else date


def _format_spoken(date_str: str, time_str: str) -> str:
    """Human-friendly time, e.g. "Tuesday, July 09 at 11:00 AM"."""
    try:
        dt = datetime.strptime(f"{date_str}T{time_str}", "%Y-%m-%dT%H:%M")
    except (ValueError, TypeError):
        return f"{date_str} at {time_str}"
    hour = dt.hour % 12 or 12
    meridiem = "AM" if dt.hour < 12 else "PM"
    return f"{dt.strftime('%A, %B %d')} at {hour}:{dt.minute:02d} {meridiem}"


def _format_dt_string(dt_str: str) -> str:
    """Format a stored 'YYYY-MM-DDThh:mm' datetime for speech, tolerant of junk."""
    if not dt_str:
        return "your appointment"
    if "T" in dt_str:
        date_part, _, time_part = dt_str.partition("T")
        return _format_spoken(date_part, time_part[:5])
    return dt_str


def _extract_requested(message: str) -> dict:
    """Run the LLM (or offline stub) to pull {date,time,location} from a message."""
    system = (
        "You are a clinic scheduling assistant. Extract the requested "
        "appointment date, time and clinic location from the caller's message. "
        "Respond ONLY with a JSON object with keys \"date\" (YYYY-MM-DD or "
        "'next available'), \"time\" (HH:MM 24h) and \"location\"."
    )
    raw = kimi_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": message or ""},
        ]
    )
    return parse_appointment_json(raw)


def _next_active_appointment(patient_uuid: str) -> Optional[dict]:
    """Return the caller's soonest non-cancelled appointment, or None."""
    from app import db

    appts = db.list_appointments_for_patient(patient_uuid) or []
    active = [a for a in appts if a.get("status") != "cancelled"]
    return active[0] if active else None


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def identify_patient(state: CallState) -> CallState:
    """Resolve (or create) the patient record for the caller."""
    from app import db

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
    """Extract {date,time,location}, snap to a slot, and persist an appointment."""
    from app import db
    from app import scheduling

    actions = list(state.get("actions", []))
    transcript = list(state.get("transcript", []))
    message = state.get("message", "")

    details = _extract_requested(message)
    date = details.get("date", "next available")
    time = details.get("time", "09:00")
    location = details.get("location", "Main Clinic")

    actions.append(f"LLM extracted appointment details: {json.dumps(details)}")

    slot = scheduling.next_available_slot(date, time)
    requested = _combine_datetime(date, time)

    if slot is None:
        actions.append(
            f"No available slot within the booking horizon for request "
            f"'{requested}' — nothing booked."
        )
        transcript.append({
            "role": "agent",
            "text": (
                "I'm sorry, we don't have any openings coming up. "
                "Please call back and we'll find you a time."
            ),
        })
        return {**state, "actions": actions, "transcript": transcript}

    slot_date, slot_time = slot
    appt_dt = f"{slot_date}T{slot_time}"
    if appt_dt != requested:
        actions.append(
            f"Requested '{requested}' → offered nearest available slot {appt_dt}"
        )

    appointment = db.create_appointment(state.get("patient_uuid"), appt_dt, location)
    appointment_id = (
        appointment.get("appointment_id")
        or appointment.get("id")
        or appointment.get("uuid")
    )

    spoken_when = _format_spoken(slot_date, slot_time)
    actions.append(f"Created appointment {appointment_id} for {appt_dt} at {location}")
    transcript.append({
        "role": "agent",
        "text": f"You're booked for {spoken_when} at {location}. See you then!",
    })

    return {
        **state,
        "appointment_id": appointment_id,
        "actions": actions,
        "transcript": transcript,
    }


def reschedule_appointment(state: CallState) -> CallState:
    """Move the caller's next active appointment to the newly requested time."""
    from app import db
    from app import scheduling

    actions = list(state.get("actions", []))
    transcript = list(state.get("transcript", []))
    message = state.get("message", "")

    appt = _next_active_appointment(state.get("patient_uuid"))
    if not appt:
        actions.append("No active appointment found to reschedule.")
        transcript.append({
            "role": "agent",
            "text": (
                "I don't see an upcoming appointment on your record to move. "
                "Would you like to book a new one?"
            ),
        })
        return {**state, "actions": actions, "transcript": transcript}

    appt_id = appt["appointment_id"]
    old_dt = appt.get("datetime", "")
    location = appt.get("location", "Main Clinic")

    details = _extract_requested(message)
    date = details.get("date", "next available")
    time = details.get("time", "09:00")
    actions.append(f"Reschedule request parsed: {json.dumps(details)}")

    slot = scheduling.next_available_slot(date, time)
    if slot is None:
        actions.append("No available slot found for the requested new time.")
        transcript.append({
            "role": "agent",
            "text": (
                "I'm sorry, I couldn't find an opening near that time. "
                "Please call back and we'll keep looking."
            ),
        })
        return {**state, "actions": actions, "transcript": transcript}

    slot_date, slot_time = slot
    new_dt = f"{slot_date}T{slot_time}"

    r = db.get_redis()
    r.hset(f"appointment:{appt_id}", "datetime", new_dt)

    actions.append(
        f"Rescheduled appointment {appt_id}: {old_dt or 'unknown'} → {new_dt}"
    )
    transcript.append({
        "role": "agent",
        "text": (
            f"Done — I've moved your appointment from {_format_dt_string(old_dt)} "
            f"to {_format_spoken(slot_date, slot_time)} at {location}. See you then!"
        ),
    })

    return {
        **state,
        "appointment_id": appt_id,
        "actions": actions,
        "transcript": transcript,
    }


def cancel_appointment(state: CallState) -> CallState:
    """Cancel the caller's next active appointment."""
    from app import db

    actions = list(state.get("actions", []))
    transcript = list(state.get("transcript", []))

    appt = _next_active_appointment(state.get("patient_uuid"))
    if not appt:
        actions.append("No active appointment found to cancel.")
        transcript.append({
            "role": "agent",
            "text": "I don't see an upcoming appointment to cancel on your record.",
        })
        return {**state, "actions": actions, "transcript": transcript}

    appt_id = appt["appointment_id"]
    db.update_appointment_status(appt_id, "cancelled")

    actions.append(f"Cancelled appointment {appt_id}")
    transcript.append({
        "role": "agent",
        "text": (
            f"I've cancelled your appointment on {_format_dt_string(appt.get('datetime'))}. "
            "Feel free to call back anytime to rebook. Take care!"
        ),
    })

    return {
        **state,
        "appointment_id": appt_id,
        "actions": actions,
        "transcript": transcript,
    }


def faq_node(state: CallState) -> CallState:
    """Answer an FAQ (hours / insurance / general) from the clinic KB."""
    actions = list(state.get("actions", []))
    transcript = list(state.get("transcript", []))
    message = state.get("message", "")

    ans = knowledge.answer(message)
    actions.append(f"Answered FAQ from knowledge base (intent={state.get('intent')})")
    transcript.append({"role": "agent", "text": ans})

    return {
        **state,
        "faq_answer": ans,
        "actions": actions,
        "transcript": transcript,
    }


def triage_emergency(state: CallState) -> CallState:
    """Dental-emergency triage: escalate to the on-call provider, do NOT book."""
    actions = list(state.get("actions", []))
    transcript = list(state.get("transcript", []))

    actions.append("URGENT: dental emergency detected — escalating to on-call provider.")
    actions.append("Booking suppressed; no appointment created for emergency call.")
    transcript.append({
        "role": "agent",
        "text": (
            "This sounds like a dental emergency. I'm connecting you with our "
            "on-call provider right now — please stay on the line and don't hang up."
        ),
    })

    return {
        **state,
        "escalated": True,
        "emergency": True,
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

    return {**state, "actions": actions, "transcript": transcript}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_intent(state: CallState) -> str:
    intent = state.get("intent")
    if intent == "reminder_flow":
        return "reminder_flow"
    if intent == "emergency":
        return "emergency"
    if intent == "reschedule":
        return "reschedule"
    if intent == "cancel":
        return "cancel"
    if intent in ("hours", "insurance", "other"):
        return "faq"
    return "book"


def _entry(state: CallState) -> CallState:
    return state


def build_graph():
    graph = StateGraph(CallState)

    graph.add_node("entry", _entry)
    graph.add_node("identify_patient", identify_patient)
    graph.add_node("collect_appointment_details", collect_appointment_details)
    graph.add_node("reschedule_appointment", reschedule_appointment)
    graph.add_node("cancel_appointment", cancel_appointment)
    graph.add_node("faq_node", faq_node)
    graph.add_node("triage_emergency", triage_emergency)
    graph.add_node("reminder_script", reminder_script)
    # Second identify node for reschedule/cancel branches (a node can't have two
    # inbound conditional targets with different successors, so we reuse one
    # identify node and branch after it).
    graph.add_node("identify_for_change", identify_patient)

    graph.set_entry_point("entry")

    graph.add_conditional_edges(
        "entry",
        _route_intent,
        {
            "book": "identify_patient",
            "reschedule": "identify_for_change",
            "cancel": "identify_for_change",
            "faq": "faq_node",
            "emergency": "triage_emergency",
            "reminder_flow": "reminder_script",
        },
    )

    # book: identify -> collect -> END
    graph.add_edge("identify_patient", "collect_appointment_details")
    graph.add_edge("collect_appointment_details", END)

    # reschedule / cancel share identify_for_change, then branch by intent.
    graph.add_conditional_edges(
        "identify_for_change",
        lambda s: "cancel" if s.get("intent") == "cancel" else "reschedule",
        {
            "reschedule": "reschedule_appointment",
            "cancel": "cancel_appointment",
        },
    )
    graph.add_edge("reschedule_appointment", END)
    graph.add_edge("cancel_appointment", END)

    graph.add_edge("faq_node", END)
    graph.add_edge("triage_emergency", END)
    graph.add_edge("reminder_script", END)

    return graph.compile()


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
    """Run the inbound flow for a simulated call.

    Classifies intent + language, routes through the graph, computes post-call
    intelligence (summary/sentiment), persists everything on the call record,
    and returns:

        {"call", "actions", "appointment"?, "intent", "language",
         "sentiment", "summary", "escalated", "emergency", "faq_answer"}
    """
    from app import db

    message = message or "I'd like to book an appointment at the next available time."

    intent = nlu.classify_intent(message)
    language = nlu.detect_language(message)

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
        "intent": intent,
        "language": language,
        "message": message,
        "escalated": False,
        "emergency": intent == "emergency",
        "actions": [
            f"Inbound call started from {phone}",
            f"Detected language: {language}",
            f"Classified intent: {intent}",
        ],
        "transcript": [{"role": "caller", "text": message}],
    }

    final = _get_graph().invoke(init)

    transcript = final.get("transcript", [])
    summary_text = nlu.summary(transcript)
    sentiment_val = nlu.sentiment(transcript)
    escalated = bool(final.get("escalated", False))
    emergency = bool(final.get("emergency", False))
    faq_answer = final.get("faq_answer")

    updated_call = db.update_call(
        call_uuid,
        patient_uuid=final.get("patient_uuid"),
        status="completed",
        ended=True,
        transcript=transcript,
    )

    # Persist the AI-brain metadata directly on the call hash (non-destructive
    # extra fields alongside the standard call model).
    try:
        r = db.get_redis()
        r.hset(
            f"call:{call_uuid}",
            mapping={
                "intent": intent,
                "language": language,
                "sentiment": sentiment_val,
                "summary": summary_text,
                "escalated": "1" if escalated else "0",
            },
        )
    except Exception:
        pass

    appointment = None
    appt_id = final.get("appointment_id")
    if appt_id:
        appointment = {
            "appointment_id": appt_id,
            "patient_uuid": final.get("patient_uuid"),
        }
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
        "intent": intent,
        "language": language,
        "sentiment": sentiment_val,
        "summary": summary_text,
        "escalated": escalated,
        "emergency": emergency,
        "faq_answer": faq_answer,
    }


def run_reminders() -> dict:
    """Run the reminder batch over all upcoming appointments."""
    from app import db

    upcoming = db.list_upcoming_appointments() or []
    results = []

    for appt in upcoming:
        appt_id = appt.get("appointment_id") or appt.get("id") or appt.get("uuid")
        patient_uuid = appt.get("patient_uuid")
        appt_dt = appt.get("datetime", "your upcoming appointment")

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
