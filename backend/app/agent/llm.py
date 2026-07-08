"""Novita Kimi chat client for Orochi.

Offline-first: if ``NOVITA_API_KEY`` is unset the client returns a deterministic
STUB response. The stub parses the user's most recent message for a plausible
date and time and always returns a JSON string with keys ``date``, ``time`` and
``location``. When ``NOVITA_API_KEY`` is set it performs a real HTTP POST to the
Novita chat completions endpoint (``NOVITA_URL``).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional

import requests

DEFAULT_NOVITA_URL = "https://api.novita.ai/v3/openai/chat/completions"
DEFAULT_MODEL = "moonshotai/kimi-k2-instruct"
DEFAULT_LOCATION = "Main Clinic"

# ---------------------------------------------------------------------------
# Deterministic stub parsing helpers
# ---------------------------------------------------------------------------

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _last_user_text(messages: List[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return str(messages[-1].get("content", "")) if messages else ""


def _extract_time(text: str) -> Optional[str]:
    """Return an HH:MM (24h) string parsed from ``text`` or None."""
    t = text.lower()

    # e.g. "3:30 pm", "10:00am", "2 pm", "14:00"
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", t)
    if m:
        hour = int(m.group(1)) % 12
        minute = int(m.group(2) or 0)
        if m.group(3) == "pm":
            hour += 12
        return f"{hour:02d}:{minute:02d}"

    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", t)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    if "morning" in t:
        return "09:00"
    if "afternoon" in t:
        return "14:00"
    if "evening" in t:
        return "17:00"
    if "noon" in t:
        return "12:00"
    return None


def _extract_date(text: str, base: Optional[datetime] = None) -> Optional[str]:
    """Return a YYYY-MM-DD string parsed from ``text`` or None."""
    base = base or datetime.now()
    t = text.lower()

    # Relative keywords
    if "today" in t:
        return base.date().isoformat()
    if "tomorrow" in t:
        return (base + timedelta(days=1)).date().isoformat()

    # "next <weekday>" / "<weekday>"
    for name, idx in _WEEKDAYS.items():
        if name in t:
            days_ahead = (idx - base.weekday()) % 7
            if days_ahead == 0 or ("next" in t):
                days_ahead = days_ahead or 7
                if "next" in t and days_ahead < 7:
                    days_ahead += 0  # keep upcoming instance
            days_ahead = days_ahead or 7
            return (base + timedelta(days=days_ahead)).date().isoformat()

    # ISO date  2026-07-15
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # US date  07/15/2026 or 7/15
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else base.year
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).date().isoformat()
        except ValueError:
            pass

    # "July 15" / "15 July"
    m = re.search(r"\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\b", t)
    if m and m.group(1) in _MONTHS:
        month, day = _MONTHS[m.group(1)], int(m.group(2))
        try:
            return datetime(base.year, month, day).date().isoformat()
        except ValueError:
            pass
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)\b", t)
    if m and m.group(2) in _MONTHS:
        month, day = _MONTHS[m.group(2)], int(m.group(1))
        try:
            return datetime(base.year, month, day).date().isoformat()
        except ValueError:
            pass

    return None


def _extract_location(text: str) -> Optional[str]:
    m = re.search(r"\bat (?:the )?([A-Za-z][A-Za-z0-9 '&-]{2,40}?)(?: (?:clinic|office|branch|location))\b", text, re.I)
    if m:
        base = m.group(1).strip().title()
        return f"{base} Clinic"
    m = re.search(r"\b([A-Za-z][A-Za-z0-9 '&-]{2,40}?) (clinic|office|branch|location)\b", text, re.I)
    if m:
        return f"{m.group(1).strip().title()} {m.group(2).title()}"
    return None


def _stub_response(messages: List[dict]) -> str:
    """Deterministic offline response: a JSON string {date,time,location}."""
    text = _last_user_text(messages)

    date = _extract_date(text)
    time = _extract_time(text)
    location = _extract_location(text)

    payload = {
        "date": date or "next available",
        "time": time or "09:00",
        "location": location or DEFAULT_LOCATION,
    }
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def kimi_chat(
    messages: List[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int = 512,
    temperature: float = 0.2,
) -> str:
    """Return the assistant's text content for ``messages``.

    ``messages`` is an OpenAI-style list of {"role", "content"} dicts.

    Offline (no NOVITA_API_KEY): returns a deterministic JSON string with keys
    date/time/location parsed from the latest user message.

    Online (NOVITA_API_KEY set): POSTs to NOVITA_URL and returns the model's
    message content string. Falls back to the stub on any transport error so the
    prototype never hard-fails.
    """
    api_key = os.getenv("NOVITA_API_KEY")
    if not api_key:
        return _stub_response(messages)

    url = os.getenv("NOVITA_URL", DEFAULT_NOVITA_URL)
    body = {
        "model": os.getenv("NOVITA_MODEL", model),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        # Degrade gracefully to the deterministic stub.
        return _stub_response(messages)


def parse_appointment_json(content: str) -> dict:
    """Best-effort parse of an LLM reply into {date,time,location}.

    Tolerates models that wrap JSON in prose or code fences.
    """
    try:
        return json.loads(content)
    except (ValueError, TypeError):
        pass
    m = re.search(r"\{.*\}", content or "", re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except ValueError:
            pass
    return {"date": "next available", "time": "09:00", "location": DEFAULT_LOCATION}
