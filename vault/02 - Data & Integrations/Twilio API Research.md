---
title: Twilio API Research
tags:
  - prd
  - twilio
  - research
  - voice
status: reference
source: Tavily pro research
researched: 2026-07-08
---

# Twilio API Research — Voice Agent

> [!note] Part of [[Orochi PRD]] · informs [[Call Flows]] and [[Architecture Overview]]
> Research into the Twilio features Orochi needs to move from the mocked prototype to real telephony. Cited to official Twilio docs.

> [!abstract] TL;DR for Orochi
> - **Inbound**: HTTPS webhook returns **TwiML** (`<Gather>` for DTMF/speech, `<Say>` for prompts). For an LLM agent, use `<Connect><ConversationRelay url="wss://…">` or `<Connect><Stream>` (Media Streams).
> - **Outbound**: `POST /2010-04-01/Accounts/{Sid}/Calls.json` with `To`, `From`, `Url`/`Twiml`, `StatusCallback`, `MachineDetection`.
> - **Real-time AI voice**: **ConversationRelay** (managed STT/TTS for LLM agents) or raw **Media Streams** (μ-law 8 kHz base64 over `wss://`).
> - **Security**: validate the `X-Twilio-Signature` header (SDK `RequestValidator`).
> - **HIPAA**: sign a **BAA**, keep PHI in BAA-covered projects, enable **recording encryption**. A BAA alone ≠ compliant.

## 1. Programmable Voice — inbound & TwiML

Inbound webhooks are HTTPS endpoints receiving Twilio POST params and replying with TwiML. Key verbs:

| Verb | Use in Orochi |
|------|---------------|
| `<Say>` | Speak prompts (`voice`, `language`, `loop`) |
| `<Gather>` | Collect `dtmf`/`speech` (`numDigits`, `timeout`, `hints`, `actionOnEmptyResult`, `partialResultCallback`) |
| `<Play>` | Play audio (audio/mpeg, audio/wav) |
| `<Dial>` | Route to a human agent (`action`, `timeout`, recording) |
| `<Connect>` | Attach ConversationRelay / Stream nouns |
| `<Start>`/`<Stream>` | Media Streams to a `wss://` endpoint (`track`, `statusCallback`) |

## 2. Outbound calls (REST)

```bash
curl -X POST "https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Calls.json" \
  -u "{AccountSid}:{AuthToken}" \
  -d "To=+15559876543" -d "From=+1XXXXXXXXXX" \
  -d "Url=https://orochi.example.com/twilio/outbound-twiml" \
  -d "StatusCallback=https://orochi.example.com/twilio/outbound-status" \
  -d "MachineDetection=DetectMessageEnd"
```

> [!tip] Maps to [[Call Flows|reminder batch]]
> `MachineDetection=Enable` → connect only on a human; `DetectMessageEnd` → wait for the beep to leave a voicemail reminder.

## 3. Real-time AI voice — ConversationRelay & Media Streams

> [!example] ConversationRelay (recommended for an LLM agent)
> `<Connect><ConversationRelay url="wss://…" welcomeGreeting="…" language="en-US"></Connect>`. Twilio handles STT/TTS; your socket receives structured events (`setup`, `prompt`, `dtmf`, `interrupt`, `error`, `end`) and you send `text`/`sendDigits`/`language`. Requires enabling the **Predictive & Generative AI/ML Addendum** in Voice Settings.

> [!example] Media Streams (raw audio)
> `wss://` socket; message types `Connected`, `Start`, `Media`, `DTMF`, `Stop`, `Mark`. Audio is **audio/x-mulaw, 8000 Hz, base64** in both directions. Default region US1 (also IE1, AU1).

> [!warning] PHI boundary
> Only route audio/metadata over BAA-covered, HIPAA-eligible products. Do **not** forward PHI to a non-BAA third-party LLM (e.g. Novita/Kimi) without legal review — this directly affects Orochi's [[Architecture Overview|PHI edge]] design.

## 4. Webhook security

- Validate **`X-Twilio-Signature`** (HMAC-SHA1 over URL + sorted params, base64, keyed on Auth Token). Use `RequestValidator` (Python) / `validateRequest` (Node).
- Enforce TLS with CA-signed certs (Twilio rejects self-signed). Make status callbacks **idempotent** (persist event SIDs; delivery is at-least-once with backoff).

## 5. Bulk / batch outbound

> [!info] Rate limiting
> Calls are throttled by account **Calls-Per-Second (CPS)**; excess is **queued** (`queue_time`), not dropped. Twilio publishes **no universal CPS number** — request yours from Support and ramp via staged load tests.

**Recommended pattern for Orochi's reminder batch:** worker pool + job queue, idempotency keys on call creation, exponential backoff, conservative start (<1 CPS/region), shard across regions/accounts to scale.

## 6. Messaging (SMS reminders)

Programmable SMS is HIPAA-eligible. Use **Messaging Services** for bulk sending / sender pools and STOP handling. *(Endpoint/parameter specifics were an evidence gap in this pass — pull from Twilio Messaging docs before implementing.)*

## 7. HIPAA / BAA / PHI

- Twilio executes a **BAA** for HIPAA-eligible products; you designate which projects/subaccounts are covered. **A signed BAA does not make the app compliant** — shared responsibility.
- Recordings encrypted at rest by default; supports **customer-provided public key** (AES256-GCM + RSA wrapping).
- Confine PHI to BAA projects, enable recording encryption, strict IAM, audit logs, retention/deletion policies.

## 8. AMD, recording, transcription

- **AMD**: `MachineDetection` (`Enable` | `DetectMessageEnd`), `AsyncAmd`, `MachineDetection*` timeouts.
- **Recording**: start/stop/pause/resume via API; dual/single channel; `recordingStatusCallback`.
- **Transcription**: Real-Time Transcriptions / `<Transcription>` + Voice Intelligence (`intelligenceService`). Treat transcripts as **PHI**.

## Evidence gaps

> [!failure] Confirm before building
> - Exact account/region **CPS** limits (ask Twilio Support).
> - Messaging Service endpoint params for bulk SMS.
> - Whether **Media Streams / ConversationRelay** audio is auto-covered by the BAA — confirm with Twilio before sending PHI to third-party LLMs.

## Works cited

Twilio docs: [Voice webhooks](https://www.twilio.com/docs/usage/webhooks/voice-webhooks) · [`<Gather>`](https://www.twilio.com/docs/voice/twiml/gather) · [`<Connect>`](https://www.twilio.com/docs/voice/twiml/connect) · [`<Stream>`](https://www.twilio.com/docs/voice/twiml/stream) · [Call resource](https://www.twilio.com/docs/voice/api/call-resource) · [Media Streams](https://www.twilio.com/docs/voice/media-streams) · [ConversationRelay](https://www.twilio.com/docs/voice/conversationrelay) · [Security](https://www.twilio.com/docs/usage/security) · [AMD](https://www.twilio.com/docs/voice/answering-machine-detection) · [Architecting for HIPAA (PDF)](https://docs-resources.prod.twilio.com/documents/architecting-for-HIPAA.pdf) · [Understanding Twilio BAA](https://www.twilio.com/en-us/blog/understanding-twilio-baa)
