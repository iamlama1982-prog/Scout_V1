"""A fictional incident with actual check results, not canned Scout answers.

Each button reports a result from the fictional shop. The real workflow
records that result, removes the completed guide and selects the next check.
"""
from __future__ import annotations

from src.scout_workflow import completed_checks

DEMO_CASE_TITLE = "DEMO · Checkout API timeouts"
DEMO_OPENING = (
    "Fictional shop: some customers cannot pay because checkout takes too long. "
    "Our checkout API is returning intermittent 504 Gateway Timeout errors. "
    "We know the symptom, not the cause. What should we check first?"
)

# These are simulated observations, as if the incident team had checked its
# own dashboards and logs. Scout never executes the commands or a rollback.
DEMO_STEPS = [
    {
        "id": "PB-TIMELINE-01",
        "label": "1. Complete the timeline check",
        "question": "A new version went live at 09:00. Orders first failed at 09:15. What does the timing tell us?",
        "finding": (
            "FICTIONAL CHECK RESULT: All times UTC. Checkout deployment 09:00; "
            "first database waits 09:12; first checkout 504 errors 09:15; "
            "both continued through 09:30. Earlier orders succeeded. "
            "The timing makes the new release a lead, not proof of cause."
        ),
    },
    {
        "id": "PB-DEPENDENCIES-01",
        "label": "2. Check what the failed orders share",
        "question": "Do failed orders and successful orders use the same route through the shop?",
        "finding": (
            "FICTIONAL CHECK RESULT: The team compared the service paths. "
            "Failed and successful checkout requests go through the same gateway, "
            "checkout API and PostgreSQL database. Failed orders wait during the "
            "database write; successful orders complete that write quickly. "
            "PostgreSQL is confirmed as part of this system."
        ),
    },
    {
        "id": "PB-TRACE-01",
        "label": "3. Follow one failed order",
        "question": "If we follow one order, where does it first slow down?",
        "finding": (
            "FICTIONAL CHECK RESULT: A failed checkout at 09:16 UTC "
            "(example request A) spent 29 seconds waiting for the database write; "
            "the gateway returned 504 at 30 seconds. A successful order at "
            "09:17 (example request B) used the same route and completed in "
            "0.4 seconds. The delay begins at the database call."
        ),
    },
    {
        "id": "PB-HTTP-504-01",
        "label": "4. Compare the timeout with a successful order",
        "question": "Was the gateway itself slow, or was it waiting for something else?",
        "finding": (
            "FICTIONAL CHECK RESULT: Gateway logs for request A show the "
            "configured 30-second timeout waiting for the checkout API; "
            "the API trace shows the upstream database call consumed 29 seconds. "
            "Request B used the same gateway and API successfully. The 504 is a "
            "symptom of the delayed upstream response; increasing the timeout "
            "would not explain the database wait."
        ),
    },
    {
        "id": "PB-POSTGRES-01",
        "label": "5. Check why the database is waiting",
        "question": "We know where the order waits. Can we find out what is holding it up?",
        "finding": (
            "FICTIONAL CHECK RESULT: An authorised investigator compared "
            "read-only PostgreSQL session activity with monitoring. During "
            "09:12–09:30 UTC, checkout writes waited on locks held by a "
            "long-running transaction from the new release. Before 09:00, "
            "these waits were absent. This supports a release-related locking "
            "problem as the leading explanation, not a proven root cause."
        ),
    },
]

DEMO_RECOVERY = (
    "FICTIONAL RECOVERY CHECK: The authorised incident team rolled back the "
    "new release at 09:35 UTC; Scout did not execute it. The blocking transaction "
    "ended at 09:36, database waits returned to normal and checkout 504s stopped. "
    "The team checked 20 test orders successfully and monitored the next "
    "30 minutes without recurrence. Checkout recovery is verified within "
    "this fictional scenario. The evidence supports release-related database "
    "locking as the leading cause; the precise code-level cause still needs review."
)
DEMO_REVIEW = (
    "DEMONSTRATION ONLY — simulated recovery evidence reviewed: rollback, "
    "normal database waits, successful test orders and 30 minutes of monitoring. "
    "This supports service recovery within the fictional scenario, not an "
    "independently verified real-world diagnosis."
)


def is_demo_case(case: dict | None) -> bool:
    """Only clearly marked demonstration cases get presenter shortcuts."""
    return bool(case and str(case.get("title", "")).startswith("DEMO · "))


def next_demo_step(notes: list[dict]) -> dict | None:
    """Find the first unfinished check from the saved case, not a click counter."""
    done = completed_checks(notes)
    for step in DEMO_STEPS:
        if step["id"] not in done:
            return step
    return None
