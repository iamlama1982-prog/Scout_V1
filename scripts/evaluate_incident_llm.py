"""Measure RAG answers over frozen questions; leaves human grading blank.

Requires a paid API key or a local OpenAI-compatible Ollama server. Explicitly
pass per-million token prices for an accurate hosted cost estimate. LLM output
must be reviewed manually; automatic citation detection is not a truth metric.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from src.incident_assistant import (
    answer_with_llm, build_index, evidence_only_answer,
    historical_evidence_for_answer, load_incidents, prepare_incidents, retrieve,
)
from src.technical_knowledge import (
    build_knowledge_index, load_knowledge, retrieve_knowledge,
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=Path("data/raw/incident_taxonomy/snapshot_2026-10-23/incidents.csv"))
    p.add_argument("--questions", type=Path, default=Path("evals/incident_eval_questions_provisional.csv"))
    p.add_argument("--out", type=Path, default=Path("outputs/project3/llm_answers_for_manual_review.csv"))
    p.add_argument("--model", default=os.environ.get("OPS_LLM_MODEL", "gpt-4.1-mini"))
    p.add_argument("--base-url", default=os.environ.get("OPS_LLM_BASE_URL"))
    p.add_argument("--input-price", type=float, default=0.0, help="USD per 1 million prompt tokens")
    p.add_argument("--output-price", type=float, default=0.0, help="USD per 1 million completion tokens")
    p.add_argument("--with-knowledge", action="store_true",
                   help="Add reviewed official guidance; default stays incident-only for baseline comparison")
    args = p.parse_args()
    # Reject a duplicate output before making any slow model requests.
    if args.out.exists():
        raise SystemExit(
            f"Refusing to overwrite earlier evaluation: {args.out}. "
            "Choose a different --out path."
        )
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if args.base_url and "localhost" in args.base_url and not api_key:
        api_key = "ollama"
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY (or --base-url pointing at local Ollama).")
    questions = pd.read_csv(args.questions, keep_default_na=False)
    if len(questions) < 15:
        raise SystemExit("Expected a pre-frozen set of at least 15 questions.")
    print(
        f"Loading and indexing the incident dataset for {len(questions)} questions...",
        flush=True,
    )
    index = build_index(prepare_incidents(load_incidents(args.data)))
    knowledge_index = build_knowledge_index(load_knowledge()) if args.with_knowledge else None
    print(
        f"Ready: {len(index.records):,} incidents. "
        f"Model: {args.model}. Technical guidance: {'on' if args.with_knowledge else 'off'}.",
        flush=True,
    )
    rows = []
    for number, item in enumerate(questions.to_dict(orient="records"), start=1):
        print(
            f"[{number}/{len(questions)}] Starting {item['question_id']}: "
            f"{str(item['question'])[:85]}",
            flush=True,
        )
        evidence = retrieve(item["question"], index)
        supporting_incidents = historical_evidence_for_answer(item["question"], evidence)
        guides = (
            retrieve_knowledge(item["question"], knowledge_index)
            if knowledge_index is not None else []
        )
        if supporting_incidents or guides:
            result = answer_with_llm(item["question"], supporting_incidents,
                                     api_key=api_key, model=args.model, base_url=args.base_url,
                                     knowledge_results=guides)
        else:
            result = {"answer": evidence_only_answer([]), "cited_ids": [],
                      "tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
                      "seconds": 0.0}
        dollars = (result["prompt_tokens"] * args.input_price
                   + result["completion_tokens"] * args.output_price) / 1_000_000
        rows.append({
            "question_id": item["question_id"], "question": item["question"],
            "answerable": item["answerable"], "expected_source": item["expected_doc_id"],
            "retrieved_ids": ";".join(r["doc_id"] for r in evidence),
            "historical_ids_used_in_answer": ";".join(r["doc_id"] for r in supporting_incidents),
            "technical_reference_ids": ";".join(g["kb_id"] for g in guides),
            "knowledge_enabled": args.with_knowledge,
            "answer": result["answer"], "cited_ids": ";".join(result["cited_ids"]),
            "latency_seconds": result["seconds"], "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "estimated_cost_usd": round(dollars, 8),
            "manual_correct": "", "manual_citations_valid": "", "manual_refusal_ok": "",
            "manual_next_checks_useful": "", "manual_technical_guidance_supported": "",
            "failure_type": "", "review_notes": "",
        })
        print(
            f"[{number}/{len(questions)}] Finished {item['question_id']} "
            f"in {result['seconds']:.1f}s; "
            f"{len(result['cited_ids'])} valid citation(s).",
            flush=True,
        )
    frame = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)
    print(f"Created manual review sheet: {args.out}")
    print(f"Total time: {frame.latency_seconds.sum():.2f}s; mean: {frame.latency_seconds.mean():.2f}s")
    if args.input_price or args.output_price:
        print("Estimated API cost: $" + format(frame.estimated_cost_usd.sum(), ".4f"))
    else:
        print("API cost NOT estimated; provide --input-price and --output-price for the selected model.")
    print("Review accuracy, source validity, refusals and retrieval/generation failures manually.")


if __name__ == "__main__":
    main()
