"""The audience sees the actual development choices before the live Scout demo."""

from html import unescape
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.scout_pitch_story import JOURNEY, TOTAL_CHAPTERS

ROOT = Path(__file__).resolve().parents[1]


def pitch():
    page = AppTest.from_file(str(ROOT / "pages" / "Pitch.py")).run(timeout=40)
    assert not page.exception, [str(item.message) for item in page.exception]
    return page


def test_journey_has_five_decisions_and_no_embedded_speaking_notes():
    assert TOTAL_CHAPTERS == 5
    assert [step["label"] for step in JOURNEY] == [
        "The problem", "The information", "The turning point", "The build", "The product",
    ]
    assert all(step["example"] and step["decision"] and "notes" not in step
               for step in JOURNEY)
    script = (ROOT / "docs/presenter_speaking_notes.md").read_text(encoding="utf-8")
    assert "PostgreSQL" in script and "SQLite" in script
    app = pitch()
    assert not any("speaking notes" in x.label.lower() for x in app.expander)


def test_pitch_journey_clicks_through_all_five_turning_points():
    app = pitch()
    assert app.session_state["scout_pitch_chapter"] == 0
    assert any("Where on earth do I start?" in item.body for item in app.markdown)

    for i in range(1, TOTAL_CHAPTERS):
        next_button = next(b for b in app.button if b.label == "Next turning point →")
        next_button.click().run(timeout=40)
        assert not app.exception, [str(item.message) for item in app.exception]
        assert app.session_state["scout_pitch_chapter"] == i
        assert any(
            JOURNEY[i]["heading"] in unescape(item.body)
            for item in app.markdown
        )

    assert next(b for b in app.button if b.label == "Next turning point →").disabled
    assert any(b.label == "▶ Enter the live Scout demo" for b in app.button)
    next(b for b in app.button if b.label == "← Previous").click().run(timeout=40)
    assert app.session_state["scout_pitch_chapter"] == TOTAL_CHAPTERS - 2
    assert not app.session_state.get("scout_pitch_mode", False)


def test_pitch_has_an_explicit_one_minute_commercial_close():
    app = pitch()
    section = next(r for r in app.radio if r.label == "Presentation section")
    section.set_value("Beyond the prototype").run(timeout=40)
    assert not app.exception, [str(item.message) for item in app.exception]
    assert any("From prototype to product" in item.body for item in app.markdown)
    assert any("The next step is not more AI" in item.body for item in app.markdown)
    assert not any("closing notes" in x.label.lower() for x in app.expander)
    next(b for b in app.button
         if b.label == "← Back to Intro to Scout").click().run(timeout=40)
    assert not app.exception, [str(item.message) for item in app.exception]
    assert app.session_state["scout_pitch_section"] == "Intro to Scout"
    assert app.session_state["scout_pitch_chapter"] == 0
