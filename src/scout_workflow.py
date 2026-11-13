"""Run one real source-first Scout turn and save it to the case.

Both the ordinary chat box and the optional presenter examples call this exact
workflow. A demonstration cannot quietly substitute a canned search answer.
"""

from __future__ import annotations

from src.incident_assistant import (
    historical_evidence_for_answer, keyword_search, retrieve,
)
from src.scout_case_store import add_message, add_note, get_messages, get_notes
from src.scout_conversation import retrieval_query, source_snapshot
from src.scout_playbooks import reported_case_text, select_playbooks
from src.scout_response_flow import first_useful_reply
from src.technical_knowledge import retrieve_knowledge


def completed_checks(notes: list[dict]) -> dict[str, str]:
    """Read explicitly completed checks from existing case notes.

    A new clue or a review of advice is not completion. The investigator
    must record a finding against a particular checked guide.
    """
    results = {}
    for note in notes:
        content = str(note.get("content", ""))
        if note.get("kind") != "confirmed_fact" or not content.startswith("Completed check "):
            continue
        heading, separator, finding = content.partition(": ")
        if separator and finding.strip():
            results[heading.removeprefix("Completed check ")] = finding
    return results


def save_investigation_turn(
    case_id: str,
    question: str,
    incident_index,
    knowledge_index,
    playbook_catalogue: list[dict],
    *,
    use_knowledge: bool = True,
    k: int = 5,
    completed_check_id: str | None = None,
) -> dict:
    """Save user input, retrieve live source leads and persist the checked reply.

    Returns the saved response metadata. Does not call an LLM.
    """
    question = question.strip()
    if not question:
        raise ValueError("A case update cannot be empty.")
    if incident_index is None:
        raise ValueError("Download the public incident CSV before starting the demo.")
    # Only complete a check that Scout actually recommended in its latest reply.
    # The same explicit action is available in normal chat and presenter mode.
    if completed_check_id:
        earlier = get_messages(case_id)
        last_reply = next((m for m in reversed(earlier) if m["role"] == "assistant"), None)
        offered = last_reply.get("evidence", {}).get("playbooks", []) if last_reply else []
        if not any(card["id"] == completed_check_id for card in offered):
            raise ValueError("Choose a check from the current investigation plan.")
        add_note(case_id, "confirmed_fact", f"Completed check {completed_check_id}: {question}")
    add_message(case_id, "user", question)
    conversation = get_messages(case_id)
    recorded_notes = get_notes(case_id)
    search_text = retrieval_query(conversation, recorded_notes, question)
    case_reports = reported_case_text(conversation, recorded_notes)
    finished = completed_checks(recorded_notes)
    # Filter only after selecting applicable guides. A completed timeline
    # stays in the evidence history but no longer blocks the next check.
    applicable = (
        select_playbooks(case_reports, playbook_catalogue, max_steps=len(playbook_catalogue))
        if use_knowledge else []
    )
    selected_playbooks = [card for card in applicable if card["id"] not in finished][:5]
    results = retrieve(search_text, incident_index, k=k)
    supporting = historical_evidence_for_answer(search_text, results)
    baseline = keyword_search(search_text, incident_index.records, k=k)
    guides = (
        retrieve_knowledge(search_text, knowledge_index, k=3)
        if use_knowledge and knowledge_index is not None else []
    )
    response = first_useful_reply(
        results, guides, selected_playbooks, case_reports,
    )
    if finished:
        titles = {card["id"]: card["title"] for card in playbook_catalogue}
        findings = []
        for check_id, finding in finished.items():
            findings.append(f"- **{titles.get(check_id, check_id)}:** {finding}")
        summary = "**Recorded investigation findings** (reported by the investigator):\n" + "\n".join(findings)
        if selected_playbooks:
            # Acknowledge the result, then recommend only the remaining checks.
            latest_finding = finished.get(completed_check_id or "")
            if latest_finding:
                response["answer"] = "**Check recorded.** " + latest_finding + "\n\n" + response["answer"]
        else:
            resolutions = [note["content"] for note in recorded_notes
                           if note.get("kind") == "verified_resolution"]
            if resolutions:
                response["answer"] = (
                    summary + "\n\n**Conclusion — recovery reported:** " + resolutions[-1]
                    + "\n\nThe investigator has recorded recovery. Scout has not inspected "
                      "the system or independently established the root cause."
                )
            else:
                response["answer"] = (
                    summary + "\n\n**Conclusion so far:** the recommended checks have "
                    "recorded findings. Review which explanation the evidence supports "
                    "and what remains uncertain. If the service has recovered, record "
                    "what changed and how recovery was verified before closing the case."
                    "\n\nScout has not independently verified the cause or executed any fix."
                )
    message_id = add_message(
        case_id, "assistant", response["answer"],
        evidence=source_snapshot(
            results, guides, response,
            baseline=baseline, supporting_incidents=supporting,
            playbooks=selected_playbooks,
        ),
    )
    return {
        "message_id": message_id,
        "playbook_ids": [item["id"] for item in selected_playbooks],
        "incident_count": len(results),
        "response": response["answer"],
    }
