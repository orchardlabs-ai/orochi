---
title: Data Model
tags:
  - prd
  - data-model
  - dragonfly
status: draft
---

# Data Model

> [!note] Part of [[Orochi PRD]] · implemented via [[Dragonfly Integration]]

Simple Redis structures for the prototype:

> [!info] `patient:{patient_uuid}` → hash
> `name`, `phone`, `created_at`

> [!info] `appointment:{appointment_id}` → hash
> `patient_uuid`, `datetime`, `location`, `status` — one of `scheduled`, `confirmed`, `cancelled`

> [!info] `call:{call_uuid}` → hash
> `patient_uuid`, `direction` (`inbound` / `outbound`), `started_at`, `ended_at`

> [!info] `appointments_by_patient:{patient_uuid}` → list
> list of `appointment_id`

## Entity relationships

```mermaid
erDiagram
    PATIENT ||--o{ APPOINTMENT : has
    PATIENT ||--o{ CALL : participates
    APPOINTMENT }o--|| CALL : "created/updated by"
    PATIENT {
        string patient_uuid PK
        string name
        string phone
        string created_at
    }
    APPOINTMENT {
        string appointment_id PK
        string patient_uuid FK
        string datetime
        string location
        string status
    }
    CALL {
        string call_uuid PK
        string patient_uuid FK
        string direction
        string started_at
        string ended_at
    }
```

## Status lifecycle

```mermaid
stateDiagram-v2
    [*] --> scheduled
    scheduled --> confirmed
    scheduled --> cancelled
    confirmed --> cancelled
```
