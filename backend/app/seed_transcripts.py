"""Synthetic call transcripts + precomputed "AI judgment" annotations for the
Transcripts demo feature. All judgments are hardcoded/mocked — no LLM calls —
matching the rest of the codebase's offline-deterministic demo-data pattern.
"""

import time

from . import db

# Spread seeded calls across the past two weeks at varied times of day instead
# of all landing on the same started_at/ended_at (db._now() is real wall-clock
# time, so a tight seeding loop would otherwise stamp every call identically).
_SPREAD_SECONDS = 14 * 24 * 3600
_DAY_SECONDS = 24 * 3600


def _call(index, total, patient_name, phone, direction, status, transcript, judgment):
    patient = db.create_or_get_patient(phone, patient_name)

    now = int(time.time())
    # Deterministic pseudo-random offsets (no randomness dependency) so the
    # same seed script always produces the same spread across runs.
    day_offset = (index * 2654435761) % _SPREAD_SECONDS
    time_of_day = (index * 40503) % _DAY_SECONDS
    started_at = now - _SPREAD_SECONDS + day_offset - (day_offset % _DAY_SECONDS) + time_of_day
    duration = 90 + ((index * 37) % 600)  # 1.5–11.5 min, varied per call
    ended_at = started_at + duration

    call = db.create_call(
        patient_uuid=patient["patient_uuid"],
        direction=direction,
        status=status,
        transcript=transcript,
        judgment=judgment,
        started_at=str(started_at),
    )
    db.update_call(call["call_uuid"], ended=True, ended_at=str(ended_at))
    return call


def seed_transcripts():
    """Idempotent-ish: only seeds if no calls exist yet."""
    if db.list_calls():
        return

    CALLS = [
        # 1. Friendly booking, clean
        dict(
            patient_name="Maria Alvarez", phone="+15551230001", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Hi, I'd like to book a cleaning."},
                {"role": "agent", "text": "Of course! I can get you in this Thursday at 2pm with Dr. Kim, does that work?"},
                {"role": "caller", "text": "Thursday at 2 works great."},
                {"role": "agent", "text": "Perfect, you're all set for Thursday at 2pm. We'll send a reminder text the day before."},
                {"role": "caller", "text": "Thank you!"},
            ],
            judgment=dict(
                receptionist_coaching=["Offered a concrete time slot immediately — good practice."],
                business_owner_insights=["Caller booked on first offered slot; no friction."],
                compliance_flags=[],
                quality_score=5,
                booked=True,
            ),
        ),
        # 2. Reschedule, efficient tone
        dict(
            patient_name="James Ortiz", phone="+15551230002", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I need to move my appointment next week."},
                {"role": "agent", "text": "Sure, what day works better?"},
                {"role": "caller", "text": "Friday afternoon if possible."},
                {"role": "agent", "text": "I have 3:30pm Friday with Dr. Patel."},
                {"role": "caller", "text": "That's fine."},
                {"role": "agent", "text": "Done, rescheduled to Friday 3:30pm."},
            ],
            judgment=dict(
                receptionist_coaching=["Efficient, but could confirm reason for reschedule to spot patterns."],
                business_owner_insights=["Reschedules trending toward Friday afternoons this month."],
                compliance_flags=[],
                quality_score=4,
                booked=True,
            ),
        ),
        # 3. Cancellation, no save attempt (missed upsell/retention)
        dict(
            patient_name="Linda Chen", phone="+15551230003", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I need to cancel my appointment on Tuesday."},
                {"role": "agent", "text": "Okay, I've cancelled that for you."},
                {"role": "caller", "text": "Thanks, bye."},
            ],
            judgment=dict(
                receptionist_coaching=[
                    "No attempt to ask the reason for cancellation or offer to reschedule.",
                    "Missed opportunity to retain the patient — consider a soft rebooking prompt.",
                ],
                business_owner_insights=["Cancellation processed with zero retention effort — potential lost revenue."],
                compliance_flags=[],
                quality_score=2,
                booked=False,
            ),
        ),
        # 4. Insurance question, thorough
        dict(
            patient_name="Robert Nguyen", phone="+15551230004", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Do you take Delta Dental?"},
                {"role": "agent", "text": "Yes we do! We're in-network with Delta Dental PPO. Would you like to book a new patient exam?"},
                {"role": "caller", "text": "Yes please, I'm a new patient."},
                {"role": "agent", "text": "Great, I have Monday 10am open — please note your specific plan coverage may vary and we'll verify benefits before your visit."},
                {"role": "caller", "text": "Sounds good."},
            ],
            judgment=dict(
                receptionist_coaching=["Excellent — proactively disclosed that coverage may vary, and pivoted to booking."],
                business_owner_insights=["Insurance questions convert well when paired with an immediate booking offer."],
                compliance_flags=[],
                quality_score=5,
                booked=True,
            ),
        ),
        # 5. Emergency call, urgent handling
        dict(
            patient_name="Sofia Torres", phone="+15551230005", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I'm in a lot of pain, I think I cracked a tooth!"},
                {"role": "agent", "text": "I'm sorry to hear that. We can see you today — can you come in at 1pm?"},
                {"role": "caller", "text": "Yes, thank you so much."},
                {"role": "agent", "text": "We'll have Dr. Kim ready for you. Please head straight to the front desk when you arrive."},
            ],
            judgment=dict(
                receptionist_coaching=["Strong empathy and fast same-day slot — model example for emergency calls."],
                business_owner_insights=["Emergency slots being filled same-day; consider reserving 1 emergency slot/day."],
                compliance_flags=[],
                quality_score=5,
                booked=True,
            ),
        ),
        # 6. Hours question, curt
        dict(
            patient_name="David Kim", phone="+15551230006", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "What time do you close today?"},
                {"role": "agent", "text": "5pm."},
                {"role": "caller", "text": "Okay thanks."},
            ],
            judgment=dict(
                receptionist_coaching=["Answer was accurate but curt — a follow-up offer (e.g. 'anything I can help book?') was missed."],
                business_owner_insights=["Simple hours questions rarely convert without a proactive booking offer."],
                compliance_flags=[],
                quality_score=3,
                booked=False,
            ),
        ),
        # 7. Frustrated caller, handled well
        dict(
            patient_name="Angela Brooks", phone="+15551230007", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "This is the third time I've called about my bill and no one has fixed it!"},
                {"role": "agent", "text": "I completely understand your frustration, I'm really sorry this has dragged on. Let me pull up your account right now and get this resolved."},
                {"role": "caller", "text": "Okay, thank you, I appreciate that."},
                {"role": "agent", "text": "I see the duplicate charge — I'm issuing a refund today and escalating to our billing lead so it doesn't happen again."},
                {"role": "caller", "text": "Thank you, that's all I wanted."},
            ],
            judgment=dict(
                receptionist_coaching=["De-escalated well with empathy before problem-solving — textbook recovery."],
                business_owner_insights=["Repeat billing complaint (3rd call) — signals a billing process gap worth auditing."],
                compliance_flags=[],
                quality_score=5,
                booked=False,
            ),
        ),
        # 8. Missing insurance disclaimer (compliance flag)
        dict(
            patient_name="Michael Reyes", phone="+15551230008", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Do you accept Cigna?"},
                {"role": "agent", "text": "Yep, we take Cigna. Want to book?"},
                {"role": "caller", "text": "Sure, next Tuesday."},
                {"role": "agent", "text": "You're booked for Tuesday at 11am."},
            ],
            judgment=dict(
                receptionist_coaching=["Confirmed insurance too casually — should state that coverage/benefits are verified prior to the visit."],
                business_owner_insights=["Fast booking, but risks patient surprise billing without a coverage disclaimer."],
                compliance_flags=["Missing insurance coverage disclaimer"],
                quality_score=3,
                booked=True,
            ),
        ),
        # 9. Missing consent language (compliance flag)
        dict(
            patient_name="Patricia Lee", phone="+15551230009", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I want to schedule my daughter for a cleaning."},
                {"role": "agent", "text": "Sure, what's her name and age?"},
                {"role": "caller", "text": "Emma, she's 9."},
                {"role": "agent", "text": "Great, I have Wednesday at 4pm."},
                {"role": "caller", "text": "That works."},
            ],
            judgment=dict(
                receptionist_coaching=["For a minor patient, should have confirmed guardian consent-on-file / treatment consent process."],
                business_owner_insights=["Pediatric bookings are increasing — consider a dedicated pediatric intake script."],
                compliance_flags=["Missing guardian consent confirmation for minor patient"],
                quality_score=3,
                booked=True,
            ),
        ),
        # 10. Outbound reminder call, efficient
        dict(
            patient_name="Kevin Walsh", phone="+15551230010", direction="outbound",
            status="completed",
            transcript=[
                {"role": "agent", "text": "Hi, this is a reminder about your appointment tomorrow at 9am."},
                {"role": "caller", "text": "Oh right, yes I'll be there."},
                {"role": "agent", "text": "Great, see you then!"},
            ],
            judgment=dict(
                receptionist_coaching=["Clean, standard reminder call."],
                business_owner_insights=["Reminder calls continue to reduce no-shows for early bookings."],
                compliance_flags=[],
                quality_score=4,
                booked=True,
            ),
        ),
        # 11. New patient booking, friendly tone
        dict(
            patient_name="Emily Foster", phone="+15551230011", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Hi! I just moved here and need a new dentist."},
                {"role": "agent", "text": "Welcome to the area! I'd love to get you set up — are mornings or afternoons better for you?"},
                {"role": "caller", "text": "Mornings, ideally."},
                {"role": "agent", "text": "I have next Monday at 9am for a new patient exam and cleaning."},
                {"role": "caller", "text": "Perfect, book me in."},
            ],
            judgment=dict(
                receptionist_coaching=["Warm welcome plus preference-based scheduling — great new-patient experience."],
                business_owner_insights=["New patient calls converting well when receptionist leads with a welcoming tone."],
                compliance_flags=[],
                quality_score=5,
                booked=True,
            ),
        ),
        # 12. Payment plan question
        dict(
            patient_name="Brian Cole", phone="+15551230012", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Do you offer payment plans for a root canal?"},
                {"role": "agent", "text": "Yes, we offer CareCredit financing and in-house payment plans. Want me to schedule a consult to go over options?"},
                {"role": "caller", "text": "Yes please."},
                {"role": "agent", "text": "Booked you for Thursday at 3pm with our treatment coordinator."},
            ],
            judgment=dict(
                receptionist_coaching=["Good — offered concrete financing options rather than a vague answer."],
                business_owner_insights=["Financing-aware callers convert at a higher rate when routed to treatment coordinator."],
                compliance_flags=[],
                quality_score=4,
                booked=True,
            ),
        ),
        # 13. Rude/dismissive receptionist (bad example)
        dict(
            patient_name="Nancy Diaz", phone="+15551230013", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I have a question about my last visit's charges."},
                {"role": "agent", "text": "You'll have to call billing separately, we don't handle that here."},
                {"role": "caller", "text": "Oh, okay... can I get that number?"},
                {"role": "agent", "text": "It's on your statement."},
            ],
            judgment=dict(
                receptionist_coaching=[
                    "Tone came across dismissive — should offer to look up the number rather than deflect.",
                    "Consider scripting a warmer handoff for billing questions.",
                ],
                business_owner_insights=["Billing handoffs are a recurring friction point across multiple calls."],
                compliance_flags=[],
                quality_score=1,
                booked=False,
            ),
        ),
        # 14. Cancellation with reschedule save
        dict(
            patient_name="Tyler Brooks", phone="+15551230014", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I need to cancel Friday's appointment, something came up."},
                {"role": "agent", "text": "No problem — would you like to go ahead and pick a new date now so you don't lose your spot in the schedule?"},
                {"role": "caller", "text": "Sure, how about the following Friday?"},
                {"role": "agent", "text": "Got it, moved you to next Friday at the same time."},
            ],
            judgment=dict(
                receptionist_coaching=["Great retention save — immediately offered a rebooking instead of just cancelling."],
                business_owner_insights=["Proactive rebooking offers are recovering ~1 in 3 cancellation calls this month."],
                compliance_flags=[],
                quality_score=5,
                booked=True,
            ),
        ),
        # 15. Wrong info given (quality issue, no compliance flag)
        dict(
            patient_name="Rachel Adams", phone="+15551230015", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Are you open on Saturdays?"},
                {"role": "agent", "text": "Yes, 9 to 1 on Saturdays."},
                {"role": "caller", "text": "Great, I'll come by this Saturday."},
            ],
            judgment=dict(
                receptionist_coaching=["Note: office is not actually open Saturdays per current hours — verify info given to callers."],
                business_owner_insights=["Potential incorrect-hours information given; flag for hours-script refresh."],
                compliance_flags=[],
                quality_score=2,
                booked=False,
            ),
        ),
        # 16. Insurance question, missing disclaimer again
        dict(
            patient_name="George Patel", phone="+15551230016", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Is Aetna in network?"},
                {"role": "agent", "text": "Yes."},
                {"role": "caller", "text": "Okay, can I book a cleaning?"},
                {"role": "agent", "text": "Sure, Tuesday 2pm works."},
            ],
            judgment=dict(
                receptionist_coaching=["One-word insurance confirmation — should clarify plan tier and mention benefits verification."],
                business_owner_insights=["Insurance answers remain inconsistent across staff — candidate for a standard script."],
                compliance_flags=["Missing insurance coverage disclaimer"],
                quality_score=3,
                booked=True,
            ),
        ),
        # 17. Waitlist request
        dict(
            patient_name="Hannah Scott", phone="+15551230017", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Nothing this week works for me, can you put me on a waitlist for a cancellation?"},
                {"role": "agent", "text": "Absolutely, I'll add you to the waitlist and call you the moment something opens up."},
                {"role": "caller", "text": "Thank you!"},
            ],
            judgment=dict(
                receptionist_coaching=["Handled waitlist request smoothly and set clear expectations."],
                business_owner_insights=["Waitlist requests are an underused signal of near-term demand."],
                compliance_flags=[],
                quality_score=4,
                booked=False,
            ),
        ),
        # 18. Emergency mishandled (long hold, slow)
        dict(
            patient_name="Oscar Jimenez", phone="+15551230018", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "My tooth is throbbing, I need to be seen today."},
                {"role": "agent", "text": "Let me check... we don't have anything until next week I'm afraid."},
                {"role": "caller", "text": "That's a long time to be in pain."},
                {"role": "agent", "text": "I understand, that's the soonest we have."},
            ],
            judgment=dict(
                receptionist_coaching=[
                    "Did not offer any emergency triage options (e.g. same-day squeeze-in, referral, pain management advice).",
                    "Consider escalating urgent pain calls to a provider for a callback.",
                ],
                business_owner_insights=["Emergency call turned away — risk of losing patient to a competitor."],
                compliance_flags=[],
                quality_score=1,
                booked=False,
            ),
        ),
        # 19. Efficient reschedule, minor tone flatness
        dict(
            patient_name="Grace Kim", phone="+15551230019", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "Can I push my appointment back an hour?"},
                {"role": "agent", "text": "One hour later, checking... yes, that's available."},
                {"role": "caller", "text": "Great, thanks."},
                {"role": "agent", "text": "Updated."},
            ],
            judgment=dict(
                receptionist_coaching=["Efficient and accurate, though a warmer closing ('see you then!') would improve rapport."],
                business_owner_insights=["Minor time-shift reschedules are quick, low-risk calls."],
                compliance_flags=[],
                quality_score=4,
                booked=True,
            ),
        ),
        # 20. Insurance + consent both missing (worse compliance example)
        dict(
            patient_name="Ethan Brooks", phone="+15551230020", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I want to book my son in for a filling, he's 7. Do you take Delta Dental?"},
                {"role": "agent", "text": "Yep we take that. I have Friday at 10am."},
                {"role": "caller", "text": "Okay, book it."},
                {"role": "agent", "text": "Done."},
            ],
            judgment=dict(
                receptionist_coaching=[
                    "No coverage disclaimer given for insurance.",
                    "No confirmation of guardian consent for a minor patient's procedure.",
                ],
                business_owner_insights=["Pediatric procedure calls need a stricter checklist — two compliance gaps in one call."],
                compliance_flags=["Missing insurance coverage disclaimer", "Missing guardian consent confirmation for minor patient"],
                quality_score=2,
                booked=True,
            ),
        ),
        # 21. Simple hours question, handled well with upsell
        dict(
            patient_name="Olivia Martin", phone="+15551230021", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "What are your hours on Wednesdays?"},
                {"role": "agent", "text": "We're open 8 to 6 on Wednesdays. Are you looking to schedule something?"},
                {"role": "caller", "text": "Actually yes, a cleaning."},
                {"role": "agent", "text": "I have 10am this Wednesday."},
                {"role": "caller", "text": "Book it please."},
            ],
            judgment=dict(
                receptionist_coaching=["Turned a simple hours question into a booking by proactively asking — great technique."],
                business_owner_insights=["Proactive booking prompts on informational calls are converting well."],
                compliance_flags=[],
                quality_score=5,
                booked=True,
            ),
        ),
        # 22. Long hold / apology, eventual booking
        dict(
            patient_name="Diego Ramirez", phone="+15551230022", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I've been on hold for ten minutes."},
                {"role": "agent", "text": "I'm so sorry about the wait — thank you for your patience. How can I help?"},
                {"role": "caller", "text": "I need a cleaning appointment."},
                {"role": "agent", "text": "I can get you in Monday at 1pm."},
                {"role": "caller", "text": "Fine, I'll take it."},
            ],
            judgment=dict(
                receptionist_coaching=["Good recovery apology, though the underlying hold-time issue should be addressed operationally."],
                business_owner_insights=["Long hold times are surfacing in caller complaints — consider staffing review at peak hours."],
                compliance_flags=[],
                quality_score=3,
                booked=True,
            ),
        ),
        # 23. Outbound campaign call, declined
        dict(
            patient_name="Samuel Green", phone="+15551230023", direction="outbound",
            status="completed",
            transcript=[
                {"role": "agent", "text": "Hi, we noticed it's been a while since your last cleaning — want to grab a spot this month?"},
                {"role": "caller", "text": "Not right now, maybe later."},
                {"role": "agent", "text": "No problem, I'll follow up in a few weeks. Have a great day!"},
            ],
            judgment=dict(
                receptionist_coaching=["Respected the 'no' without being pushy, and set a clear follow-up plan."],
                business_owner_insights=["Recall campaign calls are surfacing soft declines — good candidates for a follow-up text touch."],
                compliance_flags=[],
                quality_score=4,
                booked=False,
            ),
        ),
        # 24. Frustrated caller, handled poorly (contrast with #7)
        dict(
            patient_name="Vanessa Ruiz", phone="+15551230024", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "You guys charged me twice, this is ridiculous."},
                {"role": "agent", "text": "I don't see anything wrong on my end."},
                {"role": "caller", "text": "Well I have two charges on my statement."},
                {"role": "agent", "text": "You'd need to call your bank about that."},
            ],
            judgment=dict(
                receptionist_coaching=[
                    "Dismissed the complaint without investigating — should have pulled up the account and offered to check.",
                    "Deflecting to the bank without verifying first risks losing patient trust.",
                ],
                business_owner_insights=["Second billing-dispute call this batch handled poorly — recommend billing dispute training."],
                compliance_flags=[],
                quality_score=1,
                booked=False,
            ),
        ),
        # 25. Clean insurance + consent call (positive contrast to #20)
        dict(
            patient_name="Isabella Ward", phone="+15551230025", direction="inbound",
            status="completed",
            transcript=[
                {"role": "caller", "text": "I'd like to book my daughter, she's 10, for a checkup. We have MetLife."},
                {"role": "agent", "text": "Great — we're in-network with MetLife, though I'll note your exact benefits will be verified before the visit. Also, since she's a minor, we'll need a guardian's consent on file, which we can get signed at check-in."},
                {"role": "caller", "text": "Perfect, that all makes sense."},
                {"role": "agent", "text": "I have Thursday at 4:30pm for her checkup."},
                {"role": "caller", "text": "Book it, thank you."},
            ],
            judgment=dict(
                receptionist_coaching=["Model call — proactively covered both insurance disclaimer and minor-consent process."],
                business_owner_insights=["This call is a great training example for pediatric + insurance intake."],
                compliance_flags=[],
                quality_score=5,
                booked=True,
            ),
        ),
    ]

    for i, c in enumerate(CALLS):
        _call(
            i, len(CALLS),
            c["patient_name"], c["phone"], c["direction"], c["status"],
            c["transcript"], c["judgment"],
        )
