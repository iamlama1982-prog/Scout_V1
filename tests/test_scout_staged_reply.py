"""Staged response checks: the reviewed plan is never blocked by inference."""

from pathlib import Path

import pytest

from src.incident_assistant import answer_with_llm, build_messages
from src.scout_case_store import (
    add_message, create_case, get_messages, initialise_database,
    set_case_status, update_assistant_evidence,
)
from src.scout_conversation import source_snapshot
from src.scout_playbooks import load_playbooks, select_playbooks
from src.scout_response_flow import first_useful_reply


def test_guided_reply_is_available_without_an_llm():
    text = "Checkout API timeouts after a deployment; slow PostgreSQL connections"
    playbooks = select_playbooks(text, load_playbooks())
    assert playbooks
    response = first_useful_reply([], [], playbooks, text)
    assert "I'd start with:" in response["answer"]
    assert playbooks[0]["title"] in response["answer"]
    assert response["model"] == "reviewed investigation plan"
    assert response["seconds"] == 0
    assert "confirmed diagnosis" in response["answer"]


def test_no_playbook_reply_lists_actual_source_links():
    incidents = [{
        "doc_id": "INC-demo", "vendor": "Acme",
        "title": "API degraded in Europe",
        "started_at": "2026-11-01T13:00:00Z",
        "source_url": "https://status.example.com/incidents/abc",
    }]
    response = first_useful_reply(incidents, [], [], "API outage")
    assert "Acme" in response["answer"]
    assert "API degraded in Europe" in response["answer"]
    assert "https://status.example.com/incidents/abc" in response["answer"]
    assert "does not confirm" in response["answer"]


def test_source_retrieval_handles_no_hits_without_ai():
    response = first_useful_reply([], [], [], "No relevant incidents")
    assert "couldn't find" in response["answer"]
    assert response["model"] == "source retrieval only"


def test_optional_ai_preserves_original_reply_and_snapshot(tmp_path: Path):
    db = tmp_path / "cases.db"
    initialise_database(db)
    case = create_case("A checkout issue", db)
    add_message(case["id"], "user", "Checkout timing out", db_path=db)
    initial = first_useful_reply([], [], [], "Checkout timing out")
    evidence = source_snapshot([], [], initial, playbooks=[])
    response_id = add_message(
        case["id"], "assistant", initial["answer"],
        evidence=evidence, db_path=db,
    )
    update_assistant_evidence(
        case["id"], response_id,
        {"model_draft": "One possible explanation (unverified).",
         "model_draft_cited_ids": [], "seconds": 7.2,
         "tokens": 120, "model": "llama3.2"},
        db_path=db,
    )
    saved = get_messages(case["id"], db)[1]
    assert saved["content"] == initial["answer"]
    assert saved["evidence"]["model_draft"].startswith("One possible")
    assert saved["evidence"]["seconds"] == 7.2
    assert saved["evidence"]["model"] == "llama3.2"
    assert saved["evidence"]["incidents"] == []


def test_optional_ai_cannot_modify_user_message_or_other_case(tmp_path: Path):
    db = tmp_path / "cases.db"
    initialise_database(db)
    a = create_case("Case A", db)
    b = create_case("Case B", db)
    user_id = add_message(a["id"], "user", "Example question", db_path=db)
    with pytest.raises(ValueError, match="assistant reply"):
        update_assistant_evidence(a["id"], user_id, {"model_draft": "fake"}, db)
    assistant_id = add_message(a["id"], "assistant", "Evidence first", db_path=db)
    with pytest.raises(ValueError, match="assistant reply"):
        update_assistant_evidence(b["id"], assistant_id, {"model_draft": "fake"}, db)
    with pytest.raises(ValueError, match="Only model-generation"):
        update_assistant_evidence(a["id"], assistant_id, {"incidents": []}, db)


def test_resolved_case_does_not_accept_new_optional_ai_result(tmp_path: Path):
    from src.scout_case_store import add_note
    db = tmp_path / "cases.db"
    initialise_database(db)
    a = create_case("Case A", db)
    reply_id = add_message(a["id"], "assistant", "A checked plan", db_path=db)
    add_note(a["id"], "verified_resolution", "Issue checked and resolved", db_path=db)
    set_case_status(a["id"], "resolved", db_path=db)
    with pytest.raises(ValueError, match="resolved"):
        update_assistant_evidence(a["id"], reply_id, {"model_draft": "Late AI"}, db)


def test_generation_ceiling_validation_does_not_call_model():
    results = [{"doc_id": "INC-abc", "vendor": "Acme", "title": "API unavailable",
                "started_at": "", "impact": "", "status": "", "components": ""}]
    with pytest.raises(ValueError, match="max_tokens"):
        answer_with_llm("What happened?", results, api_key="ollama", max_tokens=0)



def test_old_saved_technical_guide_can_be_reused_for_optional_ai():
    """Regression: the first staged UI reused saved guides without applies_to.

    Previously build_messages accessed row['applies_to'] unconditionally and
    the optional AI button failed for an existing case before Ollama ran.
    """
    old_guide = {
        "kb_id": "KB-old", "title": "PostgreSQL sessions",
        "publisher": "PostgreSQL", "url": "https://example.org/guide",
        "summary": "Read-only diagnostic guidance",
        "diagnostic_checks": ["Inspect sessions"],
        "reviewed_on": "2026-11-01",
        # The previously saved case never had "applies_to".
    }
    messages = build_messages(
        "Could the checkout timeouts and database waits be connected?",
        [], knowledge_results=[old_guide], case_context="Existing case",
    )
    assert len(messages) == 2
    assert "verify applicability" in messages[1]["content"]


def test_new_technical_snapshot_carries_applicability():
    guide = {
        "kb_id": "KB-new", "title": "PostgreSQL sessions",
        "publisher": "PostgreSQL", "url": "https://example.org/guide",
        "summary": "Read-only diagnostic guidance",
        "applies_to": "Only confirmed PostgreSQL systems",
        "diagnostic_checks": ["Inspect sessions"],
        "reviewed_on": "2026-11-01",
    }
    snap = source_snapshot([], [guide], {"model": "retrieval only"})
    assert snap["guides"][0]["applies_to"] == "Only confirmed PostgreSQL systems"
    messages = build_messages(
        "Inspect confirmed PostgreSQL sessions", [],
        knowledge_results=snap["guides"],
    )
    assert "Only confirmed PostgreSQL systems" in messages[1]["content"]
