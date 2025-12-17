from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def st_main() -> None:
    stcli = import_module("streamlit.web.cli")
    sys.argv = ["streamlit", "run", "src/cashsim/ui/streamlit_app.py", "--server.headless=true"]
    stcli.main()


def main(argv: list[str] | None = None) -> int:
    st_main()
    return 0
