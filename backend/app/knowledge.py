"""Tiny clinic knowledge base for the Orochi voice agent.

Deterministic, offline. ``answer(question)`` keyword-matches a question against
a small set of clinic facts and returns a natural-language reply. Used by the
``hours`` and ``insurance`` intents (and any generic FAQ lookup).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Clinic facts (single source of truth for the FAQ)
# ---------------------------------------------------------------------------
CLINIC = {
    "name": "Orochi Dental",
    "hours": "Monday through Friday, 8:00 AM to 6:00 PM. We're closed weekends.",
    "address": "1200 Cedar Avenue, Suite 300, Portland, OR 97201.",
    "phone": "(503) 555-0142.",
    "insurance": [
        "Delta Dental",
        "Cigna",
        "Aetna",
        "MetLife",
        "Guardian",
        "UnitedHealthcare",
    ],
    "parking": "Free patient parking is available in the lot behind the building, "
    "and the Cedar Avenue parking garage is one block north.",
}


def accepted_insurance_sentence() -> str:
    plans = CLINIC["insurance"]
    joined = ", ".join(plans[:-1]) + f", and {plans[-1]}"
    return f"We accept most major dental plans, including {joined}."


def _match(text: str, *keywords: str) -> bool:
    return any(k in text for k in keywords)


def answer(question: str) -> str:
    """Return a spoken-style answer to a clinic FAQ, keyword matched."""
    t = (question or "").lower()

    if _match(t, "hour", "open", "close", "time", "when are you", "horario", "abren", "cierran"):
        return f"Our hours are {CLINIC['hours']}"

    if _match(t, "insurance", "insur", "plan", "coverage", "accept", "seguro", "cobertura"):
        return accepted_insurance_sentence()

    if _match(t, "park", "parking", "estacion", "garage"):
        return CLINIC["parking"]

    if _match(t, "address", "where", "located", "location", "direccion", "donde"):
        return f"We're located at {CLINIC['address']}"

    if _match(t, "phone", "number", "call you", "reach", "telefono", "numero"):
        return f"You can reach our front desk at {CLINIC['phone']}"

    # Fallback: give hours + phone, the two most useful facts.
    return (
        f"Our hours are {CLINIC['hours']} You can reach our front desk at "
        f"{CLINIC['phone']}"
    )
