"""The real EDA run's notebook outputs must survive explanatory edits."""

import json
from pathlib import Path

import pytest

from scripts.merge_eda_execution import merge_execution


def save_notebook(path: Path, cells: list[dict]) -> None:
    path.write_text(json.dumps({"cells": cells, "nbformat": 4,
                                "nbformat_minor": 5}), encoding="utf-8")


def markdown(identifier: str, content: str) -> dict:
    return {"id": identifier, "cell_type": "markdown",
            "metadata": {}, "source": [content]}


def code(identifier: str, source: str, count=None, outputs=None) -> dict:
    return {"id": identifier, "cell_type": "code", "source": [source],
            "metadata": {}, "execution_count": count,
            "outputs": [] if outputs is None else outputs}


def test_merge_preserves_real_results_with_new_explanations(tmp_path):
    old = tmp_path / "executed.ipynb"
    new = tmp_path / "updated.ipynb"
    printed = {"output_type": "stream", "name": "stdout",
               "text": ["Actual rows: 41314\\n"]}
    save_notebook(old, [
        markdown("intro", "The original introduction."),
        code("diagnostic", 'print("Python is working")', 1),
        code("analysis", "print('Actual rows: 41314')", 2, [printed]),
        markdown("end", "Actual limitations."),
    ])
    save_notebook(new, [
        markdown("intro", "The original introduction.\\n\\nI explain why."),
        code("analysis", "# Why the measurement matters\\n"
             "print('Actual rows: 41314')"),
        markdown("end", "Actual limitations.\\n\\nI describe limitations."),
    ])
    matched, omitted = merge_execution(old, new)
    assert matched == 1
    assert omitted == 1
    got = json.loads(new.read_text(encoding="utf-8"))["cells"]
    assert got[1]["outputs"] == [printed]
    assert got[1]["execution_count"] == 2
    assert got[1]["source"][0].startswith("# Why")
    assert "I explain why" in got[0]["source"][0]
    assert "I describe limitations" in got[2]["source"][0]
    assert json.loads(old.read_text(encoding="utf-8"))["cells"][2]["outputs"] == [printed]


def test_merge_rejects_changed_code_without_touching_target(tmp_path):
    old = tmp_path / "old.ipynb"
    new = tmp_path / "new.ipynb"
    save_notebook(old, [code("analysis", "print(1)", 1,
                              [{"output_type": "stream", "name": "stdout",
                                "text": ["1\\n"]}])])
    save_notebook(new, [code("analysis", "# explanation\\nprint(2)")])
    before = new.read_bytes()
    with pytest.raises(ValueError, match="Code differs"):
        merge_execution(old, new)
    assert new.read_bytes() == before


def test_merge_rejects_unexpected_local_cells_without_touching_target(tmp_path):
    old = tmp_path / "old.ipynb"
    new = tmp_path / "new.ipynb"
    save_notebook(old, [
        markdown("intro", "Original"),
        code("analysis", "print(1)", 1),
        code("own-code", "print('my new analysis')", 2),
    ])
    save_notebook(new, [
        markdown("intro", "Original and comments"),
        code("analysis", "# explanation\\nprint(1)"),
    ])
    before = new.read_bytes()
    with pytest.raises(ValueError, match="Unrecognised local cell"):
        merge_execution(old, new)
    assert new.read_bytes() == before


def test_merge_rejects_incomplete_execution(tmp_path):
    old = tmp_path / "old.ipynb"
    new = tmp_path / "new.ipynb"
    save_notebook(old, [code("analysis", "print(1)", None)])
    save_notebook(new, [code("analysis", "# explanation\\nprint(1)")])
    with pytest.raises(ValueError, match="not executed"):
        merge_execution(old, new)


def test_merge_rejects_same_file_as_source_and_target(tmp_path):
    path = tmp_path / "same.ipynb"
    save_notebook(path, [code("one", "print(1)", 1)])
    with pytest.raises(ValueError, match="different files"):
        merge_execution(path, path)
