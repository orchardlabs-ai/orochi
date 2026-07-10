---
title: Roadmap
tags:
  - prd
  - roadmap
  - planning
status: active
updated: 2026-07-08
---

# 🗺️ Orochi Roadmap

> [!note] Part of [[Orochi PRD]] · informed by [[research]] and [[Twilio API Research]]
> Prioritized path from the current demo mockup toward a production-credible clinic voice agent. Everything below the "Now" line is **mocked** (Twilio/LLM/PMS faked) for demonstration.

## Now — shipped in the demo

> [!success] Live in the app
> - Inbound booking agent with **intent routing** (book / reschedule / cancel / hours / insurance / emergency)
> - **Emergency triage** + escalation · **multi-language** tag · **FAQ** answers · **post-call summary + sentiment**
> - **Availability-aware booking** — weekly 45-min slot template, nearest-slot snapping ([[Schedule & Availability]])
> - **Messages** — mock Twilio SMS/email/voice + **two-way confirmation**
> - **Waitlist / ASAP backfill** · **Outbound campaigns** (recall / reactivation / missed-call recovery)
> - **Insights** — call analytics, booking conversion, **no-show risk** scoring
> - **[[Transcripts]]** — batch AI judging of call transcripts: receptionist coaching, business-owner insights, compliance flags, quality score ([[Synthetic Transcript Generation Research]])
> - Auth, dashboard, patients, appointments, calls, agent simulator

## Next — deepen realism (still mockable)

> [!todo] High-leverage, mostly additive
> - **Providers · operatories · procedure types** with variable durations (replaces the flat slot grid — the research's #1 gap: *"a flat availability check is insufficient"*)
> - **Configurable reminder cadence** (1 week / 2 days / day-of) + real scheduling of outbound jobs
> - **Human escalation queue** — surface escalated/emergency calls to staff with full context (call pop)
> - **Insurance eligibility** mock verification during the call
> - Timezone-aware datetimes + appointment end-times

## Later — production integration

> [!abstract] Requires real vendors
> - **Real telephony** via Twilio **Media Streams / ConversationRelay** ([[Twilio API Research]])
> - **PMS write-back** — Open Dental / Dentrix / Eaglesoft via NexHealth Synchronizer or CRMBridge.ai (the market's true differentiator)
> - **HIPAA hardening** — BAA-covered infra, recording encryption, audit logs, PHI redaction
> - Multi-location / DSO dashboards

## Feature ↔ research map

| Orochi feature | Market analogue (research.md) |
|----------------|-------------------------------|
| Intent routing + emergency triage | Arini / HeyGent inbound AI, emergency detection |
| Two-way confirmation | Weave / Solutionreach reminders |
| Waitlist backfill | Lighthouse "Fill-in" / ASAP list |
| Recall / reactivation campaigns | Annie "silent churn", healow Smart Campaigns |
| Call intelligence + no-show risk | Weave / Adit Call Intelligence |
| PMS write-back (Later) | NexHealth Synchronizer, CRMBridge.ai |

See [[UX Demo Thread]] for how the UI showcases each of these.
