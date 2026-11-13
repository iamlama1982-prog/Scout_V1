"""Curated technical reference retrieval for Project 3 (separate from incident evidence).

Only short, original, human-reviewable reference cards and official URLs are
stored here. No automatic web scraping, external API requests or execution.
A checked official page is guidance, not proof of a diagnosis or fix.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

CATALOGUE_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "official_guides.json"
ALLOWED_HOSTS = {
    "docs.aws.amazon.com",
    "kubernetes.io",
    "docs.cloud.google.com",
    "learn.microsoft.com",
    "www.postgresql.org",
    "developer.mozilla.org",
    "developers.cloudflare.com",
}
KB_ID_PATTERN = re.compile(r"KB-[A-Z0-9-]+\Z")


@dataclass
class KnowledgeIndex:
    records: pd.DataFrame
    vectorizer: TfidfVectorizer
    vectors: Any


def load_knowledge(path: str | Path = CATALOGUE_PATH) -> pd.DataFrame:
    """Validate the curated cards, source URLs and review metadata before use."""
    with Path(path).open(encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict) or not isinstance(payload.get("references"), list):
        raise ValueError("Knowledge catalogue must contain a references list.")
    required = {
        "id", "title", "publisher", "topics", "url", "summary",
        "diagnostic_checks", "reviewed_on", "review_status",
    }
    seen = set()
    rows = []
    for number, card in enumerate(payload["references"], start=1):
        if not isinstance(card, dict) or not required.issubset(card):
            raise ValueError(f"Invalid knowledge reference #{number}: missing required fields.")
        identifier = str(card["id"])
        if not KB_ID_PATTERN.fullmatch(identifier) or identifier in seen:
            raise ValueError(f"Invalid or duplicate knowledge ID: {identifier}")
        seen.add(identifier)
        parsed = urlparse(str(card["url"]).strip())
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
            raise ValueError(f"Knowledge source must be an approved official HTTPS page: {identifier}")
        if card["review_status"] != "official_source_checked":
            raise ValueError(f"Reference not checked against an official source: {identifier}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(card["reviewed_on"])):
            raise ValueError(f"Missing or invalid review date: {identifier}")
        checks = card["diagnostic_checks"]
        if not isinstance(checks, list) or not checks or not all(isinstance(x, str) and x.strip() for x in checks):
            raise ValueError(f"Reference has no usable diagnostic checks: {identifier}")
        text_fields = ["title", "publisher", "topics", "summary"]
        if any(not isinstance(card[key], str) or not card[key].strip() for key in text_fields):
            raise ValueError(f"Reference contains empty fields: {identifier}")
        # Author-written summaries, not copied documentation. Do not claim that
        # the source verifies a root cause or that the user runs this technology.
        search_text = " ".join([
            card["title"], card["topics"], card["topics"], card["summary"],
            " ".join(checks), card["publisher"],
        ])
        rows.append({
            "kb_id": identifier,
            "title": card["title"],
            "publisher": card["publisher"],
            "topics": card["topics"],
            "url": card["url"],
            "summary": card["summary"],
            "diagnostic_checks": checks,
            "reviewed_on": card["reviewed_on"],
            "applies_to": str(card.get("applies_to", "")).strip(),
            "search_text": search_text,
        })
    if not rows:
        raise ValueError("The technical knowledge catalogue is empty.")
    return pd.DataFrame(rows)


def build_knowledge_index(records: pd.DataFrame) -> KnowledgeIndex:
    """A small, independent TF-IDF index; no need for a hosted vector database."""
    if records.empty:
        raise ValueError("Cannot index an empty knowledge catalogue.")
    vectorizer = TfidfVectorizer(
        strip_accents="unicode", lowercase=True, stop_words="english",
        ngram_range=(1, 2), min_df=1, sublinear_tf=True, dtype=np.float32,
    )
    # Use the same TF-IDF idea as the incident index, but on official guides.
    vectors = vectorizer.fit_transform(records["search_text"].fillna("").astype(str))
    return KnowledgeIndex(records.reset_index(drop=True), vectorizer, vectors)


def retrieve_knowledge(
    question: str, index: KnowledgeIndex, *, k: int = 3, min_score: float = 0.10,
) -> list[dict]:
    """Return only the most related references, with separate KB IDs and scores."""
    if not question.strip() or k < 1:
        return []
    query = index.vectorizer.transform([question.strip()])
    if query.nnz == 0:
        return []
    scores = (index.vectors @ query.T).toarray().ravel()
    # Rank the guide scores from highest to lowest and keep at most k.
    candidates = scores.argsort()[::-1][:k]
    return [
        dict(index.records.iloc[int(i)].to_dict(), score=round(float(scores[i]), 4))
        for i in candidates if scores[i] >= min_score
    ]
