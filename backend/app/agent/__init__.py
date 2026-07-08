"""Orochi LangGraph agent package.

Exposes the two high-level entrypoints used by the FastAPI simulate routes:

    run_inbound(phone, name, message) -> dict
    run_reminders() -> dict

See graph.py for the LangGraph wiring and llm.py for the Novita Kimi client
(stubbed offline by default).
"""

from .state import CallState
from .graph import build_graph, run_inbound, run_reminders
from .llm import kimi_chat

__all__ = [
    "CallState",
    "build_graph",
    "run_inbound",
    "run_reminders",
    "kimi_chat",
]
