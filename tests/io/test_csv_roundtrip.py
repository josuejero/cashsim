from __future__ import annotations

from pathlib import Path

from cashsim.io.config_io import load_config
from cashsim.io.csv_import import import_input_tables
from cashsim.io.csv_tables import export_input_tables


def test_export_import_roundtrip(tmp_path: Path) -> None:
    cfg = Path("examples/configs/sample.json")
    dials = load_config(cfg)

    out_dir = tmp_path / "tables"
    export_input_tables(dials, out_dir, overwrite=True)

    d2 = import_input_tables(out_dir)

    assert dials.model_dump(mode="json") == d2.model_dump(mode="json")
