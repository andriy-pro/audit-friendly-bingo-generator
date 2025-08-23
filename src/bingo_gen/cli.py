from __future__ import annotations

import sys
import time
from pathlib import Path

import typer

from .config import resolve_parameters
from .core import BuildParams, UniversalCardBuilder
from .logging_setup import setup_logging
from .serialize import build_run_meta, emit_cards_json, emit_report_json
from .verify import verify as verify_artifacts
from .version import __version__

app = typer.Typer(help="Bingo/Tombola card generator CLI")


@app.callback()
def common_options(
    version: bool = typer.Option(
        False, "--version", help="Show application version and exit", is_eager=True
    ),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit(0)


@app.command()
def run(
    config: str = typer.Option(
        None,
        "--config",
        help="Path to config file (YAML/JSON)",
    ),
    # Single algorithm policy: keep option for UX but normalize to one strategy.
    profile: str = typer.Option(
        "heuristic",
        "--profile",
        help="Generation profile (heuristic only)",
    ),
    out_cards: str = typer.Option(None, "--out-cards", help="cards.json output path"),
    out_report: str = typer.Option(None, "--out-report", help="report.json output path"),
    log_file: str = typer.Option(None, "--log-file", help="Log file path"),
    colors: str = typer.Option(
        "auto",
        "--colors",
        help="auto|always|never",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="DEBUG|INFO|WARN|ERROR",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Resolve params and exit"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite outputs if they exist",
    ),
    no_mkdirs: bool = typer.Option(False, "--no-mkdirs", help="Do not create parent directories"),
    summary_csv: str = typer.Option(None, "--summary-csv", help="Path to summary.csv (optional)"),
    csv_by_position: bool = typer.Option(
        False, "--csv-by-position", help="Include per-position counts in CSV"
    ),
) -> None:
    """Construct cards and report according to provided configuration."""

    # Normalize profile to single supported strategy
    profile = "heuristic"

    cli_overrides = {}
    if out_cards:
        cli_overrides["out_cards"] = out_cards
    if out_report:
        cli_overrides["out_report"] = out_report
    if log_file:
        cli_overrides["log_file"] = log_file
    if colors:
        cli_overrides["colors"] = colors
    if log_level:
        cli_overrides["log_level"] = log_level

    resolved, params_hash, _cfg_path_unused = resolve_parameters(
        config_path_str=config, cli_overrides=cli_overrides
    )

    setup_logging(
        level=str(resolved.get("log_level", "INFO")),
        log_file=resolved.get("log_file"),
        json_format=(str(resolved.get("log_format", "text")) == "json"),
    )

    if dry_run:
        typer.echo(f"Profile: {profile}")
        typer.echo(f"Params hash: {params_hash}")
        raise typer.Exit(0)

    # Extract parameters
    R = int(resolved.get("R") or 0)
    T = int(resolved.get("T") or 0)
    m = int(resolved.get("m") or 0)
    n = int(resolved.get("n") or 0)
    unique_scope = list(resolved.get("unique_scope", []))
    uniformity = str(resolved.get("uniformity", "near"))
    rng_engine = str(resolved.get("seed", {}).get("engine", "py_random"))
    seed_value = int(resolved.get("seed", {}).get("value", 0))
    position_balance = bool(resolved.get("position_balance", False))

    # Create build parameters
    build_params = BuildParams(
        R=R,
        T=T,
        m=m,
        n=n,
        uniformity=uniformity,
        unique_scope=unique_scope,
        seed=seed_value,
        rng_engine=rng_engine,
        position_balance=position_balance,
        strategy=profile,
    )

    # Build cards using universal builder
    typer.echo("Using heuristic generation strategy...")
    start_time = time.time()

    builder = UniversalCardBuilder(strategy="heuristic")
    result = builder.build(build_params)

    # Update metrics with actual time
    result.metrics.total_time = time.time() - start_time

    typer.echo(f"Generated {len(result.cards)} cards in {result.metrics.total_time:.2f}s")
    typer.echo(f"Average attempts per card: {result.metrics.attempts_per_card:.1f}")

    # Verify artifacts
    report = verify_artifacts(result.cards, R=R, m=m, n=n, unique_scope=unique_scope)

    # Build run metadata
    run_meta = build_run_meta(
        app_version=__version__,
        params_hash=params_hash,
        seed=seed_value,
        rng_engine=rng_engine,
        parallel=bool(resolved.get("parallel", False)),
        parallelism=int(resolved.get("parallelism", 1)),
    )

    # Output files
    out_cards_path = Path(resolved.get("out_cards", "cards.json"))
    out_report_path = Path(resolved.get("out_report", "report.json"))

    emit_cards_json(
        out_cards_path,
        cards=result.cards,
        run_meta=run_meta,
        mkdirs=(not no_mkdirs),
        overwrite=force,
    )

    emit_report_json(
        out_report_path,
        report=report,
        mkdirs=(not no_mkdirs),
        overwrite=force,
    )

    # Optional CSV summary
    if summary_csv:
        from .serialize import emit_summary_csv

        freqs = report.get("frequencies", {})
        by_pos = report.get("position_frequencies", {}) if csv_by_position else None

        # Type safety for mypy
        if not isinstance(freqs, dict):
            freqs = {}
        if by_pos is not None and not isinstance(by_pos, dict):
            by_pos = None

        emit_summary_csv(
            Path(summary_csv),
            freqs=freqs,
            by_position=by_pos,
            mkdirs=(not no_mkdirs),
            overwrite=force,
        )

    typer.echo(f"✅ Generated {len(result.cards)} cards successfully!")
    typer.echo(f"📁 Output files: {out_cards_path}, {out_report_path}")
    typer.echo(
        f"⚡ Performance: {result.metrics.total_time:.2f}s total, "
        f"{result.metrics.attempts_per_card:.1f} avg attempts/card",
    )

    raise typer.Exit(code=0)


@app.command()
def verify(
    _cards: str = typer.Option(..., "--cards", help="Path to cards.json"),
    _report: str = typer.Option(..., "--report", help="Path to report.json"),
    _params: str = typer.Option(None, "--params", help="Path to resolved params JSON"),
    _strict: bool = typer.Option(False, "--strict", help="Fail on any deviation"),
    _report_only: bool = typer.Option(
        False, "--report-only", help="Validate only report.json schema"
    ),
) -> None:
    """Verify produced artifacts. Placeholder for schema checks (future)."""
    typer.echo("Verify subcommand is not fully implemented yet (schema checks TBD).")
    raise typer.Exit(code=0)


def main(_argv: list[str] | None = None) -> int:
    try:
        app(standalone_mode=True)
        return 0
    except SystemExit as e:
        return int(e.code) if e.code is not None else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
