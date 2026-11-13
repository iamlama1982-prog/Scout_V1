"""Publish a safe, assessable copy of local evaluation results.

The app's raw data, saved cases and unreviewed generated answers are not
committed. This exporter deliberately writes only public-source retrieval
results or manually entered scoring flags. It never publishes API keys,
SQLite case history, raw incident data or complete LLM drafts.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


RETRIEVAL_COLUMNS = [
    "question_id", "question", "answerable", "approach",
    "expected_doc_id", "expected_source_url", "retrieved_ids",
    "hit_at_k", "latency_seconds", "reviewed_by_human",
]

LLM_SCORE_COLUMNS = [
    "question_id", "answerable", "manual_correct",
    "manual_citations_valid", "manual_refusal_ok", "manual_next_checks_useful",
    "manual_technical_guidance_supported", "latency_seconds",
    "prompt_tokens", "completion_tokens", "estimated_cost_usd",
]


def publish_retrieval(raw_results: pd.DataFrame, questions: pd.DataFrame) -> pd.DataFrame:
    """Add the question IDs and expected links to the raw per-query output."""
    needed = {"question", "approach", "expected_doc_id", "retrieved_ids",
              "hit_at_k", "latency_seconds"}
    if not needed.issubset(raw_results):
        raise ValueError(f"Retrieval file is missing: {sorted(needed - set(raw_results))}")
    labels = {"question_id", "question", "answerable",
              "expected_doc_id", "expected_source_url", "reviewed_by_human"}
    if not labels.issubset(questions):
        raise ValueError(f"Question file is missing: {sorted(labels - set(questions))}")
    if not questions["question"].is_unique:
        raise ValueError("Question wording must be unique before export.")
    # The raw evaluator also stores "answerable". Use the validated question
    # set's value to avoid duplicate answerable_x / answerable_y columns.
    result = raw_results.drop(columns=["answerable"], errors="ignore").merge(
        questions[list(labels)], on=["question", "expected_doc_id"],
        how="left", validate="many_to_one",
    )
    if result["question_id"].isna().any():
        raise ValueError("Some evaluated questions do not match the supplied question set.")
    return result[RETRIEVAL_COLUMNS].sort_values(["question_id", "approach"]).reset_index(drop=True)


def publish_llm_scores(raw_answers: pd.DataFrame) -> pd.DataFrame:
    """Exclude generated answer text; retain only human-entered marks and timing."""
    if not set(LLM_SCORE_COLUMNS).issubset(raw_answers):
        missing = sorted(set(LLM_SCORE_COLUMNS) - set(raw_answers))
        raise ValueError(f"LLM review file is missing: {missing}")
    grade_cols = ["manual_correct", "manual_citations_valid",
                  "manual_refusal_ok", "manual_next_checks_useful",
                  "manual_technical_guidance_supported"]
    marked = raw_answers[grade_cols].astype(str).apply(
        lambda col: col.str.strip().str.lower().isin(
            ["true", "false", "yes", "no", "1", "0"]
        )
    )
    if not marked.any().any():
        raise ValueError(
            "No manual ratings found. Do not publish an unscored model output as accuracy evidence."
        )
    return raw_answers[LLM_SCORE_COLUMNS].copy().sort_values("question_id")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=["retrieval", "llm"], required=True)
    parser.add_argument(
        "--questions", type=Path, default=Path("evals/incident_eval_questions.csv")
    )
    parser.add_argument("--input", type=Path, required=True,
                        help="Locally generated evaluation CSV")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.out is None:
        args.out = Path(
            "reports/retrieval_full_details.csv" if args.kind == "retrieval"
            else "reports/llm_manual_scores.csv"
        )
    if args.out.exists():
        raise SystemExit(f"Refusing to overwrite existing evidence: {args.out}")
    if not args.input.exists():
        raise SystemExit(f"Raw evaluation CSV not found: {args.input}")
    raw = pd.read_csv(args.input, keep_default_na=False)

    if args.kind == "retrieval":
        if not args.questions.exists():
            raise SystemExit(f"Question file not found: {args.questions}")
        questions = pd.read_csv(args.questions, keep_default_na=False)
        exported = publish_retrieval(raw, questions)
    else:
        exported = publish_llm_scores(raw)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    exported.to_csv(args.out, index=False)
    print(f"Created course evidence: {args.out}")
    print(f"Rows: {len(exported)}")
    if args.kind == "retrieval":
        approved = exported["reviewed_by_human"].astype(str).str.lower().eq("true")
        print(f"Human-reviewed rows: {int(approved.sum())}/{len(exported)}")
        if not approved.all():
            print("STATUS: PROVISIONAL. Source review must be finished before final claims.")
    else:
        print("Published scoring flags and timing only, NOT raw model-generated answers.")
        print("Check all generated files for private information before git add/commit.")


if __name__ == "__main__":
    main()
