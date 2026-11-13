"""Full case-log visibility and persistence across human-review reruns."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.scout_case_log import format_case_log
from src.scout_case_store import (
    add_message, add_verification_review, create_case,
    get_messages, get_verification_reviews, initialise_database, list_cases,
)

ROOT = Path(__file__).resolve().parents[1]


def test_complete_readable_log_has_uuid_full_messages_sources_and_all_reviews(tmp_path):
    db = tmp_path / "cases.db"
    initialise_database(db)
    case = create_case("Intermittent checkout", db)
    add_message(case["id"], "user", "API 504 errors began yesterday.", db_path=db)
    mid = add_message(
        case["id"], "assistant", "Check the upstream timeline.",
        evidence={
            "incidents": [{
                "doc_id": "INC-demo", "title": "API unavailable",
                "vendor": "Demo vendor", "source_url": "https://example.org/incident",
            }],
            "model_draft": "The deployment may be involved.",
            "playbooks": [{
                "id": "PB-TIMELINE", "title": "Build timeline",
                "steps": [{"instruction": "Compare failure timestamps", "command": "date"}],
            }],
        },
        db_path=db,
    )
    add_verification_review(
        case["id"], mid, "initial_reply", "not_supported",
        "Error and deployment timestamps did not overlap.", db,
    )
    add_verification_review(
        case["id"], mid, "initial_reply", "uncertain",
        "We need better upstream trace timestamps before deciding.", db,
    )
    log = format_case_log(
        case, get_messages(case["id"], db), [],
        get_verification_reviews(case["id"], db),
    )
    for text in [
        case["id"], "API 504 errors began yesterday.", "Check the upstream timeline.",
        "INC-demo", "https://example.org/incident", "PB-TIMELINE",
        "Compare failure timestamps", "OPTIONAL AI INTERPRETATION (UNVERIFIED)",
        "not_supported", "uncertain", "Error and deployment timestamps",
        "better upstream trace timestamps",
    ]:
        assert text in log


def test_latest_case_restores_on_new_browser_session_after_human_check(
    monkeypatch, tmp_path,
):
    """No new-invocation placeholder after a saved human review and refresh."""
    db = tmp_path / "case_history.db"
    monkeypatch.setenv("SCOUT_CASE_DB", str(db))
    initialise_database(db)
    old_case = create_case("Older case", db)
    add_message(old_case["id"], "user", "Original history", db_path=db)
    active = create_case("Case with human checks", db)
    add_message(active["id"], "user", "504 timeouts", db_path=db)
    mid = add_message(active["id"], "assistant", "Check timestamps", db_path=db)
    add_verification_review(
        active["id"], mid, "initial_reply", "not_supported",
        "Our timestamps disprove this exact hypothesis.", db,
    )

    fresh_browser = AppTest.from_file(str(ROOT / "app.py")).run(timeout=40)
    assert not fresh_browser.exception, [str(e.message) for e in fresh_browser.exception]
    assert fresh_browser.session_state["scout_current_case"] == active["id"]
    assert any("Full case log" in e.label for e in fresh_browser.expander)
    assert any(
        active["id"] in str(area.value) for area in fresh_browser.text_area
    )
    assert any(
        "Our timestamps disprove" in str(area.value)
        for area in fresh_browser.text_area
    )

    # A human review updates the case, but never clears selection or its history.
    fresh_browser = fresh_browser.run(timeout=40)
    assert fresh_browser.session_state["scout_current_case"] == active["id"]
    assert len(get_verification_reviews(active["id"], db)) == 1
    assert len(list_cases(db)) == 2


def test_case_selector_does_not_jump_after_review_reorders_case_list(
    monkeypatch, tmp_path,
):
    db = tmp_path / "cases.db"
    monkeypatch.setenv("SCOUT_CASE_DB", str(db))
    initialise_database(db)
    case_a = create_case("Original case", db)
    add_message(case_a["id"], "user", "Earlier symptom", db_path=db)
    reply_id = add_message(case_a["id"], "assistant", "First check", db_path=db)
    case_b = create_case("Other case", db)
    add_message(case_b["id"], "user", "Unrelated incident", db_path=db)

    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=40)
    assert not app.exception
    select = next(x for x in app.selectbox if x.label == "Your investigations")
    select.set_value(case_a["id"]).run(timeout=40)
    assert app.session_state["scout_current_case"] == case_a["id"]

    add_verification_review(
        case_a["id"], reply_id, "initial_reply", "supported",
        "Compared historical report and production timestamps.", db,
    )
    app.run(timeout=40)
    assert not app.exception
    assert app.session_state["scout_current_case"] == case_a["id"]
    assert app.session_state["scout_case_picker"] == case_a["id"]
    assert any("Full case log" in e.label for e in app.expander)
