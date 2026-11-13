"""The three main course notebooks should run top to bottom from a fresh kernel.

This uses the *committed, real measured summary tables*. The original SevAnalysis
CSV stays excluded from Git. It tests the notebook flow, not new model scores.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

from src import incident_assistant

ROOT = Path(__file__).resolve().parents[1]
CORE_NOTEBOOKS = (
    "01_framing_and_baseline.ipynb",
    "02_rag_build.ipynb",
    "03_evaluation.ipynb",
)


@pytest.mark.parametrize("filename", CORE_NOTEBOOKS)
def test_course_notebook_executes_in_order_without_private_csv(
    filename, tmp_path, monkeypatch,
):
    """Anyone can inspect the main narrative without a private local data file."""
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(incident_assistant, "LOCAL_CSV", tmp_path / "missing.csv")

    notebook = json.loads(
        (ROOT / "notebooks" / filename).read_text(encoding="utf-8")
    )
    assert notebook["nbformat"] == 4
    assert notebook["cells"][0]["cell_type"] == "markdown"
    assert any(cell["cell_type"] == "code" for cell in notebook["cells"])

    namespace = {"__name__": "__main__", "display": lambda obj: None}
    for number, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = cell["source"]
        if isinstance(source, list):
            source = "".join(source)
        exec(compile(source, f"{filename}:cell-{number}", "exec"), namespace)


def test_data_charts_and_evaluation_evidence_are_in_the_first_three_notebooks():
    def contents(name):
        notebook = json.loads(
            (ROOT / "notebooks" / name).read_text(encoding="utf-8")
        )
        return "\n".join(
            "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
            for c in notebook["cells"]
        )

    framing = contents(CORE_NOTEBOOKS[0])
    build = contents(CORE_NOTEBOOKS[1])
    report = contents(CORE_NOTEBOOKS[2])
    assert "source_eda_missingness.png" in framing
    assert "source_eda_title_lengths.png" in framing
    assert "retrieval_baseline_2026-11.csv" in framing
    assert "build_messages" in build
    assert "select_playbooks" in build
    assert "answer_with_llm" in build
    assert "4/12" in report
    assert "53,453.8" in report
    assert "not a truly untouched" in framing
