"""Course evidence export: keep results visible without leaking raw model drafts."""

import pandas as pd
import pytest

from scripts.export_course_evidence import publish_llm_scores, publish_retrieval


def test_retrieval_export_has_source_ids_and_retrieval_evidence():
    questions = pd.DataFrame([
        {
            "question_id": "Q01", "question": "Find a DNS failure",
            "answerable": True, "expected_doc_id": "INC-example",
            "expected_source_url": "https://example.com/public-incident",
            "reviewed_by_human": False,
        }
    ])
    raw = pd.DataFrame([
        {
            "question": "Find a DNS failure", "approach": "tfidf",
            "answerable": True,
            "expected_doc_id": "INC-example", "retrieved_ids": "INC-other;INC-example",
            "hit_at_k": True, "latency_seconds": 0.018,
        },
        {
            "question": "Find a DNS failure", "approach": "keyword",
            "answerable": True,
            "expected_doc_id": "INC-example", "retrieved_ids": "INC-other",
            "hit_at_k": False, "latency_seconds": 0.35,
        },
    ])
    frame = publish_retrieval(raw, questions)
    assert len(frame) == 2
    assert frame["question_id"].tolist() == ["Q01", "Q01"]
    assert frame["approach"].tolist() == ["keyword", "tfidf"]
    assert frame["hit_at_k"].tolist() == [False, True]
    assert frame["expected_source_url"].iloc[0] == "https://example.com/public-incident"
    assert not frame["reviewed_by_human"].all()


def test_retrieval_export_rejects_unmatched_ground_truth():
    questions = pd.DataFrame([
        {
            "question_id": "Q01", "question": "Question",
            "answerable": True, "expected_doc_id": "INC-actual",
            "expected_source_url": "https://example.com", "reviewed_by_human": False,
        }
    ])
    raw = pd.DataFrame([
        {
            "question": "Question", "approach": "keyword",
            "expected_doc_id": "INC-different", "retrieved_ids": "",
            "hit_at_k": False, "latency_seconds": 0.1,
        }
    ])
    with pytest.raises(ValueError, match="do not match"):
        publish_retrieval(raw, questions)


def test_llm_export_never_copies_raw_answer_or_private_notes():
    raw = pd.DataFrame([
        {
            "question_id": "Q13", "answerable": False,
            "answer": "PRIVATE MODEL DRAFT - DO NOT COMMIT",
            "review_notes": "PRIVATE REVIEW NOTE - DO NOT COMMIT",
            "manual_correct": "yes", "manual_citations_valid": "yes",
            "manual_refusal_ok": "yes", "manual_next_checks_useful": "",
            "manual_technical_guidance_supported": "",
            "latency_seconds": 3.4, "prompt_tokens": 100,
            "completion_tokens": 80, "estimated_cost_usd": 0.0,
        }
    ])
    result = publish_llm_scores(raw)
    assert "answer" not in result
    assert "review_notes" not in result
    assert result.iloc[0]["manual_refusal_ok"] == "yes"
    assert "PRIVATE" not in result.to_csv(index=False)


def test_llm_export_refuses_to_publish_ungraded_answers_as_accuracy():
    raw = pd.DataFrame([
        {
            "question_id": "Q01", "answerable": True,
            "manual_correct": "", "manual_citations_valid": "",
            "manual_refusal_ok": "", "manual_next_checks_useful": "",
            "manual_technical_guidance_supported": "",
            "latency_seconds": 8.2, "prompt_tokens": 100,
            "completion_tokens": 80, "estimated_cost_usd": 0.0,
        }
    ])
    with pytest.raises(ValueError, match="No manual ratings"):
        publish_llm_scores(raw)
