from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # editor-only hint; avoids hard dependency during type checking
    from streamlit.web import cli as _stcli  # noqa: F401


def st_main() -> None:
    # Lazy import so CI/mypy don’t need streamlit installed
    stcli = import_module("streamlit.web.cli")
    sys.argv = ["streamlit", "run", "src/cashsim/ui/streamlit_app.py", "--server.headless=true"]
    stcli.main()  # removed: type: ignore[attr-defined]


def main(argv: list[str] | None = None) -> int:
    st_main()
    return 0
