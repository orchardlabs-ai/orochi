---
title: Novita Kimi Integration
tags:
  - prd
  - llm
  - novita
  - kimi
status: draft
---

# Novita Kimi K2\* Integration

> [!note] Part of [[Orochi PRD]] · drives nodes in [[LangGraph Design]]

Call Kimi K2\* over simple HTTP; pattern similar to NVIDIA / Moonshot examples.

## Client

```python
import os
import requests

NOVITA_API_KEY = os.getenv("NOVITA_API_KEY")
NOVITA_URL = "https://api.novita.ai/v1/chat/completions"  # adjust to actual endpoint

def kimi_chat(messages, model="kimi-k2.5", max_tokens=1024, temperature=0.2):
    headers = {
        "Authorization": f"Bearer {NOVITA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(NOVITA_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
```

## Example — inside `collect_appointment_details`

```python
def collect_appointment_details(state: CallState) -> CallState:
    prompt = (
        "You are a scheduling assistant for a clinic. "
        "Ask the caller for the date and time they'd like an appointment. "
        "Return the result as JSON with keys 'date' and 'time'."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Caller wants to book an appointment."},
    ]
    reply = kimi_chat(messages)
    # TODO: parse JSON from reply, then write to Dragonfly
    state["actions"].append("collect_appointment_details_llm")
    return state
```

> [!reference]
> - [NVIDIA build — Moonshot Kimi K2](https://build.nvidia.com/moonshotai/kimi-k2.6)
