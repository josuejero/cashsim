from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from cashsim.models import Dials


def load_config(path: str | Path) -> Dials:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    try:
        return Dials.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid config: {e}") from e


def save_config(dials: Dials, path: str | Path) -> None:
    p = Path(path)
    p.write_text(dials.model_dump_json(indent=2), encoding="utf-8")
