from __future__ import annotations

import sys

import typer

from .version import __version__

app = typer.Typer(help="Bingo/Tombola card generator CLI")


@app.callback()
def common_options(
    version: bool = typer.Option(
        False, "--version", help="Show application version and exit", is_eager=True
    ),
):
    if version:
        typer.echo(__version__)
        raise typer.Exit(0)


@app.command()
def run(
    config: str = typer.Option(
        None, "--config", help="Path to config file (YAML/JSON)"
    ),
    out_cards: str = typer.Option(None, "--out-cards", help="cards.json output path"),
    out_report: str = typer.Option(
        None, "--out-report", help="report.json output path"
    ),
    log_file: str = typer.Option(None, "--log-file", help="Log file path"),
    colors: str = typer.Option("auto", "--colors", help="auto|always|never"),
    log_level: str = typer.Option("INFO", "--log-level", help="DEBUG|INFO|WARN|ERROR"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Resolve params and exit"),
):
    """Construct cards and report according to provided configuration.

    This is a placeholder scaffold. Implementation will follow in subsequent phases.
    """
    typer.echo("Run command scaffold. Implementation pending.")
    raise typer.Exit(code=0)


@app.command()
def verify(
    cards: str = typer.Option(..., "--cards", help="Path to cards.json"),
    report: str = typer.Option(..., "--report", help="Path to report.json"),
    params: str = typer.Option(None, "--params", help="Path to resolved params JSON"),
    strict: bool = typer.Option(False, "--strict", help="Fail on any deviation"),
    report_only: bool = typer.Option(
        False, "--report-only", help="Validate only report.json schema"
    ),
):
    """Verify produced artifacts. Placeholder scaffold."""
    typer.echo("Verify command scaffold. Implementation pending.")
    raise typer.Exit(code=0)


def main(argv: list[str] | None = None) -> int:
    try:
        app(standalone_mode=True)
        return 0
    except SystemExit as e:
        return int(e.code)
    except Exception as exc:  # pragma: no cover - scaffold safety
        typer.echo(str(exc))
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
