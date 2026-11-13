"""Build a short case-aware search and prompt context for Scout.

This is memory through retrieved records, not model training.
Older assistant answers are labelled as earlier suggestions, not evidence.
"""

from __future__ import annotations

from typing import Any

from src.scout_verification import initial_verification_notice


def retrieval_query(messages: list[dict], notes: list[dict], latest: str) -> str:
    """Find references using both the original symptoms and the new detail.

    A follow-up such as 'We're using PostgreSQL' is not useful for incident
    retrieval by itself. The first description supplies the missing context.
    """
    user_messages = [
        str(item["content"]).strip()
        for item in messages if item.get("role") == "user"
    ]
    starting_problem = user_messages[0] if user_messages else latest
    facts = [
        str(item["content"]).strip()
        for item in notes if item.get("kind") == "confirmed_fact"
    ]
    parts = [starting_problem[:850], latest.strip()[:650]]
    parts.extend(fact[:200] for fact in facts[-4:])
    # Remove a duplicate when the opening question is also the current one.
    unique = list(dict.fromkeys(part for part in parts if part))
    return "\n".join(unique)[:2100]


def case_context_for_model(messages: list[dict], notes: list[dict]) -> str:
    """Summarise the *recorded* case without silently approving Scout's guesses.

    We keep the original words rather than asking another LLM to create a
    potentially misleading summary. The latest few exchanges are enough for
    a sensible follow-up; the whole record remains saved in SQLite.
    """
    parts = [
        "This is the SAME investigation, not a new incident. Respond to the "
        "latest user message using the earlier case details. Do not ask them "
        "to repeat information already recorded.",
        "Information supplied by the user is reported information, not "
        "independently validated logs or proof of a root cause.",
    ]
    if notes:
        labels = {
            "confirmed_fact": "User-marked confirmed fact",
            "observation": "Recorded observation",
            "hypothesis": "Hypothesis to test (UNVERIFIED)",
            "verified_resolution": "Human-marked verified resolution",
        }
        parts.append("CASE NOTES (labels chosen by the user):")
        for note in notes[-14:]:
            kind = str(note.get("kind", "observation"))
            label = labels.get(kind, "Unclassified note")
            parts.append(f"- {label}: {str(note.get('content', ''))[:300]}")

    if messages:
        parts.append("RECENT CONVERSATION (not independent verification):")
        for item in messages[-10:]:
            role = item.get("role")
            if role == "user":
                label = "User reported"
            elif role == "assistant":
                label = "Scout previously suggested — not verified"
            else:
                continue
            parts.append(f"- {label}: {str(item.get('content', ''))[:850]}")
    return "\n".join(parts)[-7500:]


def source_snapshot(
    incidents: list[dict],
    guides: list[dict],
    answer: dict,
    baseline: list[dict] | None = None,
    supporting_incidents: list[dict] | None = None,
    playbooks: list[dict] | None = None,
) -> dict[str, Any]:
    """Save small source cards so references remain available after restart."""

    def incident_card(item: dict) -> dict:
        return {
            "doc_id": str(item.get("doc_id", "")),
            "title": str(item.get("title", "")),
            "vendor": str(item.get("vendor", "")),
            "source_url": str(item.get("source_url", "")),
            "started_at": str(item.get("started_at", "")),
            "impact": str(item.get("impact", "")),
            "status": str(item.get("status", "")),
            "components": str(item.get("components", "")),
        }

    draft_evidence = {
        "incidents": incidents,
        "guides": guides,
        "supporting_incident_ids": [
            item.get("doc_id") for item in (supporting_incidents or [])
        ],
        "playbooks": playbooks or [],
    }
    return {
        "initial_verification": initial_verification_notice(draft_evidence),
        "cited_ids": list(answer.get("cited_ids", [])),
        # The original generated answer is kept for transparent evaluation.
        # It is never presented as the checked investigation plan.
        "model_draft": str(answer.get("model_draft", "")),
        "model_draft_cited_ids": list(answer.get("model_draft_cited_ids", [])),
        "incidents": [incident_card(item) for item in incidents],
        "baseline": [incident_card(item) for item in (baseline or [])],
        "supporting_incident_ids": [
            item["doc_id"] for item in (supporting_incidents or [])
        ],
        "guides": [
            {
                "kb_id": str(item.get("kb_id", "")),
                "title": str(item.get("title", "")),
                "publisher": str(item.get("publisher", "")),
                "url": str(item.get("url", "")),
                "summary": str(item.get("summary", "")),
                "applies_to": str(item.get("applies_to", "")),
                "diagnostic_checks": [
                    str(check) for check in item.get("diagnostic_checks", [])
                ],
                "reviewed_on": str(item.get("reviewed_on", "")),
            }
            for item in guides
        ],
        # Snapshot the exact steps displayed for this answer. Old investigations
        # still show the same checked instructions after a catalogue update.
        "playbooks": [dict(item) for item in (playbooks or [])],
        "model": str(answer.get("model", "")),
        "seconds": float(answer.get("seconds", 0)),
        "tokens": int(answer.get("tokens", 0)),
    }
