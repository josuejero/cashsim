# src/cashsim/cli.py
import sys

from streamlit.web import cli as stcli


def st_main() -> None:
    sys.argv = ["streamlit", "run", "src/cashsim/ui/streamlit_app.py", "--server.headless=true"]
    stcli.main()


def main(argv: list[str] | None = None) -> int:
    """Console entry point wrapper calling st_main()."""
    return st_main(argv)
