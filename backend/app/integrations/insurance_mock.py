"""Deterministic mock insurance eligibility verification.

No network. Everything is derived from a stable hash of ``member_id`` (and the
payer) so the same inputs always yield the same eligibility result. Useful for a
"verify during the call" demo action.
"""

import hashlib
import time
from typing import Optional

# A small catalog of plans / services to make the mock feel realistic.
_PLANS = [
    "PPO Standard",
    "PPO Plus",
    "HMO Select",
    "HMO Value",
    "EPO Core",
    "High Deductible Health Plan",
]

_SERVICES = [
    "Preventive / Cleaning",
    "Diagnostic (X-Ray)",
    "Restorative (Fillings)",
    "Major (Crowns / Bridges)",
    "Orthodontics",
]


def _digest(member_id: str, payer: str) -> int:
    raw = f"{(payer or '').strip().lower()}|{(member_id or '').strip().lower()}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest(), 16)


def verify_eligibility(member_id: str, payer: str) -> dict:
    """Return a deterministic mock eligibility payload for a member/payer pair.

    Most members are eligible; a small deterministic fraction (~1 in 6) come
    back "inactive". All monetary/coverage values are stable for a given input.
    """
    member_id = (member_id or "").strip()
    payer = (payer or "").strip()

    h = _digest(member_id, payer)

    # ~1 in 6 members are inactive (deterministic).
    eligible = (h % 6) != 0

    plan = _PLANS[(h >> 8) % len(_PLANS)]
    # Group number: stable 5-digit code.
    group = f"GRP-{(h >> 16) % 90000 + 10000}"

    if eligible:
        copay = [15, 20, 25, 30, 40, 50][(h >> 24) % 6]
        # Deductible remaining between $0 and $1500 in $50 steps.
        deductible_remaining = ((h >> 32) % 31) * 50
        coverage = []
        for i, service in enumerate(_SERVICES):
            pct_options = [100, 80, 50, 0]
            pct = pct_options[((h >> (40 + i * 3)) % 4)]
            # Preventive is almost always fully covered when eligible.
            if i == 0:
                pct = 100
            coverage.append({"service": service, "covered_pct": pct})
    else:
        copay = 0
        deductible_remaining = 0
        coverage = []

    return {
        "eligible": eligible,
        "payer": payer,
        "member_id": member_id,
        "plan": plan if eligible else None,
        "group": group if eligible else None,
        "copay": copay,
        "deductible_remaining": deductible_remaining,
        "coverage": coverage,
        "verified_at": str(int(time.time())),
        "status": "active" if eligible else "inactive",
    }
