---
title: Open Questions
tags:
  - prd
  - decisions
  - open-questions
status: draft
---

# Open Questions

> [!note] Part of [[Orochi PRD]] — decisions needed before/during build

> [!question] UX / dashboard
> The PRD has **no UI**. We're adding a web dashboard + **login**. Scope: view patients, appointments, and calls; trigger a reminder batch; a call simulator to exercise the agent without real telephony.

> [!question] Auth model
> Login for a **staff/clinic user**. Simplest secure prototype: email + password with session cookies, seeded admin user. SSO/MFA deferred.

> [!question] LangGraph routing bug
> Original spec mixes static edges with a non-existent `set_router`. Resolve with `add_conditional_edges`. See [[LangGraph Design]].

> [!question] Real vs mocked Twilio & LLM
> Prototype should run fully offline: **mock Twilio** and allow a **stub LLM** when no `NOVITA_API_KEY` is set.

> [!question] Backend framework
> PRD says "FastAPI or similar." Confirm **FastAPI**.

## Decision log

| # | Question | Decision | Date |
|---|----------|----------|------|
| 1 | UI framework | **React + Vite SPA** | 2026-07-08 |
| 2 | Auth | **Email + password, seeded admin, session cookies** | 2026-07-08 |
| 3 | Telephony & LLM in prototype | **Fully mocked by default; real when keys set** | 2026-07-08 |
| 4 | Build scope | **Full vertical slice (compose + backend + agent + auth + UI)** | 2026-07-08 |
| 5 | Backend framework | **FastAPI** | 2026-07-08 |
