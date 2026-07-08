"""Deterministic, offline mock of the Twilio API surface.

No network calls are ever made. Every helper returns a plain dict with a
mock ``sid`` of the form ``MOCK-<8 hex chars>``. The sid is derived
deterministically from the call arguments so the same inputs always yield
the same sid (handy for a demo / tests).
"""

import hashlib


def _mock_sid(*parts: str) -> str:
    """Deterministic short sid: ``MOCK-`` + 8 hex chars from the args."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return "MOCK-" + digest[:8]


def send_sms(to: str, body: str) -> dict:
    return {
        "sid": _mock_sid("sms", to, body),
        "channel": "sms",
        "status": "delivered",
        "to": to,
        "body": body,
    }


def send_email(to: str, subject: str, body: str) -> dict:
    return {
        "sid": _mock_sid("email", to, subject, body),
        "channel": "email",
        "status": "delivered",
        "to": to,
        "subject": subject,
        "body": body,
    }


def place_call(to: str, script: str) -> dict:
    return {
        "sid": _mock_sid("voice", to, script),
        "channel": "voice",
        "status": "completed",
        "to": to,
        "script": script,
    }
