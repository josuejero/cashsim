from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cashsim.cli import app


def test_cli_compare_can_write_markdown_report(tmp_path: Path) -> None:
    runner = CliRunner()

    a = Path("examples/configs/simple_baseline.json")
    b = Path("examples/configs/debt_payoff.json")

    out = tmp_path / "cmp"

    res = runner.invoke(
        app,
        [
            "compare",
            "--a",
            str(a),
            "--b",
            str(b),
            "--start",
            "2025-01-01",
            "--days",
            "31",
            "--out",
            str(out),
            "--report",
            "report.md",
        ],
    )

    assert res.exit_code == 0, res.stdout

    payload = json.loads((out / "compare.json").read_text(encoding="utf-8"))
    assert "timeline" in payload
    assert "category_totals" in payload
    assert "series_summary" in payload
    assert "meta" in payload
    assert (out / "report.md").exists()
