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

    # Simulator — run an inbound call that snaps 10:37 -> 11:00
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

    browser.close()
    print("done")
