from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from cashsim.dq.report import run_data_quality_report

dq_app = typer.Typer(help="Data quality inspection utilities.")


_CONFIG_OPTION = typer.Option(
    ...,
    "--config",
    "-c",
    exists=True,
    file_okay=True,
    dir_okay=False,
    help="Data quality configuration file.",
)

_DATASET_OPTION = typer.Option(
    None,
    "--dataset",
    "-d",
    exists=True,
    file_okay=False,
    help="Optional override for dataset root directory.",
)

_SINCE_OPTION = typer.Option(
    None,
    "--since",
    help="Only consider rows on or after this date (YYYY-MM-DD). Requires table filter hints.",
)

_OUT_OPTION = typer.Option(
    Path("out/dq-report"),
    "--out",
    "-o",
    help="Directory to write JSON/CSV/markdown artifacts.",
)

_MARKDOWN_OPTION = typer.Option(
    True,
    "--markdown/--no-markdown",
    help="Create a human-readable markdown summary.",
)

_MAX_EXAMPLES_OPTION = typer.Option(
    3,
    "--max-examples",
    min=1,
    max=20,
    help="Max rows to include when emitting example violations.",
)


def _parse_since(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise typer.BadParameter("Date must be YYYY-MM-DD") from err


@dq_app.command("report")
def report(
    config: Path = _CONFIG_OPTION,
    dataset: Path | None = _DATASET_OPTION,
    since: str | None = _SINCE_OPTION,
    out: Path = _OUT_OPTION,
    markdown: bool = _MARKDOWN_OPTION,
    max_examples: int = _MAX_EXAMPLES_OPTION,
) -> None:
    """Run a repeatable data-quality report using the provided config."""

    parsed_since = _parse_since(since) if since is not None else None
    result = run_data_quality_report(
        config_path=config,
        dataset_root=dataset,
        since=parsed_since,
        output_dir=out,
        include_markdown=markdown,
        max_examples=max_examples,
    )

    typer.echo(f"Artifacts: JSON={result.json_path}, CSV={result.csv_path}")
    if markdown and result.markdown_path is not None:
        typer.echo(f"Markdown: {result.markdown_path}")
    if result.issue_path:
        typer.secho(f"Issue stub: {result.issue_path}", fg=typer.colors.RED)

    counts = {severity.value: count for severity, count in result.severity_summary.items()}
    typer.echo(f"Severity summary: {counts}")
    typer.echo("Status: PASS" if result.exit_code == 0 else "Status: FAIL")
    raise typer.Exit(code=result.exit_code)
