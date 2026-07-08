---
title: Product Scope
tags:
  - prd
  - scope
status: draft
---

# Product Scope

> [!note] Part of [[Orochi PRD]]

## Use cases

> [!example] Inbound — appointment creation
> A patient calls a clinic number. The agent collects minimal PHI (**name, phone, desired time**) and creates or updates an appointment record.

> [!example] Outbound — appointment reminders
> The system automatically calls patients before upcoming appointments, delivers a reminder, and optionally allows **confirmation / cancellation**.

## HIPAA stance (prototype)

- Treat **name, phone, and appointment metadata** as PHI. For this local prototype it's all stored in [[Dragonfly Integration|Dragonfly]] (Redis-compatible), with future migration to HIPAA-ready cloud services.
- Design around a **PHI edge** and **UUIDs** so later HIPAA hardening is straightforward.

> [!quote] References
> - [Dragonfly — Redis clients](https://www.dragonflydb.io/docs/cloud/connect/redis-clients)
> - [Protecto — de-identifying PII / healthcare data](https://www.protecto.ai/blog/advanced-techniques-for-de-identifying-pii-and-healthcare-data/)

## Out of scope (for now)

- Real PHI in production
- Payment / billing
- EHR integration
- Multi-language support

See [[Open Questions]] for decisions that shape scope.
