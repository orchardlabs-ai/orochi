Let’s write a lightweight PRD oriented around a local Docker prototype, then sprinkle in Python snippets for LangGraph + Novita (Kimi K2*) + Dragonfly.

I’ll keep it concrete enough that you can drop this into a repo as `PRD.md` + `main.py` scaffolding.

***

## 1. Product scope

### 1.1 Use cases

- **Inbound calls – appointment creation**  
  A patient calls a clinic number; the agent collects minimal PHI (name, phone, desired time) and creates or updates an appointment record.

- **Outbound calls – appointment reminders**  
  The system automatically calls patients before upcoming appointments, delivers a reminder, and optionally allows confirmation/cancellation.

HIPAA stance for prototype:  
- Treat name, phone, and appointment metadata as PHI, but for this local prototype it’s all stored in Dragonfly (Redis-compatible), with future migration to HIPAA-ready cloud services. [dragonflydb](https://www.dragonflydb.io/docs/cloud/connect/redis-clients)
- Design around a **PHI edge** and UUIDs so later HIPAA hardening is straightforward. [protecto](https://www.protecto.ai/blog/advanced-techniques-for-de-identifying-pii-and-healthcare-data/)

***

## 2. High-level architecture (prototype)

### 2.1 Components

- **Twilio (mocked or real)**  
  - Webhook endpoints for inbound calls (`/twilio/inbound`) and outbound status callbacks (`/twilio/outbound-status`).  
  - For prototype, you can mock Twilio payloads locally.

- **PHI Edge Service (Python, FastAPI or similar)**  
  - Receives Twilio events, parses caller phone/name.  
  - Stores patient + appointment data in Dragonfly.  
  - Issues `patient_uuid` and `call_uuid`.

- **LangGraph Agent Orchestrator**  
  - Graph defines nodes for: `collect_patient_info`, `schedule_appointment`, `prepare_reminder_script`.  
  - Uses Novita Kimi K2* LLM for dialog and decision logic via a LangGraph LLM node. [github](https://github.com/langchain-ai/langgraph)

- **Dragonfly data store (local Docker)**  
  - Redis-compatible KV and simple hashes/lists to store patient records, appointments, and conversation state for the prototype. [github](https://github.com/dragonflydb/dragonfly-examples)

***

## 3. Data model (prototype in Dragonfly)

Use simple Redis structures:

- `patient:{patient_uuid}` → hash  
  - `name`, `phone`, `created_at`

- `appointment:{appointment_id}` → hash  
  - `patient_uuid`, `datetime`, `location`, `status` (`scheduled`, `confirmed`, `cancelled`)

- `call:{call_uuid}` → hash  
  - `patient_uuid`, `direction` (`inbound`/`outbound`), `started_at`, `ended_at`

- `appointments_by_patient:{patient_uuid}` → list of `appointment_id`

***

## 4. LangGraph design

### 4.1 State definition

Use a typed dict-like state for LangGraph:

```python
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph

class CallState(TypedDict, total=False):
    call_uuid: str
    patient_uuid: Optional[str]
    caller_phone: Optional[str]
    patient_name: Optional[str]
    intent: Optional[str]          # "create_appointment" or "reminder_flow"
    appointment_id: Optional[str]
    actions: List[str]             # log of agent decisions
```



### 4.2 Nodes

- `identify_patient_node`: resolve `caller_phone` → `patient_uuid` or create new patient.  
- `collect_appointment_details_node`: use LLM to ask for date/time, then store appointment.  
- `reminder_script_node`: generate outbound reminder script for patient.

Skeleton with LangGraph:

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(CallState)

def identify_patient(state: CallState) -> CallState:
    # TODO: Dragonfly lookup by phone, create if not exists
    state["actions"].append("identify_patient")
    return state

def collect_appointment_details(state: CallState) -> CallState:
    state["actions"].append("collect_appointment_details")
    # TODO: call Novita Kimi to converse and capture datetime/location
    return state

def reminder_script(state: CallState) -> CallState:
    state["actions"].append("reminder_script")
    # TODO: call Novita Kimi to generate safe reminder text
    return state

graph.add_node("identify_patient", identify_patient)
graph.add_node("collect_appointment_details", collect_appointment_details)
graph.add_node("reminder_script", reminder_script)

def router(state: CallState) -> str:
    if state.get("intent") == "create_appointment":
        if state.get("patient_uuid") is None:
            return "identify_patient"
        if state.get("appointment_id") is None:
            return "collect_appointment_details"
        return END
    elif state.get("intent") == "reminder_flow":
        return "reminder_script"
    return END

graph.set_entry_point("identify_patient")
graph.add_edge("identify_patient", "collect_appointment_details")
graph.add_edge("collect_appointment_details", END)
graph.add_edge("reminder_script", END)
graph.set_router(router)

call_agent_app = graph.compile()
```



***

## 5. Novita Kimi K2* integration (LLM calls)

Use the Kimi K2* API via simple HTTP requests; pattern similar to NVIDIA/Moonshot examples. [build.nvidia](https://build.nvidia.com/moonshotai/kimi-k2.6)

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



Example use inside `collect_appointment_details`:

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

***

## 6. Dragonfly integration (local Docker)

Run Dragonfly as a local container and talk to it via `redis-py`. [dragonflydb](https://www.dragonflydb.io/docs/development/sdks)

### 6.1 Docker compose snippet (conceptual)

```yaml
version: "3.8"
services:
  dragonfly:
    image: dragonflydb/dragonfly
    ports:
      - "6379:6379"
    command: ["--logtostderr"]
  app:
    build: .
    depends_on:
      - dragonfly
    environment:
      DRAGONFLY_URL: redis://dragonfly:6379
```



### 6.2 Python client

```python
import os
import redis

DRAGONFLY_URL = os.getenv("DRAGONFLY_URL", "redis://localhost:6379")
db = redis.Redis.from_url(DRAGONFLY_URL)

def create_or_get_patient(phone: str, name: str) -> str:
    # naive example: key lookup by phone
    patient_uuid = db.get(f"phone:{phone}")
    if patient_uuid:
        return patient_uuid.decode()

    import uuid
    patient_uuid = str(uuid.uuid4())
    pipe = db.pipeline()
    pipe.hset(f"patient:{patient_uuid}", mapping={"name": name, "phone": phone})
    pipe.set(f"phone:{phone}", patient_uuid)
    pipe.execute()
    return patient_uuid
```



***

## 7. Inbound and outbound flows (API-level)

### 7.1 Inbound webhook handler

Simplified FastAPI example:

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/twilio/inbound")
async def twilio_inbound(request: Request):
    form = await request.form()
    caller_phone = form.get("From")
    call_sid = form.get("CallSid")
    # For prototype, assume name is spoken later and set by agent later
    initial_state = CallState(
        call_uuid=call_sid,
        caller_phone=caller_phone,
        intent="create_appointment",
        actions=[],
    )
    result_state = call_agent_app.invoke(initial_state)
    # TODO: return TwiML or appropriate response to Twilio
    return {"status": "ok", "state": result_state}
```



### 7.2 Outbound reminder scheduler

Prototype: simple script that scans Dragonfly for upcoming appointments and calls the agent to generate scripts.

```python
import datetime

def get_upcoming_appointments():
    # TODO: implement a simple scan based on datetime stored in appointment hashes
    return []

def run_reminder_batch():
    for appt in get_upcoming_appointments():
        state = CallState(
            call_uuid=str(uuid.uuid4()),
            patient_uuid=appt["patient_uuid"],
            appointment_id=appt["id"],
            intent="reminder_flow",
            actions=[],
        )
        result_state = call_agent_app.invoke(state)
        # TODO: use result_state to trigger Twilio outbound call with reminder text

if __name__ == "__main__":
    run_reminder_batch()
```



***

This should be enough to start wiring a local Docker prototype: Dragonfly for storage, LangGraph for orchestration, Novita Kimi for dialog/logic, and Twilio mocked or real.

To keep it iterative: what part do you want to implement first—the LangGraph graph and state, or the Dragonfly persistence functions for patients and appointments?
