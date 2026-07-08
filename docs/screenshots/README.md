# Orochi — UI screenshots

Captured from the running app (`http://localhost:5173`) with seeded demo data.

| Screen | Preview |
|--------|---------|
| **Login** | ![Login](01-login.png) |
| **Dashboard** — activity stats + recent calls | ![Dashboard](02-dashboard.png) |
| **Schedule** — weekly 45-min availability grid | ![Schedule](03-schedule.png) |
| **Simulator** — inbound call snapped to nearest open slot | ![Simulator](04-simulator.png) |
| **Appointments** — list + inline status changes | ![Appointments](05-appointments.png) |
| **Simulator (Emergency)** — triage + escalation, sentiment, summary | ![Emergency](06-simulator-emergency.png) |
| **Waitlist** — ASAP list + one-click cancellation backfill | ![Waitlist](07-waitlist.png) |
| **Messages** — mock Twilio SMS/email + two-way confirmation | ![Messages](08-communications.png) |
| **Campaigns** — recall / reactivation / missed-call recovery | ![Campaigns](09-campaigns.png) |
| **Insights** — call analytics, booking conversion, no-show risk | ![Insights](10-insights.png) |
| **Providers** — providers + procedure types with durations | ![Providers](11-providers.png) |
| **Escalations** — emergency queue + patient call-pop | ![Escalations](12-escalations.png) |
| **Reminders** — configurable cadence + due-job runner | ![Reminders](13-reminders.png) |
| **Insurance** — mock eligibility verification | ![Insurance](14-insurance.png) |
| **Guided demo** — scripted product walkthrough | ![Guided demo](15-guided-demo.png) |
| **Dark mode** — theme-aware dashboard | ![Dark mode](16-dark-dashboard.png) |

> Regenerate with `python3 scripts/screenshots.py` (drives headless Chrome via Playwright against the running dev servers).
