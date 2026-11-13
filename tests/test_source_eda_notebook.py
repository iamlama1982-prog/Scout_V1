"""Run every source EDA notebook code cell against a tiny disposable fixture.

This is a structural smoke test only; it does NOT produce the real project's
data-science results or substitute for executing the actual SevAnalysis CSV.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import pandas as pd

from src import incident_assistant


def test_source_eda_runs_all_cells_and_exports_only_aggregates(
    tmp_path, monkeypatch,
):
    data_path = tmp_path / "synthetic" / "incidents.csv"
    data_path.parent.mkdir(parents=True)
    rows = [
        dict(id="a", vendor_name="Vendor A", title="API 504 gateway timeout",
             started_at="2026-10-02T10:00:00Z", resolved_at="2026-10-02T11:00:00Z",
             impact="major", status="resolved", components="API",
             url="https://status.example.org/a"),
        dict(id="a", vendor_name="Vendor A", title="API 504 gateway timeout",
             started_at="2026-10-02T10:00:00Z", resolved_at="2026-10-02T11:00:00Z",
             impact="major", status="resolved", components="API",
             url="https://status.example.org/a"),
        dict(id="b", vendor_name="Vendor B", title="Database connection failures",
             started_at="2026-09-04T13:00:00Z", resolved_at="",
             impact="", status="investigating", components="Database",
             url="https://status.example.org/b"),
        dict(id="c", vendor_name="Vendor A", title="Maintenance announcement",
             started_at="not-a-date", resolved_at="",
             impact="minor", status="investigating", components="",
             url="not-a-valid-url"),
        dict(id="d", vendor_name="", title="Source missing vendor",
             started_at="", resolved_at="", impact="", status="",
             components="", url=""),
        dict(id="e", vendor_name="Vendor C", title="",
             started_at="", resolved_at="", impact="", status="",
             components="", url=""),
    ]
    pd.DataFrame(rows).to_csv(data_path, index=False)

    output_dir = tmp_path / "charts"
    monkeypatch.setenv("SCOUT_EDA_REPORT_DIR", str(output_dir))
    monkeypatch.setattr(incident_assistant, "LOCAL_CSV", data_path)

    root = Path(__file__).resolve().parents[1]
    notebook = json.loads(
        (root / "notebooks" / "06_source_eda.ipynb").read_text(encoding="utf-8")
    )
    namespace = {"__name__": "__main__"}

    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        exec(compile(source, cell.get("id", "eda-cell"), "exec"), namespace)

    metrics_path = output_dir / "source_eda_metrics.json"
    assert metrics_path.is_file()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["sha256"] == hashlib.sha256(data_path.read_bytes()).hexdigest()
    assert metrics["raw_rows"] == 6
    assert metrics["rows_missing_core_fields"] == 2
    assert metrics["duplicate_usable_rows"] == 1
    assert metrics["prepared_rows"] == 3
    assert metrics["unique_vendors"] == 2
    assert metrics["valid_start_timestamps"] == 2
    assert metrics["missing_or_invalid_start_timestamps"] == 1
    assert metrics["missing_pct_prepared"]["Original source URL"] > 0
    assert "file_modified_utc_not_verified_download_date" in metrics
    assert "source_url" not in metrics
    assert not any("status.example.org" in str(v) for v in metrics.values())

    expected = [
        "source_eda_missingness.png",
        "source_eda_title_lengths.png",
        "source_eda_vendor_coverage.png",
        "source_eda_monthly_coverage.png",
        "source_eda_impact_labels.png",
    ]
    for name in expected:
        image = output_dir / name
        assert image.is_file(), name
        assert image.stat().st_size > 1000, name
