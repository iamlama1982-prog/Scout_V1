"""The in-app evidence-led presentation and real human-review workflow."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.scout_case_store import (
    get_messages, get_verification_reviews, list_cases,
)

ROOT = Path(__file__).resolve().parents[1]


def test_presentation_renders_actual_chart_assets_without_ollama(monkeypatch, tmp_path):
    monkeypatch.setenv("SCOUT_CASE_DB", str(tmp_path / "presentation.db"))
    app = AppTest.from_file(str(ROOT / "pages" / "Presentation.py")).run(timeout=40)
    assert not app.exception, [str(e.message) for e in app.exception]
    assert len(app.tabs) == 8
    assert not any("speaker notes" in x.label.lower() for x in app.expander)
    assert any("The evidence behind the design" in x.body for x in app.markdown)
    assert any("real Live Scout" in b.label for b in app.button)
    # A tab renders only its CURRENTLY selected slide; selecting EDA slides
    # must actually load the original saved figures.
    assert len(app.get("image")) >= 2
    data = next(x for x in app.selectbox if x.key == "scout_story_data")
    data.set_value(4).run(timeout=40)
    assert not app.exception
    assert len(app.get("image")) >= 3
    data = next(x for x in app.selectbox if x.key == "scout_story_data")
    data.set_value(5).run(timeout=40)
    assert not app.exception
    assert len(app.get("image")) >= 3


def test_all_saved_figures_are_reused():
    from importlib.util import module_from_spec, spec_from_file_location

    src = (ROOT / "pages" / "Presentation.py").read_text(encoding="utf-8")
    expected = [
        "source_eda_missingness.png",
        "source_eda_title_lengths.png",
        "source_eda_vendor_coverage.png",
        "source_eda_monthly_coverage.png",
        "source_eda_impact_labels.png",
        "retrieval_hit_at_5.svg",
        "retrieval_query_latency.svg",
        "llm_provisional_findings.svg",
    ]
    for name in expected:
        assert name in src
        assert (ROOT / "reports" / name).is_file()
    assert "72.94" in src
    assert "4/12" in src
    assert "0.007" in src
    assert "independent human-approved" in src


def test_entrypoint_retains_real_scout_navigation():
    content = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"pages/Presentation.py"' in content
    assert '"pages/Scout.py"' in content
    assert "default=True" in content
    assert 'position="top"' in content


def test_human_review_submission_changes_status_not_original_answer(
    monkeypatch, tmp_path,
):
    db = tmp_path / "human_check_demo.db"
    monkeypatch.setenv("SCOUT_CASE_DB", str(db))
    sample = tmp_path / "incidents.csv"
    sample.write_text(
        "id,vendor_name,title,started_at,url,components\n"
        "a,Demo Vendor,API 504 gateway timeout after deployment,2026-11-01,"
        "https://example.org/status,API\n"
        "b,Demo Service,Checkout intermittent errors,2026-11-02,"
        "https://example.org/checkout,Checkout\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SCOUT_INCIDENT_CSV", str(sample))

    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=40)
    assert not app.exception, [str(e.message) for e in app.exception]
    next(x for x in app.selectbox if x.label == "How would you like Scout to help?").set_value(
        "Evidence only (no LLM)"
    ).run(timeout=40)
    next(x for x in app.text_area if x.label == "Describe your incident").set_value(
        "Our API returns 504 timeouts after a deployment."
    )
    next(x for x in app.button if x.label == "Start investigation").click().run(timeout=40)
    assert not app.exception, [str(e.message) for e in app.exception]
    case = list_cases(db)[0]
    answer = get_messages(case["id"], db)[1]["content"]

    # Select a concrete unsupported conclusion, not a wholesale 'bad answer' grade.
    next(x for x in app.selectbox if x.label == "What did your check establish?").set_value(
        "not_supported"
    )
    next(x for x in app.text_area if x.label == "What exactly did you check and find?").set_value(
        "I compared the deployment and error timestamps; the errors started much later."
    )
    next(x for x in app.button if x.label == "Save review to case history").click().run(timeout=40)
    assert not app.exception, [str(e.message) for e in app.exception]
    reviews = get_verification_reviews(case["id"], db)
    assert len(reviews) == 1
    assert reviews[0]["outcome"] == "not_supported"
    assert "errors started much later" in reviews[0]["detail"]
    assert get_messages(case["id"], db)[1]["content"] == answer
    assert any("Finding not supported" in x.body for x in app.markdown)

    # A later, more specific check adds a NEW record; the old one stays.
    next(x for x in app.selectbox if x.label == "What did your check establish?").set_value(
        "supported"
    )
    next(x for x in app.text_area if x.label == "What exactly did you check and find?").set_value(
        "I confirmed the gateway 504s align with upstream response delay in our traces."
    )
    next(x for x in app.button if x.label == "Save review to case history").click().run(timeout=40)
    assert not app.exception, [str(e.message) for e in app.exception]
    reviews = get_verification_reviews(case["id"], db)
    assert [r["outcome"] for r in reviews] == ["not_supported", "supported"]
    assert get_messages(case["id"], db)[1]["content"] == answer
