"""Capture UI screenshots by driving the running dev server via headless Chrome.

Prereqs: the app running locally (backend on :8000, frontend on :5173) and
Playwright with a Chrome channel available. Run from the repo root:
    python3 scripts/screenshots.py
"""

import os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)
BASE = "http://localhost:5173"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()

    # Login page (unauthenticated)
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.wait_for_timeout(600)
    page.screenshot(path=f"{OUT}/01-login.png")

    # Sign in (fields are pre-filled with seeded creds)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"{BASE}/", timeout=8000)
    page.wait_for_timeout(800)
    page.screenshot(path=f"{OUT}/02-dashboard.png")

    # Schedule
    page.goto(f"{BASE}/schedule", wait_until="networkidle")
    page.wait_for_timeout(700)
    page.screenshot(path=f"{OUT}/03-schedule.png", full_page=True)

    # Simulator — run an inbound booking that snaps to the nearest open slot
    page.goto(f"{BASE}/simulator", wait_until="networkidle")
    page.wait_for_timeout(400)
    page.get_by_placeholder("What does the caller want?").fill(
        "Hi, I'd like an appointment next Tuesday around 10:37am please."
    )
    page.get_by_role("button", name="Simulate inbound call").click()
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{OUT}/04-simulator.png", full_page=True)

    # Appointments
    page.goto(f"{BASE}/appointments", wait_until="networkidle")
    page.wait_for_timeout(700)
    page.screenshot(path=f"{OUT}/05-appointments.png", full_page=True)

    # Simulator — emergency triage/escalation
    page.goto(f"{BASE}/simulator", wait_until="networkidle")
    page.wait_for_timeout(400)
    page.get_by_placeholder("What does the caller want?").fill(
        "I knocked out a tooth and it won't stop bleeding, I'm in severe pain!"
    )
    page.get_by_role("button", name="Simulate inbound call").click()
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{OUT}/06-simulator-emergency.png", full_page=True)

    # New feature pages
    for slug, name in [
        ("waitlist", "07-waitlist"),
        ("communications", "08-communications"),
        ("campaigns", "09-campaigns"),
        ("insights", "10-insights"),
        ("catalog", "11-providers"),
        ("escalations", "12-escalations"),
        ("reminders", "13-reminders"),
        ("insurance", "14-insurance"),
        ("demo", "15-guided-demo"),
    ]:
        page.goto(f"{BASE}/{slug}", wait_until="networkidle")
        page.wait_for_timeout(800)
        page.screenshot(path=f"{OUT}/{name}.png", full_page=True)

    # Dark mode — set the persisted theme, then capture the dashboard
    dark = ctx.new_page()
    dark.add_init_script("localStorage.setItem('orochi-theme','dark')")
    dark.goto(f"{BASE}/", wait_until="networkidle")
    dark.wait_for_timeout(900)
    dark.screenshot(path=f"{OUT}/16-dark-dashboard.png", full_page=True)

    # Transcripts — batch overview
    page.goto(f"{BASE}/transcripts", wait_until="networkidle")
    page.wait_for_timeout(800)
    page.screenshot(path=f"{OUT}/17-transcripts.png", full_page=True)

    # Transcripts — per-call drill-down (last row = oldest = one of the 25
    # seeded transcripts, not a just-created Simulator test call)
    page.get_by_role("row").nth(-1).click()
    page.wait_for_timeout(600)
    page.screenshot(path=f"{OUT}/18-transcripts-detail.png", full_page=True)

    browser.close()
    print("done")
