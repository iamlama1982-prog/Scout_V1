"""Project 3 retrieval comparison on the same, pre-frozen question set.

Does not claim to grade generated answers automatically. Manually inspect LLM
answers for factual accuracy, citation quality, appropriate refusals and cost.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.incident_assistant import build_index, evaluate_retrieval, load_incidents, prepare_incidents


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=Path("data/raw/incident_taxonomy/snapshot_2026-10-23/incidents.csv"))
    p.add_argument("--questions", type=Path, default=Path("evals/incident_eval_questions_provisional.csv"))
    p.add_argument("--out", type=Path, default=Path("outputs/project3/retrieval_evaluation.csv"))
    p.add_argument("--k", type=int, default=5)
    args = p.parse_args()
    if not args.questions.exists():
        raise SystemExit("No frozen questions. Run scripts/build_incident_eval_set.py first and review them.")
    questions = pd.read_csv(args.questions, keep_default_na=False)
    if len(questions) < 15 or sum(questions["answerable"].astype(str).str.lower().isin(["false", "0", "no"])) < 3:
        raise SystemExit("Rubric requires >=15 questions including >=3 out-of-scope questions.")
    if not questions["reviewed_by_human"].astype(str).str.lower().eq("true").all():
        print("WARNING: one or more questions still need a human review before a final rubric claim.")
    records = prepare_incidents(load_incidents(args.data))
    result = evaluate_retrieval(questions, build_index(records), k=args.k)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False)
    print(f"Saved raw evaluation: {args.out}")
    for name, group in result[result["answerable"]].groupby("approach"):
        print(f"{name} hit@{args.k}: {group['hit_at_k'].astype(float).mean():.1%}, "
              f"mean retrieval latency: {group['latency_seconds'].mean():.3f}s")
    print("LLM answer accuracy, citation quality and API cost still require a separate measured run.")


if __name__ == "__main__":
    main()
