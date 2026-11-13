"""Small, checked investigation guides for Scout's clickable actions.

I don't ask the model to invent commands. These playbooks are short, manually
reviewed steps selected using information *the user actually supplied*. Every
official procedure is linked to a reference in our existing technical library.
General investigative methods are labelled as general, not vendor-verified.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.technical_knowledge import load_knowledge

PLAYBOOK_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "investigation_playbooks.json"
ID_FORMAT = re.compile(r"PB-[A-Z0-9-]+\Z")
READ_ONLY_COMMANDS = ("SELECT ", "kubectl describe pod ", "kubectl logs ")
TECHNOLOGY_NEGATIONS = re.compile(
    r"\b(?:not using|don't use|do not use|not running|no|without)\s+"
    r"(?:a\s+)?postgres(?:ql)?\b", re.IGNORECASE,
)


def load_playbooks(path: str | Path = PLAYBOOK_PATH) -> list[dict[str, Any]]:
    """Validate playbooks and check official links against our source catalogue."""
    with Path(path).open(encoding="utf-8") as f:
        payload = json.load(f)
    cards = payload.get("playbooks") if isinstance(payload, dict) else None
    if not isinstance(cards, list) or not cards:
        raise ValueError("The investigation playbook file needs a non-empty playbooks list.")

    approved_sources = {
        row["kb_id"]: (row["url"], row["publisher"])
        for row in load_knowledge().to_dict(orient="records")
    }
    result = []
    seen = set()
    required = {
        "id", "title", "summary", "source_type", "reference_id", "applies_when",
        "steps", "interpretation", "share_back", "reviewed_on",
    }
    for card in cards:
        if not isinstance(card, dict) or not required.issubset(card):
            raise ValueError("A playbook is missing required fields.")
        identifier = card["id"]
        if not isinstance(identifier, str) or not ID_FORMAT.fullmatch(identifier) or identifier in seen:
            raise ValueError(f"Invalid or repeated playbook ID: {identifier}")
        seen.add(identifier)
        for field in ["title", "summary", "applies_when", "share_back", "reviewed_on"]:
            if not isinstance(card[field], str) or not card[field].strip():
                raise ValueError(f"Playbook {identifier} needs a non-empty {field}.")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", card["reviewed_on"]):
            raise ValueError(f"Playbook {identifier} needs a review date.")
        kind = card["source_type"]
        reference_id = card["reference_id"]
        if kind == "official_documentation":
            if reference_id not in approved_sources:
                raise ValueError(f"Playbook {identifier} has an unknown official source.")
            source_url, source_publisher = approved_sources[reference_id]
        elif kind == "general_investigation":
            if reference_id is not None:
                raise ValueError(f"General playbook {identifier} cannot claim an official source.")
            source_url, source_publisher = "", "Original investigation method — not vendor documentation"
        else:
            raise ValueError(f"Unknown source type in {identifier}.")

        instructions = card["steps"]
        if not isinstance(instructions, list) or len(instructions) < 2:
            raise ValueError(f"Playbook {identifier} needs at least two steps.")
        for item in instructions:
            if not isinstance(item, dict) or not isinstance(item.get("instruction"), str) or not item["instruction"].strip():
                raise ValueError(f"Invalid step in {identifier}.")
            command = item.get("command")
            if command is not None:
                if kind != "official_documentation" or not isinstance(command, str):
                    raise ValueError(f"Only documented technical guides can contain commands: {identifier}")
                # This isn't a shell sandbox. The fixed catalogue is reviewed by
                # a human; this guard catches accidental command additions.
                trimmed = command.strip()
                if not trimmed.startswith(READ_ONLY_COMMANDS):
                    raise ValueError(f"Unapproved command in playbook {identifier}.")
                if trimmed.startswith("SELECT "):
                    # SELECT-only query with exactly one terminator. Refuse any
                    # additional SQL statements or obvious database mutations.
                    if trimmed.count(";") != 1 or not trimmed.endswith(";"):
                        raise ValueError(f"Unexpected SQL statements in {identifier}.")
                    if re.search(
                        r"\b(?:INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|"
                        r"GRANT|REVOKE|COPY|CALL|EXECUTE|DO)\b",
                        trimmed, flags=re.IGNORECASE,
                    ):
                        raise ValueError(f"Non-read-only SQL in {identifier}.")
                else:
                    # Fixed read-only kubectl commands. Prevent shell chaining,
                    # substitution and additional commands.
                    if any(token in trimmed for token in (";", "|", "&&", "`", "$(", "\n", "\r")):
                        raise ValueError(f"Unsafe shell content in {identifier}.")
                    if not trimmed.startswith(("kubectl describe pod ", "kubectl logs ")):
                        raise ValueError(f"Unapproved kubectl action in {identifier}.")

        interpretation = card["interpretation"]
        if not isinstance(interpretation, dict) or not all(
            isinstance(interpretation.get(field), str) and interpretation[field].strip()
            for field in ("supports", "weakens", "unknown")
        ):
            raise ValueError(f"Playbook {identifier} needs support, weakness and uncertainty explanations.")
        result.append({
            **card,
            "source_url": source_url,
            "source_publisher": source_publisher,
        })
    return result


def reported_case_text(messages: list[dict], notes: list[dict]) -> str:
    """Use user reports, not the model's previous guesses, to pick playbooks."""
    parts = [str(m.get("content", "")) for m in messages if m.get("role") == "user"]
    parts.extend(
        str(n.get("content", ""))
        for n in notes if n.get("kind") in {"confirmed_fact", "observation"}
    )
    return "\n".join(parts)[-5000:]


def select_playbooks(reported_text: str, catalogue: list[dict], *, max_steps: int = 5) -> list[dict]:
    """Deterministic, conservative choices; never infer a stack from incident titles."""
    if not reported_text.strip() or max_steps < 1:
        return []
    text = reported_text.lower()
    # These are pattern-based rules, not a learned classifier. Each bool
    # tells me whether the user reported a matching technology or symptom.
    # Word boundaries (\b) avoid matching parts of unrelated words.
    postgres = bool(re.search(r"\b(?:postgres|postgresql|pg_stat_activity)\b", text))
    postgres = postgres and not bool(TECHNOLOGY_NEGATIONS.search(text))
    kubernetes = bool(re.search(r"\b(?:kubernetes|k8s|pods?|crashloopbackoff)\b", text))
    restart = bool(re.search(r"\b(?:restart|crash|probe|not ready|unready)\w*\b", text))
    gateway_504 = bool(re.search(r"\b504\b|gateway timeout", text))
    api = bool(re.search(r"\b(?:api|endpoint|gateway|http|upstream)\b", text))
    database = bool(re.search(r"\b(?:database|db|postgres(?:ql)?|sql|connection pool)\b", text))
    checkout = bool(re.search(r"\b(?:checkout|transaction|payment|customer order)\w*\b", text))
    changes = bool(re.search(r"\b(?:deploy|update|change|release|rollout|migration)\w*\b", text))
    multiple_areas = sum((api, database, checkout, kubernetes)) >= 2
    linked = bool(re.search(r"\b(?:connect|relat|link|shared|together|correlat)\w*\b", text))
    ordered = []
    if changes or multiple_areas or linked:
        ordered.append("PB-TIMELINE-01")
    if multiple_areas or linked:
        ordered.append("PB-DEPENDENCIES-01")
    if api or checkout:
        ordered.append("PB-TRACE-01")
    if gateway_504:
        ordered.append("PB-HTTP-504-01")
    if postgres:
        ordered.append("PB-POSTGRES-01")
    if kubernetes and restart:
        ordered.append("PB-K8S-POD-01")
    by_id = {record["id"]: record for record in catalogue}
    return [by_id[key] for key in ordered if key in by_id][:max_steps]


def playbook_prompt_summary(playbooks: list[dict]) -> str:
    """Tell Llama which clickable guides exist, but not let it rewrite commands."""
    if not playbooks:
        return ""
    records = [
        f"- {item['title']} [{item['id']}]: {item['summary']} "
        f"Applies only when: {item['applies_when']}"
        for item in playbooks
    ]
    return (
        "CHECKED, CLICKABLE INVESTIGATION GUIDES AVAILABLE BELOW YOUR REPLY:\n"
        + "\n".join(records)
        + "\nThe interface itself presents these guides IN THE ORDER SHOWN above, "
          "so don't create a second investigation checklist. Refer to the first "
          "guide by its EXACT TITLE, and explain what finding would make it "
          "useful to continue to the next guide. Keep the answer short and "
          "conversational. Do not introduce other technical procedures as though "
          "a checked guide exists for them. The user can expand each guide "
          "for the full steps and their interpretation. Never invent SQL "
          "views, CLI commands, flags or procedures in your answer. "
          "Only the fixed playbook contains runnable examples. "
          "A guide does NOT mean it was executed."
    )



def guide_led_answer(playbooks: list[dict], reported_text: str) -> str:
    """A reliable first-step explanation, built from reviewed guide records.

    Why not use the raw LLM answer here? We tested several stronger prompts
    and the local model still supplied a different, unsupported checklist.
    We therefore use the LLM for separate unverified analysis, while the
    visible *action plan* comes from the checked guide catalogue.

    The text never says that a diagnosis has been confirmed or a check done.
    """
    if not playbooks:
        raise ValueError("A guide-led answer needs at least one reviewed action.")

    first = playbooks[0]
    has_change = bool(
        re.search(
            r"\b(?:deploy|update|release|change|rollout|migration)\w*\b",
            reported_text, re.IGNORECASE,
        )
    )
    has_multiple_symptoms = sum(
        bool(re.search(pattern, reported_text, re.IGNORECASE))
        for pattern in [
            r"\b(?:api|endpoint|gateway|http)\b",
            r"\b(?:database|db|postgres(?:ql)?|sql)\b",
            r"\b(?:checkout|transaction|payment)\w*\b",
            r"\b(?:kubernetes|k8s|pods?)\b",
        ]
    ) >= 2

    if first["id"] == "PB-TIMELINE-01":
        opening = (
            "These symptoms could be connected, but we haven't established a "
            "shared cause yet. "
            if has_multiple_symptoms else
            "The timing of the reported problem is the first thing I'd establish. "
        )
        if has_change:
            opening += (
                "The reported change is worth investigating, but its timing "
                "alone doesn't prove it caused the fault. "
            )
    elif first["id"] == "PB-DEPENDENCIES-01":
        opening = (
            "A shared dependency might explain the reported failures, but "
            "we need evidence from the actual service paths. "
        )
    elif first["id"] == "PB-TRACE-01":
        opening = (
            "I'd find out where one affected request first becomes slow or "
            "fails, rather than assume the gateway or database is responsible. "
        )
    elif first["id"] == "PB-HTTP-504-01":
        opening = (
            "A gateway timeout tells us the gateway didn't receive a timely "
            "upstream response. That doesn't identify which component caused it. "
        )
    elif first["id"] == "PB-POSTGRES-01":
        opening = (
            "Since PostgreSQL is part of the reported environment, checking "
            "session activity can help us test whether waits or connection "
            "pressure are involved. It won't establish the root cause alone. "
        )
    elif first["id"] == "PB-K8S-POD-01":
        opening = (
            "The restart reason and Pod events are the best starting evidence. "
            "A restart after a deployment doesn't automatically make that "
            "deployment the cause. "
        )
    else:
        opening = "I haven't established a root cause from the information provided. "

    title = str(first["title"])
    summary = str(first["summary"])
    share_back = str(first["share_back"])
    total = len(playbooks)

    return (
        opening
        + f"\n\n**I'd start with: {title}.** {summary}\n\n"
        + "Open **View steps** below for the checked procedure and what "
          "different results would mean. "
        + (
            f"The other {total - 1} actions are ordered after it; we can "
            "revisit their priority as you add findings. "
            if total > 1 else
            "We can refine the next action when you have a result. "
        )
        + f"\n\n**What to tell me next:** {share_back}"
        + "\n\n*This is an investigation plan, not a confirmed diagnosis. "
          "No checks have been run by Scout.*"
    )



def checked_plan_response(
    model_response: dict, playbooks: list[dict], reported_text: str,
) -> dict:
    """Keep generated reasoning for evaluation, not as the user's action plan.

    Llama 3.2 repeatedly supplied a conflicting checklist despite stronger
    instructions. The tested plan from the reviewed catalogue therefore owns
    the visible response whenever a relevant playbook is available.
    """
    if not playbooks:
        return model_response
    result = dict(model_response)
    result["model_draft"] = str(model_response.get("answer", ""))
    result["model_draft_cited_ids"] = list(model_response.get("cited_ids", []))
    result["answer"] = guide_led_answer(playbooks, reported_text)
    result["cited_ids"] = []
    return result
