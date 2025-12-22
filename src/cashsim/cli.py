from __future__ import annotations

import importlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import typer

from cashsim.batch import run_from_config
from cashsim.compare import (
    build_compare_payload,
    render_compare_markdown,
    series_diff,
)
from cashsim.io.config_io import load_config
from cashsim.io.csv_import import import_input_tables
from cashsim.io.csv_tables import export_input_tables
from cashsim.io.exporters import metrics_to_dict, write_run
from cashsim.risk import predict_overdraft_risk

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
INPUTS_OUT_OPTION = typer.Option(
    Path("inputs_out"),
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
IMPORT_FROM_OPTION = typer.Option(
    ...,
    "--from",
    exists=True,
    file_okay=False,
    help="Folder with CSV tables.",
)
IMPORT_OUT_OPTION = typer.Option(
    Path("config.imported.json"),
    "--out",
    help="Output config JSON path.",
)
IMPORT_BASE_CONFIG_OPTION = typer.Option(
    None,
    "--base-config",
    exists=True,
    dir_okay=False,
    help="Optional base Dials config if dials.json is not present in --from.",
)
IMPORT_STRICT_OPTION = typer.Option(False, "--strict", help="Reject extra CSV columns.")
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
REPORT_OPTION = typer.Option(
    None,
    "--report",
    help=(
        "Write a human-readable compare report to Markdown. If relative, it is written under --out."
    ),
)
THRESHOLD_OPTION = typer.Option(
    0.01,
    "--threshold",
    min=0,
    help="Threshold used by series_summary to flag first divergence.",
)
RISK_HORIZON_OPTION = typer.Option(
    30,
    "--horizon-days",
    min=1,
    max=366,
)
RISK_MODEL_OPTION = typer.Option(
    Path("artifacts/risk/model.joblib"),
    "--model",
    exists=False,
)
RISK_TOP_K_OPTION = typer.Option(
    5,
    "--top-k",
    min=0,
    max=20,
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
    report: Path | None = REPORT_OPTION,
    threshold: float = THRESHOLD_OPTION,
    overwrite: bool = OVERWRITE_OPTION,
) -> None:
    """Compare two configs (deep compare + optional series diff + optional Markdown report)."""

    s = _parse_date(start)
    run_a = run_from_config(config=a, start=s, days=days)
    run_b = run_from_config(config=b, start=s, days=days)

    out_dir = out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    compare_path = out_dir / "compare.json"
    diff_path = out_dir / "series_diff.csv"

    # Report path: if a relative path is provided, write it under out_dir
    report_path: Path | None = None
    if report is not None:
        report_path = report if report.is_absolute() else (out_dir / report)

    # Overwrite protections
    to_check: list[Path] = [compare_path]
    if series:
        to_check.append(diff_path)
    if report_path is not None:
        to_check.append(report_path)

    if not overwrite:
        for p in to_check:
            if p.exists():
                raise typer.BadParameter(f"Refusing to overwrite {p} (use --overwrite)")

    payload = build_compare_payload(
        metrics_a=run_a.metrics,
        metrics_b=run_b.metrics,
        df_a=run_a.df,
        df_b=run_b.df,
        start=start,
        days=days,
        threshold=threshold,
    )

    compare_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if series:
        # Use the same default columns used by build_compare_payload to keep UX aligned
        cols = payload.get("meta", {}).get("series_columns", [])
        diff = series_diff(run_a.df, run_b.df, columns=list(cols))
        diff.to_csv(diff_path, index=False, lineterminator="\n")

    if report_path is not None:
        md = render_compare_markdown(
            payload, series_diff_path=("series_diff.csv" if series else None)
        )
        report_path.write_text(md, encoding="utf-8", newline="\n")

    typer.echo(f"Wrote compare artifacts to: {out_dir}")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def api(
    ctx: typer.Context,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """Run the CashSim FastAPI server (Uvicorn)."""

    args = [
        "uvicorn",
        "cashsim.api.app:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    if reload:
        args.append("--reload")

    # pass-through for things like: --log-level debug, --workers 2
    args.extend(list(ctx.args))

    raise SystemExit(subprocess.call(args))


@app.command("export-inputs")
def export_inputs_cmd(
    config: Path = CONFIG_OPTION,
    out: Path = INPUTS_OUT_OPTION,
    overwrite: bool = OVERWRITE_OPTION,
) -> None:
    """Export canonical input CSV tables + dials.json into a folder."""

    dials = load_config(config)
    export_input_tables(dials, out, overwrite=overwrite)
    typer.echo(f"Wrote input tables to: {out.resolve()}")


@app.command("import")
def import_cmd(
    from_dir: Path = IMPORT_FROM_OPTION,
    out: Path = IMPORT_OUT_OPTION,
    base_config: Path | None = IMPORT_BASE_CONFIG_OPTION,
    strict: bool = IMPORT_STRICT_OPTION,
) -> None:
    """Import canonical input tables into a Dials JSON config."""

    dials = import_input_tables(from_dir, base_config=base_config, strict=strict)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dials.model_dump_json(indent=2) + "\n", encoding="utf-8")
    typer.echo(f"Wrote config: {out.resolve()}")


@app.command()
def risk(
    config: Path = CONFIG_OPTION,
    start: str = START_OPTION,
    horizon_days: int = RISK_HORIZON_OPTION,
    model: Path = RISK_MODEL_OPTION,
    top_k: int = RISK_TOP_K_OPTION,
) -> None:
    """Estimate overdraft risk P(balance < 0 within N days)."""
    s = _parse_date(start)
    run = run_from_config(config=config, start=s, days=horizon_days)
    result = predict_overdraft_risk(
        run.dials,
        start=s,
        horizon_days=horizon_days,
        model_path=model,
        top_k=top_k,
    )

    payload = {
        "probability": result.probability,
        "horizon_days": result.horizon_days,
        "drivers": [
            {
                "feature": d.feature,
                "contribution": d.contribution,
                "direction": d.direction,
                "value": d.value,
            }
            for d in result.drivers
        ],
    }
    typer.echo(json.dumps(payload, indent=2))


def main() -> None:
    # Compatibility: `cashsim` launches the UI.
    # Canonical UI: `cashsim ui`.
    if len(sys.argv) == 1:
        sys.argv = [sys.argv[0], "ui"]

    app()


if __name__ == "__main__":
    main()
