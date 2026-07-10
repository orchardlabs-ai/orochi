---
title: Transcripts
tags:
  - prd
  - flows
  - transcripts
  - ai-judging
status: active
updated: 2026-07-10
---

# Transcripts

> [!note] Part of [[Orochi PRD]] · demo feature informed by [[Synthetic Transcript Generation Research]]

Batch call-transcript judging demo: AI-style review of a group of calls, surfacing actions for the receptionist (coaching), the business owner (recurring insights), and compliance risk — plus a per-call quality score.

## Data model

Reuses the existing `call:{uuid}` Redis hash in `db.py` (no parallel store). A `judgment` dict is persisted alongside `transcript`:

```json
{
  "receptionist_coaching": ["string"],
  "business_owner_insights": ["string"],
  "compliance_flags": ["string"],
  "quality_score": 1,
  "booked": true
}
```

25 synthetic calls are seeded in `backend/app/seed_transcripts.py` (booking/reschedule/cancel/insurance/emergency/hours scenarios, friendly vs efficient receptionist tone, a few frustrated-caller and missed-upsell edge cases, 4 calls carrying compliance flags). Judgments are **precomputed/mocked**, not live LLM calls — same offline-first bias as `nlu.py`.

## API

`backend/app/routers/transcripts.py`:
- `GET /api/transcripts` — list with judgment summary
- `GET /api/transcripts/{call_uuid}` — full transcript + judgment
- `GET /api/transcripts/overview` — batch aggregation (counts, average quality, top recurring themes)

## UI

`frontend/src/pages/Transcripts.tsx`, nav item + route at `/transcripts`, alongside [[Insights|/insights]] and `/calls`. Batch overview stat row up top (mirrors Insights.tsx), call list below that drills into a per-call view with turn-by-turn transcript + inline coaching/flag annotations (mirrors Calls.tsx's list+detail pattern).

## Timestamps

Seeded calls are spread across the past ~2 weeks with varied times of day and call durations (deterministic pseudo-random offsets in `_call()`, not real wall-clock time) — `db.create_call`/`db.update_call` accept explicit `started_at`/`ended_at` for this. Fixed 2026-07-10 after the verify pass caught all 25 seeded calls sharing one identical timestamp.
