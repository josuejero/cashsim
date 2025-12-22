from __future__ import annotations

from pathlib import Path

from scripts.gx_validate_inputs import validate_inputs


def test_gx_validates_fixture() -> None:
    ok = validate_inputs(Path("tests/fixtures/csv_inputs_v1"))
    assert ok
