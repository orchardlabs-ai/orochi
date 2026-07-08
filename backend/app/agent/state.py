"""Shared LangGraph state contract for the Orochi call agent."""

from __future__ import annotations

from typing import List, Optional, TypedDict


class CallState(TypedDict, total=False):
    """State object threaded through the LangGraph nodes.

    All fields are optional (total=False) so nodes may populate them
    incrementally as the flow progresses.

    Fields:
        call_uuid:      UUID of the call record created for this interaction.
        patient_uuid:   UUID of the identified / created patient.
        caller_phone:   E.164-ish phone number of the caller.
        patient_name:   Human name supplied by / resolved for the caller.
        intent:         Routing key. One of "create_appointment" | "reminder_flow".
        appointment_id: ID of the appointment created (create_appointment flow).
        actions:        Human-readable log of what the agent did (for the UI).
        transcript:     Ordered list of {role, text} turns.
        message:        The inbound caller message being processed.
    """

    call_uuid: str
    patient_uuid: str
    caller_phone: str
    patient_name: str
    intent: str
    appointment_id: Optional[str]
    actions: List[str]
    transcript: List[dict]
    message: str
