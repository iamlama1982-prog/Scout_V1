"""Checked investigation guides: provenance, relevance, safety and persistence.

These tests do not claim that the LLM can correctly diagnose a real outage.
They make sure the *clickable instructions* do not depend on an improvised
model answer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.incident_assistant import build_messages
from src.scout_case_store import add_message, create_case, export_case, get_messages, initialise_database
from src.scout_conversation import source_snapshot
from src.scout_playbooks import (
    PLAYBOOK_PATH, checked_plan_response, guide_led_answer, load_playbooks,
    playbook_prompt_summary, reported_case_text, select_playbooks,
)


@pytest.fixture
def catalogue():
    return load_playbooks()


def test_catalogue_has_safe_sources_and_working_explanations(catalogue):
    assert len(catalogue) == 6
    assert len({item["id"] for item in catalogue}) == len(catalogue)
    for item in catalogue:
        assert len(item["steps"]) >= 2
        assert item["interpretation"]["supports"]
        assert item["interpretation"]["weakens"]
        assert item["interpretation"]["unknown"]
        if item["source_type"] == "official_documentation":
            assert item["source_url"].startswith("https://")
            assert item["reference_id"].startswith("KB-")
        else:
            assert item["source_url"] == ""
            assert item["reference_id"] is None


def test_postgres_requires_user_supplied_technology(catalogue):
    intro = "Checkout failures and API timeouts. We suspect a shared dependency."
    ids = {item["id"] for item in select_playbooks(intro, catalogue)}
    assert "PB-POSTGRES-01" not in ids

    user_history = [
        {"role": "user", "content": intro},
        {"role": "assistant", "content": "You may wish to inspect PostgreSQL."},
    ]
    based_on_user = reported_case_text(user_history, [])
    assert "PostgreSQL" not in based_on_user
    assert "PB-POSTGRES-01" not in {
        item["id"] for item in select_playbooks(based_on_user, catalogue)
    }

    history = user_history + [{"role": "user", "content": "We use PostgreSQL."}]
    ids = {item["id"] for item in select_playbooks(reported_case_text(history, []), catalogue)}
    assert "PB-POSTGRES-01" in ids
    assert "PB-TIMELINE-01" in ids


def test_rejected_technology_is_not_assumed(catalogue):
    text = "Our API is slow. We don't use PostgreSQL."
    ids = {item["id"] for item in select_playbooks(text, catalogue)}
    assert "PB-POSTGRES-01" not in ids


def test_generic_guides_are_not_claimed_as_official(catalogue):
    selected = select_playbooks("Checkout failures and API delays may be connected", catalogue)
    assert selected[0]["id"] == "PB-TIMELINE-01"
    assert selected[0]["source_type"] == "general_investigation"
    assert not selected[0]["source_url"]
    assert "PB-DEPENDENCIES-01" in {item["id"] for item in selected}
    assert "PB-TRACE-01" in {item["id"] for item in selected}


def test_official_guides_only_when_relevant(catalogue):
    standalone = select_playbooks("HTTP 504 from our reverse proxy", catalogue)
    assert "PB-HTTP-504-01" in {item["id"] for item in standalone}
    unknown = select_playbooks("The team's rota is missing", catalogue)
    assert unknown == []
    pod = select_playbooks("Our Kubernetes pod is restarting after a deployment.", catalogue)
    assert "PB-K8S-POD-01" in {item["id"] for item in pod}


def test_only_documented_read_only_commands(catalogue):
    commands = [
        (card["id"], step["command"])
        for card in catalogue
        for step in card["steps"]
        if "command" in step
    ]
    assert len(commands) >= 3
    pg = next(item for item in catalogue if item["id"] == "PB-POSTGRES-01")
    sql = next(item["command"] for item in pg["steps"] if "command" in item)
    assert sql.strip().startswith("SELECT")
    assert "FROM pg_stat_activity" in sql
    assert "pg_stat_database_size" not in sql
    assert all(
        command.startswith(("SELECT ", "kubectl describe pod ", "kubectl logs "))
        for _, command in commands
    )


def test_reject_unapproved_source_and_mutating_sql(catalogue, tmp_path):
    original = json.loads(PLAYBOOK_PATH.read_text(encoding="utf-8"))
    changed = tmp_path / "playbooks.json"
    official = next(
        c for c in original["playbooks"] if c["id"] == "PB-POSTGRES-01"
    )
    official["reference_id"] = "KB-FAKE-999"
    changed.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown official source"):
        load_playbooks(changed)

    official["reference_id"] = "KB-PG-STATS-01"
    sql = next(step for step in official["steps"] if "command" in step)
    sql["command"] = "SELECT 1; DELETE FROM tickets;"
    changed.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError, match="SQL"):
        load_playbooks(changed)


def test_playbook_prompt_contains_guide_not_invented_commands(catalogue):
    selected = select_playbooks("We use PostgreSQL and the API is timing out", catalogue)
    prompt = playbook_prompt_summary(selected)
    assert "CLICKABLE INVESTIGATION GUIDES" in prompt
    assert "Never invent SQL" in prompt
    messages = build_messages("How can I investigate this?", [], [], "Same case", selected)
    assert "PB-POSTGRES-01" in messages[1]["content"]
    assert "Don't write executable SQL" in messages[0]["content"]
    assert "Do NOT write another checklist" in messages[0]["content"]
    assert "first priority MUST be the FIRST checked guide" in messages[0]["content"]
    assert selected[0]["title"] in messages[0]["content"]
    assert "The actual question is" in messages[0]["content"]
    assert "The interface itself presents these guides IN THE ORDER SHOWN" in messages[1]["content"]
    assert "Use the following natural headings" not in messages[0]["content"]


def test_saved_replies_keep_exact_guides_after_reopening(tmp_path, catalogue):
    db = tmp_path / "scout_guides.db"
    initialise_database(db)
    case = create_case("API failure", db)
    steps = select_playbooks("Our API gives 504 timeouts", catalogue)
    snapshot = source_snapshot([], [], {
        "answer": "Check the gateway", "model": "test",
        "cited_ids": [], "seconds": 0, "tokens": 0,
    }, playbooks=steps)
    add_message(case["id"], "user", "Our API gives 504 timeouts", db_path=db)
    add_message(case["id"], "assistant", "Check the gateway", evidence=snapshot, db_path=db)
    reopened = get_messages(case["id"], db)
    assert reopened[1]["evidence"]["playbooks"] == steps
    exported = export_case(case["id"], db)
    assert exported["conversation"][1]["evidence"]["playbooks"] == steps



def test_checked_plan_overrides_conflicting_model_checklist(catalogue):
    """A small model's plausible-sounding database-first advice cannot outrank the checked plan."""
    user_report = (
        "Our checkout API times out and database connections are slow. "
        "We use PostgreSQL and deployed an update on Monday."
    )
    selected = select_playbooks(user_report, catalogue)
    raw = {
        "answer": "The actual question is... First check database memory, then the gateway.",
        "cited_ids": ["KB-PG-STATS-01"],
        "model": "llama3.2", "tokens": 300, "seconds": 10.0,
    }
    shown = checked_plan_response(raw, selected, user_report)
    assert selected[0]["id"] == "PB-TIMELINE-01"
    assert "Put the failures and changes on one timeline" in shown["answer"]
    assert "The reported change is worth investigating" in shown["answer"]
    assert "database memory" not in shown["answer"]
    assert "The actual question is" not in shown["answer"]
    assert "View steps" in shown["answer"]
    assert shown["cited_ids"] == []
    assert shown["model_draft"] == raw["answer"]
    assert shown["model_draft_cited_ids"] == raw["cited_ids"]
    assert raw["cited_ids"] == ["KB-PG-STATS-01"]
    assert shown["model"] == "llama3.2"


def test_no_checked_plan_preserves_llm_factual_answers(catalogue):
    raw = {"answer": "A simple answer", "cited_ids": []}
    assert checked_plan_response(raw, [], "What is the error?") is raw
    with pytest.raises(ValueError, match="needs at least one"):
        guide_led_answer([], "anything")


def test_guided_plan_and_original_ai_draft_survive_case_reopen(tmp_path, catalogue):
    db = tmp_path / "scout_checked_plan.db"
    initialise_database(db)
    case = create_case("Checkout API errors", db)
    user_input = "Checkout API timeouts after a deployment, using PostgreSQL."
    selected = select_playbooks(user_input, catalogue)
    raw = {
        "answer": "Check the database first; memory may be low.",
        "cited_ids": ["KB-PG-STATS-01"],
        "model": "llama3.2", "seconds": 5, "tokens": 120,
    }
    response = checked_plan_response(raw, selected, user_input)
    snapshot = source_snapshot([], [], response, playbooks=selected)
    add_message(case["id"], "user", user_input, db_path=db)
    add_message(case["id"], "assistant", response["answer"], evidence=snapshot, db_path=db)
    reopened = get_messages(case["id"], db)
    assert "Put the failures and changes on one timeline" in reopened[1]["content"]
    assert "database first" not in reopened[1]["content"]
    assert reopened[1]["evidence"]["model_draft"] == raw["answer"]
    assert reopened[1]["evidence"]["model_draft_cited_ids"] == raw["cited_ids"]
    assert reopened[1]["evidence"]["playbooks"] == selected
