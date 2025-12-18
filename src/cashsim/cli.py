from __future__ import annotations

import importlib
import sys
from pathlib import Path

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="CashSim CLI. Use `cashsim ui` to launch the Streamlit app.",
)


def _streamlit_app_file() -> str:
    """Return the installed module file path for the Streamlit app."""
    mod = importlib.import_module("cashsim.ui.streamlit_app")
    file = getattr(mod, "__file__", None)
    if file is None:
        raise RuntimeError("cashsim.ui.streamlit_app has no __file__; install may be broken")
    return str(Path(file).resolve())


def _run_streamlit(app_file: str, *, headless: bool, extra_args: list[str]) -> None:
    """Invoke Streamlit programmatically so `cashsim ui` behaves like a real product entrypoint."""
    from streamlit.web import cli as stcli

    argv = ["streamlit", "run", app_file]
    if headless:
        argv.append("--server.headless=true")

    # Allow advanced users to pass Streamlit flags, e.g. `cashsim ui -- --server.port 8502`
    argv.extend(extra_args)

    old_argv = sys.argv
    try:
        sys.argv = argv
        stcli.main()
    finally:
        sys.argv = old_argv


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def ui(
    ctx: typer.Context,
    headless: bool = typer.Option(
        False,
        "--headless/--no-headless",
        help="Run Streamlit without opening a browser.",
    ),
) -> None:
    """Launch the Streamlit UI."""
    app_file = _streamlit_app_file()
    extra_args = list(ctx.args)
    _run_streamlit(app_file, headless=headless, extra_args=extra_args)


def main() -> None:
    # Compatibility: `cashsim` launches the UI.
    # Canonical: `cashsim ui`.
    if len(sys.argv) == 1:
        sys.argv = [sys.argv[0], "ui"]

    app()


if __name__ == "__main__":
    main()
