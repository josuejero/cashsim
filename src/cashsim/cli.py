from __future__ import annotations

import importlib
import json
import sys
from datetime import date
from pathlib import Path

import typer

from cashsim.batch import run_from_config
from cashsim.compare import metrics_delta, series_diff
from cashsim.io.exporters import metrics_to_dict, write_run

APP_HELP = (
    "CashSim CLI. Use `cashsim ui` for the Streamlit app and "
    "`cashsim simulate/export/compare` for batch mode."
)

app = typer.Typer(add_completion=False, no_args_is_help=False, help=APP_HELP)

HEADLESS_OPTION = typer.Option(
    False,
    "--headless/--no-headless",
    help="Run Streamlit without opening a browser.",
)
CONFIG_OPTION = typer.Option(
    ...,
    "--config",
    exists=True,
    dir_okay=False,
    help="Path to a Dials JSON config.",
)
START_OPTION = typer.Option(
    ...,
    "--start",
    help="Simulation start date (YYYY-MM-DD).",
)
DAYS_OPTION = typer.Option(
    31,
    "--days",
    min=1,
    max=366,
    help="Number of days to simulate.",
)
OUT_OPTION = typer.Option(
    Path("out"),
    "--out",
    help="Output directory.",
)
SERIES_FORMAT_OPTION = typer.Option(
    "csv",
    "--series-format",
    help="csv|json",
)
EVENTS_OPTION = typer.Option(
    False,
    "--events/--no-events",
    help="Also export events.csv (flattened).",
)
OVERWRITE_OPTION = typer.Option(
    False,
    "--overwrite",
    help="Overwrite existing artifacts in --out.",
)
A_OPTION = typer.Option(
    ...,
    "--a",
    exists=True,
    dir_okay=False,
    help="Config A (baseline).",
)
B_OPTION = typer.Option(
    ...,
    "--b",
    exists=True,
    dir_okay=False,
    help="Config B (candidate).",
)
SERIES_OPTION = typer.Option(
    False,
    "--series/--no-series",
    help="Also write an aligned series_diff.csv.",
)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise typer.BadParameter("Date must be YYYY-MM-DD") from e


def _streamlit_app_file() -> str:
    mod = importlib.import_module("cashsim.ui.streamlit_app")
    file = getattr(mod, "__file__", None)
    if file is None:
        raise RuntimeError("cashsim.ui.streamlit_app has no __file__; install may be broken")
    return str(Path(file).resolve())


def _run_streamlit(app_file: str, *, headless: bool, extra_args: list[str]) -> None:
    from streamlit.web import cli as stcli

    argv = ["streamlit", "run", app_file]
    if headless:
        argv.append("--server.headless=true")

    argv.extend(extra_args)

    old_argv = sys.argv
    try:
        sys.argv = argv
        stcli.main()
    finally:
        sys.argv = old_argv


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def ui(
    ctx: typer.Context,
    headless: bool = HEADLESS_OPTION,
) -> None:
    """Launch the Streamlit UI."""
    app_file = _streamlit_app_file()
    _run_streamlit(app_file, headless=headless, extra_args=list(ctx.args))


@app.command()
def simulate(
    config: Path = CONFIG_OPTION,
    start: str = START_OPTION,
    days: int = DAYS_OPTION,
) -> None:
    """Run a simulation and print the result as JSON to stdout."""
    s = _parse_date(start)
    run = run_from_config(config=config, start=s, days=days)

    payload = {
        "metrics": metrics_to_dict(run.metrics),
        "series": run.df.to_dict(orient="records"),
    }
    # NOTE: This is primarily for quick inspection; `export` is the stable artifact writer.
    typer.echo(json.dumps(payload, indent=2, default=str))


@app.command()
def export(
    config: Path = CONFIG_OPTION,
    start: str = START_OPTION,
    days: int = DAYS_OPTION,
    out: Path = OUT_OPTION,
    series_format: str = SERIES_FORMAT_OPTION,
    events: bool = EVENTS_OPTION,
    overwrite: bool = OVERWRITE_OPTION,
) -> None:
    """Run a simulation and write stable artifacts to disk."""
    s = _parse_date(start)
    run = run_from_config(config=config, start=s, days=days)

    try:
        write_run(
            out_dir=out.resolve(),
            df=run.df,
            metrics=run.metrics,
            config_path=run.config_path,
            start=start,
            days=days,
            series_format=series_format,
            include_events=events,
            overwrite=overwrite,
        )
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"Wrote artifacts to: {out.resolve()}")


@app.command()
def compare(
    a: Path = A_OPTION,
    b: Path = B_OPTION,
    start: str = START_OPTION,
    days: int = DAYS_OPTION,
    out: Path = OUT_OPTION,
    series: bool = SERIES_OPTION,
    overwrite: bool = OVERWRITE_OPTION,
) -> None:
    """Compare two configs (skeleton: metrics delta; optional series delta)."""
    s = _parse_date(start)
    run_a = run_from_config(config=a, start=s, days=days)
    run_b = run_from_config(config=b, start=s, days=days)

    out_dir = out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    compare_path = out_dir / "compare.json"
    if not overwrite and compare_path.exists():
        raise typer.BadParameter(f"Refusing to overwrite {compare_path} (use --overwrite)")

    compare_payload = metrics_delta(run_a.metrics, run_b.metrics)
    compare_path.write_text(
        json.dumps(compare_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if series:
        diff = series_diff(
            run_a.df,
            run_b.df,
            columns=[
                "balance",
                "total_cc_balance",
                "total_iou_balance",
                "accrued_interest_unposted",
            ],
        )
        diff.to_csv(out_dir / "series_diff.csv", index=False, lineterminator="\n")

    typer.echo(f"Wrote compare artifacts to: {out_dir}")


def main() -> None:
    # Compatibility: `cashsim` launches the UI.
    # Canonical UI: `cashsim ui`.
    if len(sys.argv) == 1:
        sys.argv = [sys.argv[0], "ui"]

    app()


if __name__ == "__main__":
    main()
