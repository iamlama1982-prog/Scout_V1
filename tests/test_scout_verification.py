"""Human verification is explicit, scoped and never granted by the LLM."""

import pytest

from src.scout_case_store import (
    add_message, add_verification_review, create_case, delete_case,
    export_case, get_verification_reviews, initialise_database,
    set_case_status, update_assistant_evidence,
)
from src.scout_conversation import source_snapshot
from src.scout_verification import ai_verification_notice, initial_verification_notice


def test_playbook_notice_has_reason_and_practical_check():
    notice = initial_verification_notice({
        "playbooks": [{"title": "Build a timeline"}],
        "incidents": [{"doc_id": "INC-1"}],
    })
    assert "Build a timeline" in notice["reason"]
    assert "live" in notice["reason"]
    assert "logs" in notice["human_check"]


def test_historical_source_is_only_a_lead():
    evidence = {
        "incidents": [{"doc_id": "INC-1"}],
        "supporting_incident_ids": ["INC-1"],
    }
    notice = initial_verification_notice(evidence)
    assert "current cause unconfirmed" in notice["source_state"]
    assert "other organisations" in notice["reason"]
    assert "Open the original report" in notice["human_check"]


def test_missing_evidence_requires_more_details():
    notice = initial_verification_notice({})
    assert "No supporting incident" in notice["source_state"]
    assert "start time" in notice["human_check"]


def test_reference_without_playbook_requires_confirmation():
    notice = initial_verification_notice({"guides": [{"kb_id": "KB-a"}]})
    assert "no checked investigation playbook" in notice["reason"]


@pytest.mark.parametrize(
    ("cited", "fragment"),
    [
        ([], "No usable source IDs"),
        (["INC-missing"], "not in this reply"),
        (["INC-known"], "do not prove"),
    ],
)
def test_ai_notice_never_self_verifies(cited, fragment):
    evidence = {
        "incidents": [{"doc_id": "INC-known"}],
        "model_draft_cited_ids": cited,
    }
    assert fragment in ai_verification_notice(evidence)["reason"]
    assert "not independently verified" in ai_verification_notice(evidence)["source_state"]


def test_snapshot_saves_explanation_and_optional_ai_cannot_replace_it(tmp_path):
    db = tmp_path / "cases.db"
    initialise_database(db)
    case = create_case("Timeout", db)
    reply = {
        "answer": "Check a timeline", "model": "reviewed investigation plan",
        "seconds": 0, "tokens": 0,
    }
    evidence = source_snapshot(
        [], [], reply, playbooks=[{"title": "Check changes"}],
    )
    assert "Check changes" in evidence["initial_verification"]["reason"]
    mid = add_message(case["id"], "assistant", "Check a timeline", evidence, db)
    with pytest.raises(ValueError, match="Only model-generation"):
        update_assistant_evidence(
            case["id"], mid,
            {"initial_verification": {"source_state": "verified"}},
            db,
        )
    update_assistant_evidence(
        case["id"], mid, {"model_draft": "AI thinks it knows."}, db,
    )
    with pytest.raises(ValueError, match="Only model-generation"):
        update_assistant_evidence(
            case["id"], mid, {"verification_reviews": [{"outcome": "supported"}]}, db,
        )


def test_human_review_is_scoped_append_only_and_exported(tmp_path):
    db = tmp_path / "cases.db"
    initialise_database(db)
    a = create_case("A", db)
    b = create_case("B", db)
    mid = add_message(a["id"], "assistant", "Plan", {"model_draft": "AI draft"}, db)
    add_verification_review(
        a["id"], mid, "initial_reply", "uncertain",
        "No logs have been checked yet", db,
    )
    add_verification_review(
        a["id"], mid, "initial_reply", "supported",
        "Validated the selected step against service logs", db,
    )
    add_verification_review(
        a["id"], mid, "ai_interpretation", "not_supported",
        "The cited report was about a different component", db,
    )
    reviews = get_verification_reviews(a["id"], db)
    assert [r["outcome"] for r in reviews] == [
        "uncertain", "supported", "not_supported",
    ]
    assert len(export_case(a["id"], db)["verification_reviews"]) == 3
    assert get_verification_reviews(b["id"], db) == []
    delete_case(a["id"], db)
    assert get_verification_reviews(a["id"], db) == []


def test_human_check_rejects_invalid_scope_or_unsupported_target(tmp_path):
    db = tmp_path / "cases.db"
    initialise_database(db)
    a = create_case("A", db)
    b = create_case("B", db)
    user_mid = add_message(a["id"], "user", "Incident", db_path=db)
    reply_mid = add_message(a["id"], "assistant", "Plan", db_path=db)
    args = (a["id"], reply_mid, "initial_reply", "supported")
    with pytest.raises(ValueError, match="12"):
        add_verification_review(*args, "OK", db)
    with pytest.raises(ValueError, match="Unknown item"):
        add_verification_review(a["id"], reply_mid, "model_claim", "supported", "Checked actual service logs", db)
    with pytest.raises(ValueError, match="Unknown review outcome"):
        add_verification_review(a["id"], reply_mid, "initial_reply", "AI_verified", "Checked actual service logs", db)
    with pytest.raises(ValueError, match="not found"):
        add_verification_review(b["id"], reply_mid, "initial_reply", "supported", "Checked actual service logs", db)
    with pytest.raises(ValueError, match="not found"):
        add_verification_review(a["id"], user_mid, "initial_reply", "supported", "Checked actual service logs", db)
    with pytest.raises(ValueError, match="no AI interpretation"):
        add_verification_review(a["id"], reply_mid, "ai_interpretation", "supported", "Checked actual service logs", db)
    add_verification_review(*args, "Checked actual service logs", db)
    set_case_status(a["id"], "open", db)


def test_resolved_case_does_not_accept_new_review(tmp_path):
    db = tmp_path / "cases.db"
    initialise_database(db)
    from src.scout_case_store import add_note
    case = create_case("A", db)
    mid = add_message(case["id"], "assistant", "Plan", db_path=db)
    add_note(case["id"], "verified_resolution", "Verified end-to-end", db)
    set_case_status(case["id"], "resolved", db)
    with pytest.raises(ValueError, match="Reopen"):
        add_verification_review(
            case["id"], mid, "initial_reply", "supported",
            "Checked actual service logs", db,
        )
