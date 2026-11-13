"""No external data, network access or paid API is required for these checks."""

from __future__ import annotations

import pandas as pd
import pytest

from src.incident_assistant import (
    build_index, build_messages, clean_text, evaluate_retrieval,
    historical_evidence_for_answer, investigation_focus, is_cross_symptom_question,
    keyword_search,
    load_incidents, prepare_incidents, retrieve, safe_http_url,
)
from scripts.build_incident_eval_set import make_questions


def sample_raw():
    return pd.DataFrame([
        {"id": "abc", "vendor_name": "Blue Cloud", "title": "API requests timing out in Europe", "started_at": "2026-01-01T10:00:00Z", "impact": "major", "url": "https://status.bluecloud.example/incidents/abc", "components": "API"},
        {"id": "def", "vendor_name": "Green Host", "title": "Database connections fail in Amsterdam", "started_at": "2026-01-02T08:00:00Z", "url": "https://status.greenhost.example/def", "components": "Postgres"},
        {"id": "ghi", "vendor_name": "Orange App", "title": "Delayed notifications in mobile application", "started_at": "2026-01-03T09:00:00Z", "url": "https://status.orangeapp.example/ghi"},
    ])


def test_required_columns_are_checked():
    with pytest.raises(ValueError, match="vendor"):
        prepare_incidents(pd.DataFrame({"title": ["Some problem"]}))


def test_prepare_preserves_ids_and_deduplicates():
    raw = pd.concat([sample_raw(), sample_raw().iloc[[0]]], ignore_index=True)
    records = prepare_incidents(raw)
    assert len(records) == 3
    assert records.loc[0, "doc_id"].startswith("INC-")
    assert records.loc[0, "doc_id"] == prepare_incidents(sample_raw()).loc[0, "doc_id"]
    assert records.loc[0, "vendor"] == "Blue Cloud"


def test_clean_text_masks_contact_details():
    assert "alex@example.com" not in clean_text("Contact alex@example.com regarding failures")
    assert safe_http_url("javascript:alert(1)") == ""
    assert safe_http_url("https://status.example.com/incidents/a")


def test_tfidf_returns_relevant_incident():
    index = build_index(prepare_incidents(sample_raw()))
    results = retrieve("API requests timeout in Europe", index, k=2)
    assert results and results[0]["vendor"] == "Blue Cloud"


def test_keyword_baseline_and_out_of_domain():
    records = prepare_incidents(sample_raw())
    found = keyword_search("database connections", records, k=3)
    assert found and found[0]["vendor"] == "Green Host"
    assert retrieve("", build_index(records)) == []


def test_prompt_says_not_to_invent_root_causes():
    index = build_index(prepare_incidents(sample_raw()))
    docs = retrieve("API timeout", index)
    messages = build_messages("Who was on call?", docs)
    assert "Never guess a root cause" in messages[0]["content"]
    assert docs[0]["doc_id"] in messages[1]["content"]


def test_evaluation_scores_expected_source():
    index = build_index(prepare_incidents(sample_raw()))
    expected = index.records.iloc[0]["doc_id"]
    questions = pd.DataFrame([
        {"question": "API requests timing out in Europe", "expected_doc_id": expected, "answerable": True},
        {"question": "Who was on call?", "expected_doc_id": "", "answerable": False},
    ])
    outcome = evaluate_retrieval(questions, index)
    assert len(outcome) == 4
    assert outcome.loc[outcome["approach"].eq("tfidf") & outcome["answerable"], "hit_at_k"].iloc[0] == True


def test_generator_needs_reliable_source_evidence():
    with pytest.raises(ValueError, match="12 distinct"):
        make_questions(prepare_incidents(sample_raw()))



def test_cross_symptom_evidence_filter_does_not_conflate_single_issue_reports():
    question = (
        "We've had slow database connections, API timeouts and failed customer "
        "transactions. Could these be connected?"
    )
    hits = [
        {"title": "API Timeout", "components": "API", "doc_id": "INC-111111111111"},
        {"title": "Database connection errors", "components": "Database", "doc_id": "INC-222222222222"},
        {"title": "Database connection saturation affecting API responses", "components": "Database API",
         "doc_id": "INC-333333333333"},
    ]
    relevant = historical_evidence_for_answer(question, hits)
    assert [r["doc_id"] for r in relevant] == ["INC-333333333333"]
    # The caller retains the original lexical search results separately.
    assert len(hits) == 3


def test_simple_single_symptom_retrieval_is_preserved():
    hits = [{"title": "API Timeout", "components": "", "doc_id": "INC-111111111111"}]
    assert historical_evidence_for_answer("Why is our API timing out?", hits) == hits


def test_linked_symptom_analysis_asks_for_a_testable_shared_cause():
    question = (
        "Our database is slow, APIs time out and payments fail. "
        "Could these be related?"
    )
    focus = investigation_focus(question)
    assert "DIRECTLY" in focus
    assert "shared dependency" in focus
    assert "support or weaken" in focus
    assert "Do NOT assume" in focus
    messages = build_messages(
        question,
        [],
        [{"kb_id": "KB-MDN-504-01", "publisher": "MDN Web Docs",
          "title": "HTTP 504 Gateway Timeout", "summary": "Gateway timeout",
          "diagnostic_checks": ["Inspect upstream latency"],
          "applies_to": "HTTP gateway", "reviewed_on": "2026-11-09"}],
    )
    assert "INVESTIGATION FOCUS" in messages[1]["content"]
    assert "dependency mapping" in messages[1]["content"]


def test_no_causal_context_gets_general_prioritised_checks():
    focus = investigation_focus("How do I investigate a Kubernetes CrashLoopBackOff?")
    assert "Answer the actual question first" in focus
    assert "what observation" in focus


def test_database_connections_alone_are_not_mistaken_for_a_shared_cause_question():
    question = "Why are our database connections timing out?"
    assert not is_cross_symptom_question(question)
    assert "shared dependency" not in investigation_focus(question)


def test_shared_cause_guard_requires_more_than_one_symptom_area():
    assert not is_cross_symptom_question("Could our database connection problems be related?")
    assert is_cross_symptom_question(
        "Could database failures, API timeouts and transaction errors be connected?"
    )
