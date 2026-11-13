"""Keep the real executed EDA results when we add clearer notebook notes.

Usage (after copying the executed notebook to a safe backup and pulling GitHub):
    python -m scripts.merge_eda_execution "PATH_TO_EXECUTED_BACKUP.ipynb"

This program changes ONLY the destination notebook's recorded execution counts
and cell outputs. It keeps the newer explanations and code untouched.
It does not modify the backup, charts, raw dataset, or case database.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "notebooks" / "06_source_eda.ipynb"

# We allowed this one diagnostic cell while troubleshooting VS Code/Jupyter.
# It is not part of the EDA and shouldn't end up in the assessed notebook.
DIAGNOSTIC_CELLS = {
    'print("Python is working")',
    "print('Python is working')",
}


def cell_text(cell: dict) -> str:
    """Jupyter may store lines as either a list or a single string."""
    value = cell["source"]
    return "".join(value) if isinstance(value, list) else value


def merge_execution(executed_path: Path, target_path: Path = TARGET) -> tuple[int, int]:
    """Return (executed code cells copied, extra diagnostic cells omitted).

    If the user's notebook contains any other unexpected work, stop rather
    than silently discarding it. Validate the whole merge before writing.
    """
    executed_path = executed_path.resolve()
    target_path = target_path.resolve()
    if executed_path == target_path:
        raise ValueError("Backup and target must be different files.")

    old = json.loads(executed_path.read_text(encoding="utf-8-sig"))
    new = json.loads(target_path.read_text(encoding="utf-8-sig"))
    old_cells = old["cells"]
    new_cells = new["cells"]

    target_by_id = {cell.get("id"): cell for cell in new_cells if cell.get("id")}
    if len(target_by_id) != len(new_cells):
        raise ValueError("Target notebook has missing or duplicate cell IDs. Nothing changed.")

    merged = set()
    old_code = []
    extras = 0

    for old_cell in old_cells:
        old_id = old_cell.get("id")
        new_cell = target_by_id.get(old_id)
        if new_cell is None:
            # Permit ONLY the temporary print cell we used to test the kernel.
            if (old_cell["cell_type"] == "code"
                    and cell_text(old_cell).strip() in DIAGNOSTIC_CELLS):
                extras += 1
                continue
            raise ValueError(
                f"Unrecognised local cell {old_id or '(without ID)'}. "
                "Your backup is intact; nothing has been overwritten."
            )
        if new_cell["cell_type"] != old_cell["cell_type"]:
            raise ValueError(f"Cell {old_id} changed type. Nothing changed.")

        old_source = cell_text(old_cell).strip()
        new_source = cell_text(new_cell).strip()
        if old_cell["cell_type"] == "code":
            # The GitHub update added comments ABOVE the existing code.
            # If the code itself changed, stop: don't claim old outputs came
            # from a different program.
            if not new_source.endswith(old_source):
                raise ValueError(
                    f"Code differs in {old_id}; will not attach old results "
                    "to changed calculations. Your backup is intact."
                )
            if old_cell.get("execution_count") is None:
                raise ValueError(
                    f"Cell {old_id} was not executed; please run all EDA "
                    "cells and save before merging."
                )
            if any(result.get("output_type") == "error"
                   for result in old_cell.get("outputs", [])):
                raise ValueError(
                    f"Cell {old_id} has an error output; no merge performed."
                )
            old_code.append((new_cell, old_cell))
        elif not new_source.startswith(old_source):
            # The published changes should only append clearer explanatory
            # notes. Keep user-authored changes if any rather than discard.
            raise ValueError(
                f"Markdown differs in {old_id}; no merge performed."
            )
        merged.add(old_id)

    unmatched = set(target_by_id) - merged
    if unmatched:
        raise ValueError(
            "New target cells cannot be paired with the executed notebook: "
            + ", ".join(sorted(unmatched))
            + ". Nothing changed."
        )

    # Only now do we modify the in-memory target notebook.
    for new_cell, old_cell in old_code:
        new_cell["execution_count"] = old_cell["execution_count"]
        new_cell["outputs"] = copy.deepcopy(old_cell.get("outputs", []))

    # Write an intermediate file, then atomically replace the destination.
    tmp = target_path.with_name(target_path.name + ".merge_tmp")
    try:
        tmp.write_text(
            json.dumps(new, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, target_path)
    finally:
        if tmp.exists():
            tmp.unlink()

    return len(old_code), extras


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Keep executed EDA plots and measured outputs, "
        "while retaining the clearer GitHub markdown and code comments."
    )
    parser.add_argument(
        "executed_backup", type=Path,
        help="A saved copy of the fully executed older EDA notebook.",
    )
    args = parser.parse_args()
    try:
        cells, extras = merge_execution(args.executed_backup)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Could not safely merge: {exc}\n")
    print(f"Merged outputs from {cells} executed EDA code cells.")
    if extras:
        print(f"Left out {extras} temporary Python-kernel test cell(s).")
    print("Kept the new explanatory notes and code comments.")
    print("Original backup and generated reports have not been touched.")


if __name__ == "__main__":
    main()
