"""Readable, complete case transcript for a single local Scout investigation.

The database remains the source of truth. This is a presentation/export view
only: the history, stored source snapshots and original text are not altered.
"""

from __future__ import annotations


def format_case_log(
    case: dict, messages: list[dict], notes: list[dict],
    reviews: list[dict],
) -> str:
    """Include every message and human review, with IDs and timestamps."""
    lines = [
        "SCOUT — COMPLETE INVESTIGATION LOG",
        "=" * 44,
        f"Case title: {case.get('title', '')}",
        f"Unique case ID: {case.get('id', '')}",
        f"Status: {case.get('status', '')}",
        f"Created (UTC): {case.get('created_at', '')}",
        f"Last updated (UTC): {case.get('updated_at', '')}",
        "",
        "CONVERSATION — FULL HISTORY",
        "-" * 44,
    ]

    if not messages:
        lines.append("(No saved messages.)")

    for item in messages:
        role = "SCOUT" if item.get("role") == "assistant" else "INVESTIGATOR"
        lines.extend([
            "",
            f"[{item.get('created_at', '')}] {role} "
            f"(message ID {item.get('id', '')})",
            str(item.get("content", "")),
        ])
        evidence = item.get("evidence") or {}

        if evidence.get("model_draft"):
            lines.extend([
                "",
                "OPTIONAL AI INTERPRETATION (UNVERIFIED):",
                str(evidence["model_draft"]),
            ])
            ai_refs = evidence.get("model_draft_cited_ids") or []
            if ai_refs:
                lines.append("AI citation IDs: " + ", ".join(map(str, ai_refs)))

        incidents = evidence.get("incidents") or []
        if incidents:
            lines.append("RETRIEVED PUBLISHED INCIDENTS (SEARCH LEADS):")
            for source in incidents:
                lines.append(
                    "- " + str(source.get("doc_id", "")) + " | "
                    + str(source.get("vendor", "")) + " | "
                    + str(source.get("title", "")) + " | "
                    + str(source.get("source_url", ""))
                )

        guides = evidence.get("guides") or []
        if guides:
            lines.append("RETRIEVED TECHNICAL REFERENCES:")
            for guide in guides:
                lines.append(
                    "- " + str(guide.get("kb_id", "")) + " | "
                    + str(guide.get("title", "")) + " | "
                    + str(guide.get("url", ""))
                )

        playbooks = evidence.get("playbooks") or []
        if playbooks:
            lines.append("CHECKED INVESTIGATION GUIDES PRESENTED:")
            for playbook in playbooks:
                lines.append(
                    "- " + str(playbook.get("id", "")) + " | "
                    + str(playbook.get("title", ""))
                )
                for step in playbook.get("steps") or []:
                    if isinstance(step, dict):
                        lines.append("    " + str(step.get("instruction", "")))
                        if step.get("command"):
                            lines.append("    Command: " + str(step["command"]))

        notice = evidence.get("initial_verification") or {}
        if notice:
            lines.extend([
                "AUTOMATED HUMAN-CHECK NOTICE (NOT A REVIEW):",
                "Reason: " + str(notice.get("reason", "")),
                "Suggested check: " + str(notice.get("human_check", "")),
            ])

    lines.extend(["", "HUMAN VERIFICATION REVIEWS — COMPLETE HISTORY", "-" * 44])
    if not reviews:
        lines.append("(No human verification reviews recorded.)")
    for review in reviews:
        lines.extend([
            "",
            f"[{review.get('created_at', '')}] Review ID {review.get('id', '')}"
            f" · Reply message ID {review.get('message_id', '')}",
            f"Target: {review.get('target', '')}",
            f"Outcome: {review.get('outcome', '')}",
            "What the person checked: " + str(review.get("detail", "")),
        ])

    lines.extend(["", "CASE NOTES — COMPLETE HISTORY", "-" * 44])
    if not notes:
        lines.append("(No saved case notes.)")
    for note in notes:
        lines.extend([
            "",
            f"[{note.get('created_at', '')}] Note ID {note.get('id', '')}"
            f" · Type: {note.get('kind', '')}",
            str(note.get("content", "")),
        ])

    lines.extend([
        "",
        "IMPORTANT:",
        "Source IDs and suggested steps do not verify a live root cause.",
        "Human reviews cover only the specific finding described.",
        "This readable log may omit detailed metadata retained in the JSON export.",
        "",
    ])
    return "\n".join(lines)
