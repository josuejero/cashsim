from __future__ import annotations

import sys

from streamlit.web import cli as stcli


def st_main() -> None:
    sys.argv = ["streamlit", "run", "src/cashsim/ui/streamlit_app.py", "--server.headless=true"]
    stcli.main()


def main(argv: list[str] | None = None) -> int:
    st_main()
    return 0
