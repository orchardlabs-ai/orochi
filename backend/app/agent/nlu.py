"""Natural-language understanding helpers for the Orochi voice agent.

Everything here is deterministic and offline by default. When
``settings.NOVITA_API_KEY`` is set, intent classification, summarization and
sentiment defer to the real LLM (via ``app.agent.llm``); otherwise fast keyword
rules produce the same shaped output so the demo never needs a network.
"""

from __future__ import annotations

import re
from typing import List

from ..config import settings

INTENTS = ["book", "reschedule", "cancel", "hours", "insurance", "emergency", "other"]

# ---------------------------------------------------------------------------
# Keyword tables
# ---------------------------------------------------------------------------
_EMERGENCY_TERMS = [
    "bleeding", "knocked out", "knocked-out", "severe pain", "swelling",
    "swollen", "broken tooth", "broke my tooth", "cracked tooth",
    "can't stop", "cannot stop", "abscess", "emergency", "excruciating",
    # Spanish
    "sangrado", "sangre", "dolor severo", "hinchazon", "hinchazón",
    "diente roto", "emergencia",
]

_RESCHEDULE_TERMS = [
    "reschedule", "move my appointment", "move my appt", "change my appointment",
    "change my appt", "push back", "different time", "another time",
    "later date", "earlier date", "reprogramar", "cambiar mi cita", "mover mi cita",
]

_CANCEL_TERMS = [
    "cancel", "cancellation", "call off", "no longer need", "won't make it",
    "cannot make it", "can't make it", "drop my appointment", "cancelar",
]

_BOOK_TERMS = [
    "book", "schedule", "make an appointment", "set up an appointment",
    "new appointment", "see the dentist", "come in", "get an appointment",
    "appointment for", "reservar", "agendar", "cita nueva", "hacer una cita",
]

_HOURS_TERMS = [
    "hour", "open", "close", "what time", "when are you", "horario", "abren",
    "cierran",
]

_INSURANCE_TERMS = [
    "insurance", "insur", "coverage", "do you accept", "do you take", "plan",
    "seguro", "cobertura", "aceptan",
]

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
_SPANISH_MARKERS = [
    "hola", "gracias", "cita", "necesito", "quiero", "por favor", "buenos",
    "buenas", "dolor", "diente", "muela", "seguro", "horario", "cancelar",
    "reprogramar", "cuando", "donde", "puedo", "tengo", "sangre", "emergencia",
    "estacionamiento", "abren", "cierran", "mañana",
]


def detect_language(message: str) -> str:
    """Return "es" for Spanish-looking text, else "en" (keyword/character)."""
    if not message:
        return "en"
    t = message.lower()
    # Spanish-only characters are a strong signal.
    if re.search(r"[ñ¡¿áéíóú]", t):
        return "es"
    words = re.findall(r"[a-záéíóúñ]+", t)
    hits = sum(1 for w in words if w in _SPANISH_MARKERS)
    if hits >= 1 and hits >= max(1, len(words) // 8):
        return "es"
    # Also trigger on any strong standalone marker.
    if any(f" {m} " in f" {t} " for m in ("hola", "necesito", "quiero", "cita")):
        return "es"
    return "en"


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------
def _rule_intent(message: str) -> str:
    t = (message or "").lower()

    # Emergency first — safety takes precedence over everything.
    if any(term in t for term in _EMERGENCY_TERMS):
        return "emergency"
    if any(term in t for term in _RESCHEDULE_TERMS):
        return "reschedule"
    if any(term in t for term in _CANCEL_TERMS):
        return "cancel"
    if any(term in t for term in _INSURANCE_TERMS):
        return "insurance"
    if any(term in t for term in _HOURS_TERMS):
        return "hours"
    if any(term in t for term in _BOOK_TERMS):
        return "book"
    return "other"


def classify_intent(message: str) -> str:
    """Classify a caller message into one of ``INTENTS``.

    Offline: keyword rules. Online (NOVITA_API_KEY set): asks the LLM and
    validates the reply against ``INTENTS``, falling back to rules on anything
    unexpected.
    """
    if not settings.NOVITA_API_KEY:
        return _rule_intent(message)

    from .llm import kimi_chat

    system = (
        "You are an intent classifier for a dental clinic phone line. "
        "Classify the caller's message into exactly one of these labels: "
        + ", ".join(INTENTS)
        + ". Reply with ONLY the label, nothing else."
    )
    try:
        raw = kimi_chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": message or ""},
            ],
            max_tokens=8,
            temperature=0.0,
        )
        label = (raw or "").strip().lower().split()[0].strip(".,!\"'")
        if label in INTENTS:
            return label
    except Exception:
        pass
    return _rule_intent(message)


def is_emergency(message: str) -> bool:
    t = (message or "").lower()
    return any(term in t for term in _EMERGENCY_TERMS)


# ---------------------------------------------------------------------------
# Post-call intelligence
# ---------------------------------------------------------------------------
def _transcript_text(transcript: List[dict]) -> str:
    return " ".join(str(turn.get("text", "")) for turn in (transcript or []))


_POSITIVE_TERMS = [
    "thank", "thanks", "great", "perfect", "appreciate", "wonderful",
    "awesome", "see you", "sounds good", "gracias", "perfecto",
]
_NEGATIVE_TERMS = [
    "sorry", "unfortunately", "no openings", "can't", "cannot", "pain",
    "bleeding", "emergency", "swelling", "urgent", "frustrat", "angry",
    "upset", "dolor", "emergencia",
]


def sentiment(transcript: List[dict]) -> str:
    """Return "positive" | "neutral" | "negative" for a call transcript."""
    text = _transcript_text(transcript).lower()
    if not text.strip():
        return "neutral"
    pos = sum(text.count(term) for term in _POSITIVE_TERMS)
    neg = sum(text.count(term) for term in _NEGATIVE_TERMS)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def summary(transcript: List[dict]) -> str:
    """Return a one-line post-call summary.

    Offline: a deterministic template built from the transcript. Online: an LLM
    summary, falling back to the template on any error.
    """
    if not transcript:
        return "No conversation recorded."

    if settings.NOVITA_API_KEY:
        from .llm import kimi_chat

        convo = "\n".join(
            f"{turn.get('role', 'agent')}: {turn.get('text', '')}"
            for turn in transcript
        )
        try:
            raw = kimi_chat(
                [
                    {
                        "role": "system",
                        "content": "Summarize this clinic phone call in one short "
                        "sentence for the front-desk log.",
                    },
                    {"role": "user", "content": convo},
                ],
                max_tokens=60,
                temperature=0.2,
            )
            text = (raw or "").strip()
            if text and not text.startswith("{"):
                return text
        except Exception:
            pass

    # Deterministic fallback: caller opening + agent outcome.
    caller = next(
        (t.get("text", "") for t in transcript if t.get("role") == "caller"), ""
    )
    last_agent = next(
        (t.get("text", "") for t in reversed(transcript) if t.get("role") == "agent"),
        "",
    )
    caller = caller.strip()
    last_agent = last_agent.strip()
    if caller and last_agent:
        return f"Caller: \"{caller}\" Outcome: {last_agent}"
    return caller or last_agent or "Call completed."
