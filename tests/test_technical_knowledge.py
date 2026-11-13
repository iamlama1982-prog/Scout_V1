"""Deterministic tests for technical reference provenance and RAG grounding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.incident_assistant import answer_with_llm, build_messages
from src.technical_knowledge import (
    CATALOGUE_PATH, build_knowledge_index, load_knowledge, retrieve_knowledge,
)


def test_official_library_has_checked_unique_sources():
    docs = load_knowledge()
    assert len(docs) >= 15
    assert docs["kb_id"].is_unique
    assert docs["url"].str.startswith("https://").all()
    assert docs["reviewed_on"].notna().all()
    assert docs["diagnostic_checks"].map(len).ge(1).all()


def test_retrieve_relevant_http_timeout_guide():
    index = build_knowledge_index(load_knowledge())
    hits = retrieve_knowledge("Our API returns 504 Gateway Timeout from an upstream proxy", index, k=5)
    assert hits
    assert "KB-MDN-504-01" in {item["kb_id"] for item in hits}


def test_retrieve_database_reference():
    index = build_knowledge_index(load_knowledge())
    hits = retrieve_knowledge("PostgreSQL sessions are blocked and queries are slow", index, k=4)
    assert "KB-PG-STATS-01" in {item["kb_id"] for item in hits}


def test_build_messages_distinguishes_evidence_types():
    index = build_knowledge_index(load_knowledge())
    guides = retrieve_knowledge("API 504 timeout", index, k=3)
    incidents = [
        {"doc_id": "INC-aaaaaaaaaaaa", "vendor": "Demo status page",
         "title": "API gateway timeout", "started_at": "2026-11-01",
         "impact": "unknown", "status": "resolved", "components": "API"}
    ]
    messages = build_messages("Why did the API time out?", incidents, guides)
    assert "Never guess a root cause" in messages[0]["content"]
    assert "HISTORICAL INCIDENTS" in messages[0]["content"]
    assert "TECHNICAL REFERENCES" in messages[0]["content"]
    assert "[INC-aaaaaaaaaaaa]" in messages[1]["content"]
    assert f"[{guides[0]['kb_id']}]" in messages[1]["content"]
    assert "Official guidance describes diagnostic methods" in messages[0]["content"]
    assert "You are Scout" in messages[0]["content"]
    assert "Where I'd start" in messages[0]["content"]
    assert "Do not use loosely related historical incidents" in messages[0]["content"]


def test_can_answer_using_guidance_without_matching_incidents():
    guide = retrieve_knowledge(
        "HTTP 429 rate limit Retry-After", build_knowledge_index(load_knowledge()), k=2
    )[0]
    messages = build_messages("What should I check first?", [], [guide])
    assert "No sufficiently similar published incidents" in messages[1]["content"]
    assert guide["kb_id"] in messages[1]["content"]


def test_no_evidence_rejected():
    with pytest.raises(ValueError, match="No supporting"):
        build_messages("Anything", [], [])


def test_reject_unapproved_or_duplicate_knowledge_source(tmp_path: Path):
    payload = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    payload["references"][0]["url"] = "https://docs.aws.amazon.com.evil.example/fake"
    corrupt = tmp_path / "unapproved.json"
    corrupt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="approved official"):
        load_knowledge(corrupt)
    payload["references"][0]["url"] = "https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html"
    payload["references"][1]["id"] = payload["references"][0]["id"]
    corrupt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_knowledge(corrupt)


def test_invalid_document_citation_is_removed(monkeypatch):
    from types import SimpleNamespace
    import openai

    class FakeChatCompletions:
        def create(self, **kwargs):
            assert any("TECHNICAL REFERENCES" in m["content"] for m in kwargs["messages"])
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content="Review relevant error data [KB-MDN-504-01]. Fabricated [KB-FAKE-01]."
                ))],
                usage=SimpleNamespace(total_tokens=80, prompt_tokens=60, completion_tokens=20),
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    docs = load_knowledge()
    guide = docs.loc[docs["kb_id"].eq("KB-MDN-504-01")].iloc[0].to_dict()
    result = answer_with_llm(
        "504 timeout", [], api_key="ollama", model="test",
        base_url="http://localhost:11434/v1", knowledge_results=[guide],
    )
    assert "KB-MDN-504-01" in result["cited_ids"]
    assert "KB-FAKE-01" not in result["answer"]
    assert "KB-FAKE-01" in result["removed_citation_ids"]
    assert "unverified reference removed" not in result["answer"]
