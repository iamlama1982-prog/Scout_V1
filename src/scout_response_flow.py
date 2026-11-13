"""First useful Scout reply without waiting for model inference.

The local retrieval, reference cards and reviewed playbook catalogue already
exist before Llama generates anything. Keep this first response deterministic
and source-linked. AI interpretation may be requested separately.
"""

from __future__ import annotations

from src.incident_assistant import evidence_only_answer
from src.scout_playbooks import guide_led_answer


def first_useful_reply(
    incidents: list[dict],
    guides: list[dict],
    checked_playbooks: list[dict],
    reported_text: str,
) -> dict:
    """Prepare a safe first reply; no LLM, remote API or case write involved."""
    if checked_playbooks:
        text = guide_led_answer(checked_playbooks, reported_text)
        kind = "reviewed investigation plan"
    else:
        text = evidence_only_answer(incidents)
        if incidents:
            text += "\n\n**Closest published reports:**"
            for item in incidents[:3]:
                vendor = str(item.get("vendor", "Unknown vendor"))
                title = str(item.get("title", "Untitled incident"))
                started = str(item.get("started_at", ""))
                url = str(item.get("source_url", ""))
                display_title = f"{vendor} — {title}"
                if url.startswith(("https://", "http://")):
                    display_title = f"[{display_title}]({url})"
                text += f"\n- {display_title}"
                if started:
                    text += f" (reported {started})"
        if guides:
            text += "\n\nRelated technical references appear in the evidence panel."
        kind = "source retrieval only"

    return {
        "answer": text,
        "cited_ids": [],
        "model": kind,
        "seconds": 0.0,
        "tokens": 0,
    }
