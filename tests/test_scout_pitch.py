"""Presenter controls use the real Scout pipeline and never fake an AI result.

Fixtures are fictional, isolated and run without Ollama or private local data.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.scout_case_store import (
    create_case, get_messages, get_notes, get_verification_reviews, list_cases,
    initialise_database,
)
from src.scout_demo import (
    DEMO_CASE_TITLE, DEMO_OPENING, DEMO_STEPS, DEMO_RECOVERY, next_demo_step,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture(monkeypatch, tmp_path):
    database = tmp_path / "pitch_cases.db"
    monkeypatch.setenv("SCOUT_CASE_DB", str(database))
    csv = tmp_path / "public_sample.csv"
    csv.write_text(
        "id,vendor_name,title,started_at,url,components\n"
        "a,Example Status,API 504 gateway timeout,2026-11-01,"
        "https://example.org/api,API\n"
        "b,Example Status,Database connection degradation,2026-11-02,"
        "https://example.org/postgres,Database\n"
        "c,Example Status,Checkout deployment delay,2026-11-03,"
        "https://example.org/deploy,Checkout\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SCOUT_INCIDENT_CSV", str(csv))
    return database


def _button(app, label):
    return next(item for item in app.button if item.label == label)


def test_pitch_page_opens_and_uses_real_chart_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_CASE_DB", str(tmp_path / "pitch.db"))
    app = AppTest.from_file(str(ROOT / "pages" / "Pitch.py")).run(timeout=40)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert "▶ Enter the live Scout demo" in [
        button.label for button in app.button
    ]
    assert len(app.get("image")) == 2


def test_one_click_pitch_preparation_followups_review_and_original_case(
    monkeypatch, tmp_path,
):
    db = _fixture(monkeypatch, tmp_path)
    initialise_database(db)
    untouched = create_case("Real existing case", db)

    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=40)
    assert not app.exception, [str(error.message) for error in app.exception]
    toggle = next(x for x in app.checkbox if x.label == "Show presenter controls")
    toggle.set_value(True).run(timeout=40)

    mode = next(
        x for x in app.selectbox
        if x.label == "How would you like Scout to help?"
    )
    mode.set_value("Evidence only (no LLM)").run(timeout=40)

    _button(app, "▶ Prepare a fresh demo case").click().run(timeout=40)
    assert not app.exception, [str(error.message) for error in app.exception]
    current_id = app.session_state["scout_current_case"]
    assert current_id != untouched["id"]
    demo_case = next(x for x in list_cases(db) if x["id"] == current_id)
    assert demo_case["title"] == DEMO_CASE_TITLE
    messages = get_messages(current_id, db)
    assert [x["role"] for x in messages] == ["user", "assistant"]
    assert messages[0]["content"] == DEMO_OPENING
    assert any("Audience question" in item.value for item in app.info)
    assert messages[1]["evidence"]["incidents"]
    assert not messages[1]["evidence"]["model_draft"]
    assert next_demo_step([])["id"] == "PB-TIMELINE-01"
    for number, step in enumerate(DEMO_STEPS, start=1):
        assert step["label"].startswith(f"{number}. ")
        assert any(f"Next check: {number} of 5" in x.body for x in app.markdown)
        previous = get_messages(current_id, db)[-1]
        assert previous["evidence"]["playbooks"][0]["id"] == step["id"]
        _button(app, step["label"]).click().run(timeout=40)
        assert not app.exception, [str(error.message) for error in app.exception]
        messages = get_messages(current_id, db)
        assert messages[-2]["content"] == step["finding"]
        assert any("Completed: " + step["label"] in x.value for x in app.success)
        assert len(get_notes(current_id, db)) == number
        assert step["id"] not in [card["id"] for card in messages[-1]["evidence"]["playbooks"]]
        assert app.session_state["scout_current_case"] == current_id
    assert next_demo_step(get_notes(current_id, db)) is None
    assert "Conclusion so far" in messages[-1]["content"]
    _button(app, "Verify recovery and close the fictional case").click().run(timeout=40)
    assert not app.exception, [str(error.message) for error in app.exception]
    reviews = get_verification_reviews(current_id, db)
    assert len(reviews) == 1
    assert reviews[0]["outcome"] == "supported"
    assert "DEMONSTRATION ONLY" in reviews[0]["detail"]
    messages = get_messages(current_id, db)
    assert messages[-2]["content"] == DEMO_RECOVERY
    assert "recovery reported" in messages[-1]["content"]
    assert "not inspected" in messages[-1]["content"]
    assert next(x for x in list_cases(db) if x["id"] == current_id)["status"] == "resolved"
    assert get_messages(untouched["id"], db) == []
    assert any("Full case log" in x.label for x in app.expander)
    assert any(b.label == "Finish pitch · Beyond the prototype" for b in app.button)


def test_pitch_buttons_disabled_without_incident_csv(monkeypatch, tmp_path):
    db = tmp_path / "no_data.db"
    monkeypatch.setenv("SCOUT_CASE_DB", str(db))
    monkeypatch.setenv("SCOUT_INCIDENT_CSV", str(tmp_path / "missing.csv"))

    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=40)
    next(x for x in app.checkbox if x.label == "Show presenter controls").set_value(
        True
    ).run(timeout=40)
    assert _button(app, "▶ Prepare a fresh demo case").disabled
    assert list_cases(db) == []

def test_normal_investigation_can_record_timeline_and_advance(monkeypatch, tmp_path):
    db = _fixture(monkeypatch, tmp_path)
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=40)
    next(x for x in app.selectbox if x.label == "How would you like Scout to help?").set_value(
        "Evidence only (no LLM)"
    ).run(timeout=40)
    next(x for x in app.text_area if x.label == "Describe your incident").set_value(
        "Checkout API has 504 errors after a deployment."
    )
    _button(app, "Start investigation").click().run(timeout=40)
    case_id = list_cases(db)[0]["id"]
    initial = get_messages(case_id, db)[-1]
    assert initial["evidence"]["playbooks"][0]["id"] == "PB-TIMELINE-01"
    next(x for x in app.text_area if x.label == "What did this check establish?").set_value(
        "I compared logs in UTC: release 09:00, first errors 09:15, last errors 09:30."
    )
    _button(app, "Save result and continue").click().run(timeout=40)
    assert not app.exception, [str(error.message) for error in app.exception]
    notes = get_notes(case_id, db)
    assert notes[0]["content"].startswith("Completed check PB-TIMELINE-01:")
    latest = get_messages(case_id, db)[-1]
    assert latest["evidence"]["playbooks"][0]["id"] == "PB-DEPENDENCIES-01"
    assert "Check recorded" in latest["content"]
    assert get_messages(case_id, db)[1]["content"] == initial["content"]


def test_fresh_demo_stays_selected_when_old_demo_has_three_checks(monkeypatch, tmp_path):
    """Regression: same-title cases must not share a selectbox label or progress."""
    db = _fixture(monkeypatch, tmp_path)
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=40)
    next(x for x in app.checkbox if x.label == "Show presenter controls").set_value(
        True
    ).run(timeout=40)
    next(x for x in app.selectbox if x.label == "How would you like Scout to help?").set_value(
        "Evidence only (no LLM)"
    ).run(timeout=40)

    _button(app, "▶ Prepare a fresh demo case").click().run(timeout=40)
    old_id = app.session_state["scout_current_case"]
    for step in DEMO_STEPS[:3]:
        _button(app, step["label"]).click().run(timeout=40)
        assert not app.exception, [str(error.message) for error in app.exception]
    old_messages = get_messages(old_id, db)
    old_notes = get_notes(old_id, db)
    assert len(old_notes) == 3

    # This is the user's exact sequence: prepare another identical-looking
    # demo while the previous one is already partway through.
    _button(app, "▶ Prepare a fresh demo case").click().run(timeout=40)
    assert not app.exception, [str(error.message) for error in app.exception]
    new_id = app.session_state["scout_current_case"]
    assert new_id != old_id
    assert len(get_messages(new_id, db)) == 2
    assert get_notes(new_id, db) == []
    picker = next(x for x in app.selectbox if x.label == "Your investigations")
    assert len(picker.options) == len(set(picker.options))
    assert any(old_id[:8] in label for label in picker.options)
    assert any(new_id[:8] in label for label in picker.options)
    assert picker.value == new_id

    # A normal rerun and the timeline click must not restore the old demo.
    app.run(timeout=40)
    assert app.session_state["scout_current_case"] == new_id
    assert any("Next check: 1 of 5" in x.body for x in app.markdown)
    _button(app, DEMO_STEPS[0]["label"]).click().run(timeout=40)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert app.session_state["scout_current_case"] == new_id
    assert len(get_notes(new_id, db)) == 1
    assert len(get_messages(new_id, db)) == 4
    assert any("Next check: 2 of 5" in x.body for x in app.markdown)
    assert get_messages(old_id, db) == old_messages
    assert get_notes(old_id, db) == old_notes

    # Explicitly reopening the old demo is allowed; it must show its own
    # fourth check. Selecting the new demo again must show its second.
    next(x for x in app.selectbox if x.label == "Your investigations").set_value(
        old_id
    ).run(timeout=40)
    assert app.session_state["scout_current_case"] == old_id
    assert any("Next check: 4 of 5" in x.body for x in app.markdown)
    next(x for x in app.selectbox if x.label == "Your investigations").set_value(
        new_id
    ).run(timeout=40)
    assert app.session_state["scout_current_case"] == new_id
    assert any("Next check: 2 of 5" in x.body for x in app.markdown)
    assert not app.exception, [str(error.message) for error in app.exception]
