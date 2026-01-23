from __future__ import annotations

import json
from pathlib import Path

from cashsim.dq.config import Severity
from cashsim.dq.report import run_data_quality_report


def test_dq_report_produces_artifacts(tmp_path: Path) -> None:
    config_path = Path("tests/fixtures/dq_report_config.json")

    result = run_data_quality_report(
        config_path=config_path,
        output_dir=tmp_path,
        include_markdown=True,
    )

    assert result.exit_code == 1
    assert result.severity_summary[Severity.FAIL] >= 1
    assert result.issue_path is not None
    assert result.issue_path.exists()
    assert (tmp_path / "dq_report.json").exists()
    assert (tmp_path / "dq_report.csv").exists()
    assert (tmp_path / "dq_report.md").exists()

    payload = json.loads((tmp_path / "dq_report.json").read_text(encoding="utf-8"))
    assert payload["meta"]["dataset"] == "dq_sample"
    assert payload["meta"]["config_path"].endswith("dq_report_config.json")
    assert payload["results"]
