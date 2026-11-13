"""Check that the tutor's focused Scout entrypoint starts.

This runs the Streamlit page in a test harness without a browser. It does not
run Ollama, and it is not an assessment of the LLM's answers.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.scout_case_store import get_case, get_messages, list_cases


@pytest.fixture
def isolated_scout_database(monkeypatch, tmp_path):
    """Never let the UI smoke tests create cases in a user's real database."""
    path = tmp_path / "scout_ui_test.db"
    monkeypatch.setenv("SCOUT_CASE_DB", str(path))
    return path


def test_scout_tutor_entrypoint_starts(isolated_scout_database):
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert list_cases(isolated_scout_database) == []
    assert any("Start here" in item.body for item in app.markdown)
    assert any(item.label == "Describe your incident" for item in app.text_area)
    assert not any("Case record" in item.label for item in app.expander)


def test_new_investigation_button_creates_visible_case(isolated_scout_database):
    """Clicking Start must actually create and select a new saved case."""
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    new_button = next(
        button for button in app.button
        if "Start a new investigation" in button.label
    )
    new_button.click().run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    case_id = app.session_state["scout_current_case"]
    assert case_id != "__new_case__"
    assert get_case(case_id, isolated_scout_database)["title"] == "New investigation"
    assert len(list_cases(isolated_scout_database)) == 1

    # Clicking again must select a DIFFERENT new case, not silently do nothing.
    new_button = next(
        button for button in app.button
        if "Start a new investigation" in button.label
    )
    new_button.click().run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    second_id = app.session_state["scout_current_case"]
    assert second_id != case_id
    assert len(list_cases(isolated_scout_database)) == 2


def test_example_fills_the_opening_prompt(isolated_scout_database):
    """The first screen offers a working example, without sidebar setup."""
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    example = next(
        button for button in app.button if button.label == "Checkout failures"
    )
    example.click().run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    question = next(area for area in app.text_area if area.label == "Describe your incident")
    assert "slow database connections" in question.value
    assert list_cases(isolated_scout_database) == []


def test_new_case_opens_guided_start_not_empty_case_record(isolated_scout_database):
    """New case should take users directly to a clear first question form."""
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    start = next(button for button in app.button if "Start a new investigation" in button.label)
    start.click().run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert any("Start here" in item.body for item in app.markdown)
    assert any(area.label == "Describe your incident" for area in app.text_area)
    assert not any("Case record" in item.label for item in app.expander)


def test_start_here_creates_case_and_allows_followup(
    isolated_scout_database, monkeypatch, tmp_path
):
    """Exercise the full first-message path without Ollama or production data."""
    sample = tmp_path / "example_incidents.csv"
    sample.write_text(
        "id,vendor_name,title,started_at,url,components\n"
        "a,Demo Vendor,API timeouts affect checkout,2026-11-01,"
        "https://example.org/a,API\n"
        "b,Demo Host,Database connections are slow,2026-11-02,"
        "https://example.org/b,Database\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SCOUT_INCIDENT_CSV", str(sample))
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]

    mode = next(
        widget for widget in app.selectbox
        if widget.label == "How would you like Scout to help?"
    )
    mode.set_value("Evidence only (no LLM)").run(timeout=30)
    start_text = next(
        area for area in app.text_area if area.label == "Describe your incident"
    )
    # Streamlit forms batch their values until the submit event. Set the text
    # and click the submit button in the SAME simulated interaction.
    start_text.set_value("Checkout is timing out and our database is slow.")
    submit = next(button for button in app.button if button.label == "Start investigation")
    assert not submit.disabled
    submit.click().run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]

    cases = list_cases(isolated_scout_database)
    assert len(cases) == 1
    assert cases[0]["title"].startswith("Checkout is timing out")
    history = get_messages(cases[0]["id"], isolated_scout_database)
    assert [message["role"] for message in history] == ["user", "assistant"]
    assert not any(area.label == "Describe your incident" for area in app.text_area)
    assert len(app.chat_input) == 1
    assert any(
        "View steps" in expander.label for expander in app.expander
    ), "A case answer should include expandable investigation instructions."
    initial_cards = get_messages(cases[0]["id"], isolated_scout_database)[1]["evidence"]["playbooks"]
    assert "PB-TRACE-01" in {card["id"] for card in initial_cards}
    assert "PB-POSTGRES-01" not in {card["id"] for card in initial_cards}
    # Both roles need visible labels as well as different emoji avatars.
    # The same speaker labels are used by the CSS for distinct chat colours.
    speaker_labels = [
        block.body for block in app.markdown if "scout-speaker-" in block.body
    ]
    assert any("scout-speaker-user" in body and "You" in body for body in speaker_labels)
    assert any("scout-speaker-assistant" in body and "Scout" in body for body in speaker_labels)

    app.chat_input[0].set_value("We use PostgreSQL.").run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    followup = get_messages(cases[0]["id"], isolated_scout_database)
    assert [message["role"] for message in followup] == [
        "user", "assistant", "user", "assistant"
    ]
    assert followup[2]["content"] == "We use PostgreSQL."
    assert "PB-POSTGRES-01" in {
        card["id"] for card in followup[3]["evidence"]["playbooks"]
    }
    # Reopening has the same steps because the exact instructions are saved.
    assert any(
        "PostgreSQL sessions and waits" in expander.label for expander in app.expander
    )


def test_existing_streamlit_session_recovers_old_playbook_import(
    isolated_scout_database, monkeypatch
):
    """Hot reload should recover if Streamlit cached an older module version.

    The CLI import can succeed in a new Python process while an existing
    Streamlit server holds the previous version in its module cache.
    """
    from src import scout_playbooks

    assert hasattr(scout_playbooks, "checked_plan_response")
    monkeypatch.delattr(scout_playbooks, "checked_plan_response")
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert callable(scout_playbooks.checked_plan_response)



def test_precreated_case_followup_survives_sidebar_option_changes(
    isolated_scout_database, monkeypatch, tmp_path
):
    """Regression: case selector must not reset to New investigation.

    Clicking Start a new investigation, then submitting a question used to
    work, but a later chat follow-up could return to the empty start screen
    when Streamlit rebuilt the selectbox after case-list changes.
    """
    from src.scout_case_store import create_case

    data = tmp_path / "case_switch_incidents.csv"
    data.write_text(
        "id,vendor_name,title,started_at,url,components\n"
        "a,Demo Vendor,API 504 gateway timeout,2026-11-01,"
        "https://example.org/a,API\n"
        "b,Demo Vendor,Service failures after deployment,2026-11-02,"
        "https://example.org/b,API\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SCOUT_INCIDENT_CSV", str(data))
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]

    # The exact flow used in the reported bug: create a real empty case first.
    next(button for button in app.button
         if "Start a new investigation" in button.label).click().run(timeout=30)
    selected_id = app.session_state["scout_current_case"]
    assert selected_id != "__new_case__"

    entry = next(area for area in app.text_area
                 if area.label == "Describe your incident")
    entry.set_value(
        "Our API is returning 504 timeouts. Where should we start?"
    )
    next(button for button in app.button
         if button.label == "Start investigation").click().run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert app.session_state["scout_current_case"] == selected_id
    assert len(app.chat_input) == 1
    assert len(get_messages(selected_id, isolated_scout_database)) == 2
    assert get_case(selected_id, isolated_scout_database)["title"].startswith(
        "Our API is returning 504"
    ), "The placeholder title should be replaced by the first real message."

    # Another saved investigation makes the selectbox's option list change.
    # Its default MUST NOT replace the actively selected investigation.
    another = create_case("An unrelated new investigation",
                          isolated_scout_database)
    app.run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert app.session_state["scout_current_case"] == selected_id
    assert app.session_state["scout_case_picker"] == selected_id
    assert len(app.chat_input) == 1

    app.chat_input[0].set_value(
        "We deployed an update last night. Could it be related?"
    ).run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert app.session_state["scout_current_case"] == selected_id

    history = get_messages(selected_id, isolated_scout_database)
    assert [m["role"] for m in history] == [
        "user", "assistant", "user", "assistant"
    ]
    assert "deployed an update" in history[2]["content"]
    assert "PB-TIMELINE-01" in {
        card["id"] for card in history[3]["evidence"]["playbooks"]
    }
    assert not get_messages(another["id"], isolated_scout_database)
    assert len(app.chat_input) == 1
    assert not any(area.label == "Describe your incident"
                   for area in app.text_area)


def test_manual_sidebar_switch_still_opens_selected_investigation(
    isolated_scout_database
):
    """A user choosing a different case is different from a widget reset."""
    from src.scout_case_store import create_case, initialise_database

    initialise_database(isolated_scout_database)
    first = create_case("First case", isolated_scout_database)
    second = create_case("Second case", isolated_scout_database)
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    picker = next(box for box in app.selectbox
                  if box.label == "Your investigations")
    picker.set_value(first["id"]).run(timeout=30)
    assert not app.exception, [str(error.message) for error in app.exception]
    assert app.session_state["scout_current_case"] == first["id"]
    picker = next(box for box in app.selectbox
                  if box.label == "Your investigations")
    picker.set_value(second["id"]).run(timeout=30)
    assert app.session_state["scout_current_case"] == second["id"]
