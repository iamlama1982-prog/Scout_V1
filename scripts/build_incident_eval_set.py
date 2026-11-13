"""Freeze a source-labelled Project 3 evaluation set BEFORE retrieval tuning.

This creates a reproducible *draft*. A human must review question wording,
source relevance and answerability before treating it as final assessment data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.incident_assistant import load_incidents, prepare_incidents


def make_questions(records: pd.DataFrame) -> pd.DataFrame:
    # Stable sampling across vendors. Avoid relying on whichever rows CSV lists first.
    eligible = records.loc[
        records["source_url"].ne("")
        & records["title"].str.len().between(28, 125)
        & records["started_at"].ne("")
    ].sort_values(["vendor", "title", "doc_id"])
    eligible = eligible.drop_duplicates(subset=["vendor"], keep="first")
    if len(eligible) < 12:
        raise ValueError("Need at least 12 distinct vendor incidents with linked titles and dates.")
    # Distributed deterministic selection rather than a cluster from the same vendor.
    indices = [round(i * (len(eligible) - 1) / 11) for i in range(12)]
    chosen = eligible.iloc[indices].reset_index(drop=True)
    questions = []
    for i, row in chosen.iterrows():
        if i < 4:
            question = f"Find the historical incident involving {row['title']}."
        elif i < 8:
            question = f"Did {row['vendor']} report an incident about {row['title']}?"
        else:
            question = f"When did {row['vendor']} report {row['title']}?"
        questions.append({
            "question_id": f"Q{i+1:02d}", "question": question,
            "answerable": True, "expected_doc_id": row["doc_id"],
            "expected_source_url": row["source_url"],
            "expected_answer_note": (
                f"Publisher record: {row['vendor']} — {row['title']}; "
                f"started_at={row['started_at']}. No verified fix details."
            ),
            "reviewed_by_human": False,
        })
    exclusions = [
        "Who was the on-call engineer responsible for the latest internal outage?",
        "What precise internal troubleshooting commands fixed the database failure?",
        "How much revenue was lost because of these incidents?",
    ]
    for i, question in enumerate(exclusions, start=13):
        questions.append({
            "question_id": f"Q{i:02d}", "question": question, "answerable": False,
            "expected_doc_id": "", "expected_source_url": "",
            "expected_answer_note": "Not present in public status-page incident metadata; decline to invent.",
            "reviewed_by_human": False,
        })
    return pd.DataFrame(questions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/incident_taxonomy/snapshot_2026-10-23/incidents.csv"))
    parser.add_argument("--out", type=Path, default=Path("evals/incident_eval_questions.csv"))
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"Evaluation set already exists: {args.out}. Do not silently rewrite it.")
    records = prepare_incidents(load_incidents(args.data))
    questions = make_questions(records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    questions.to_csv(args.out, index=False)
    print(f"Created {len(questions)} draft questions: {args.out}")
    print("Review each question/source against the original record, then freeze BEFORE tuning.")


if __name__ == "__main__":
    main()
