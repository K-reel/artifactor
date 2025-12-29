"""Command-line interface for Artifactor."""

import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from typing_extensions import Annotated

from .config import ArtifactorConfig, load_config, discover_config_file
from .config.loader import config_to_dict
from .generator import PostGenerator
from .ingest import Ingester, IngestStatus

# Main app
app = typer.Typer(
    help="Generate Jekyll HTML posts from article data.",
    no_args_is_help=True,
    add_completion=False,
)

# Config subcommand app
config_app = typer.Typer(help="Configuration management commands")
app.add_typer(config_app, name="config")


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Artifactor: Generate Jekyll HTML posts from article data.

    I treat my writing like an artifact pipeline.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@config_app.command(name="validate")
def config_validate(
    config_file: Annotated[
        Optional[Path],
        typer.Option(
            "--config",
            help="Path to config file (default: discover artifactor.yml)",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
):
    """Validate configuration file.

    Checks for:
    - Valid YAML syntax
    - Required fields present
    - Valid values and types
    - Deterministic defaults

    Exit code 0 if valid, non-zero if invalid.

    Example:
        artifactor config validate
        artifactor config validate --config my-config.yml
    """
    try:
        # Try to load config
        config = load_config(config_file)

        # If we got here, config is valid
        if config_file:
            typer.echo(f"✓ Config file is valid: {config_file}")
        else:
            discovered = discover_config_file()
            if discovered:
                typer.echo(f"✓ Config file is valid: {discovered}")
            else:
                typer.echo("✓ Using default configuration (no config file found)")

        typer.echo()
        typer.echo("Configuration summary:")
        typer.echo(f"  Version: {config.version}")
        typer.echo(f"  Site directory: {config.output.site_dir}")
        typer.echo(f"  Posts directory: {config.output.posts_dir}")
        typer.echo(f"  Allow network: {config.input.allow_network}")
        typer.echo(f"  Default adapter: {config.input.default_adapter}")

    except FileNotFoundError as e:
        typer.echo(f"✗ Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"✗ Validation failed: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"✗ Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@config_app.command(name="print")
def config_print(
    config_file: Annotated[
        Optional[Path],
        typer.Option(
            "--config",
            help="Path to config file (default: discover artifactor.yml)",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    resolved: Annotated[
        bool,
        typer.Option(
            "--resolved",
            help="Show resolved config with all defaults filled in",
        ),
    ] = False,
):
    """Print configuration in YAML format.

    Shows the current configuration after merging defaults with any config file.
    Output is deterministically ordered.

    Example:
        artifactor config print
        artifactor config print --config my-config.yml
        artifactor config print --resolved
    """
    try:
        # Load config
        config = load_config(config_file)

        # Convert to dict and print as YAML
        config_dict = config_to_dict(config)

        # Print with stable ordering (sort_keys=False to preserve our explicit ordering)
        yaml_output = yaml.safe_dump(
            config_dict,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        if resolved:
            typer.echo("# Resolved configuration (with all defaults)")
        else:
            typer.echo("# Current configuration")

        if config_file:
            typer.echo(f"# Source: {config_file}")
        else:
            discovered = discover_config_file()
            if discovered:
                typer.echo(f"# Source: {discovered}")
            else:
                typer.echo("# Source: built-in defaults (no config file)")

        typer.echo()
        typer.echo(yaml_output)

    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="scaffold")
def scaffold(
    out: Annotated[
        Path,
        typer.Option(
            "--out",
            help="Output directory for Jekyll site (e.g., site/)",
            dir_okay=True,
            file_okay=False,
        ),
    ],
    fixture: Annotated[
        Path,
        typer.Option(
            "--fixture",
            help="Path to fixture JSON file representing an Article",
            exists=True,
            dir_okay=False,
        ),
    ],
):
    """Generate a sample Jekyll post from a fixture file.

    This command reads a JSON fixture representing an Article object
    and generates a Jekyll HTML post with YAML front matter.

    Example:
        artifactor scaffold --out site/ --fixture fixtures/sample_article.json
    """
    generator = PostGenerator()

    # Load article from fixture
    article = generator.load_article_from_fixture(fixture)

    # Generate post in _posts subdirectory
    posts_dir = out / "_posts"
    output_path = generator.generate_post(article, posts_dir)

    typer.echo(f"Generated post: {output_path}")
    typer.echo(f"  Title: {article.title}")
    typer.echo(f"  Date: {article.date}")
    typer.echo(f"  Source: {article.source}")


@app.command(name="ingest")
def ingest(
    urls: Annotated[
        Path,
        typer.Option(
            "--urls",
            help="Path to file containing URLs (one per line, # for comments)",
            exists=True,
            dir_okay=False,
        ),
    ],
    config_file: Annotated[
        Optional[Path],
        typer.Option(
            "--config",
            help="Path to config file (default: discover artifactor.yml)",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    out: Annotated[
        Optional[Path],
        typer.Option(
            "--out",
            help="Output directory for Jekyll site (overrides config)",
        ),
    ] = None,
    posts_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--posts-dir",
            help="Posts output directory (overrides config)",
        ),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            help="Request timeout in seconds",
        ),
    ] = 20,
    user_agent: Annotated[
        Optional[str],
        typer.Option(
            "--user-agent",
            help="User-Agent header for requests (overrides config)",
        ),
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option(
            "--limit",
            help="Process only first N URLs (useful for testing)",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would be done without writing files",
        ),
    ] = False,
    offline: Annotated[
        bool,
        typer.Option(
            "--offline",
            help="Disable network access (requires --html-fixture)",
        ),
    ] = False,
    allow_network: Annotated[
        Optional[bool],
        typer.Option(
            "--allow-network/--no-allow-network",
            help="Explicitly enable/disable network access (overrides config)",
        ),
    ] = None,
    html_fixture: Annotated[
        Optional[Path],
        typer.Option(
            "--html-fixture",
            help="HTML fixture file for offline testing (no network fetch)",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    require_date: Annotated[
        Optional[bool],
        typer.Option(
            "--require-date/--no-require-date",
            help="Require date in articles (overrides config)",
        ),
    ] = None,
    fallback_date: Annotated[
        Optional[str],
        typer.Option(
            "--fallback-date",
            help="Fallback date for articles without dates (YYYY-MM-DD)",
        ),
    ] = None,
):
    """Ingest URLs and generate Jekyll posts.

    Reads a list of URLs from a file, fetches each URL, extracts article
    content, and generates Jekyll HTML posts with YAML front matter.

    URL file format:
        - One URL per line
        - Blank lines ignored
        - Lines starting with # are comments

    Configuration:
        Uses artifactor.yml if present, or built-in defaults.
        CLI options override config file settings.

    Offline mode:
        Use --html-fixture to provide a sample HTML file for testing without
        network requests. All URLs will be processed using this HTML content.

    Example:
        artifactor ingest --urls urls.txt
        artifactor ingest --urls urls.txt --config my-config.yml
        artifactor ingest --urls urls.txt --offline --html-fixture fixtures/sample.html
        artifactor ingest --urls urls.txt --limit 5 --dry-run
    """
    if dry_run:
        typer.echo("[DRY RUN MODE - No files will be written]")
        typer.echo()

    # Load configuration
    try:
        config = load_config(config_file)

        # Apply CLI overrides
        config = config.merge_cli_overrides(
            config_file=config_file,
            site_dir=out,
            posts_dir=posts_dir,
            allow_network=allow_network,
            offline=offline,
            require_date=require_date,
            fallback_date=fallback_date,
        )

    except (FileNotFoundError, ValueError) as e:
        typer.echo(f"Config error: {e}", err=True)
        raise typer.Exit(1)

    # Validate offline mode
    if offline and html_fixture is None:
        typer.echo("Error: --offline requires --html-fixture", err=True)
        raise typer.Exit(1)

    if not config.input.allow_network and html_fixture is None:
        typer.echo("Error: Network disabled but no --html-fixture provided", err=True)
        raise typer.Exit(1)

    if html_fixture:
        typer.echo(f"OFFLINE MODE: using {html_fixture} for all URLs")
        typer.echo()

    # Use resolved config values (already merged with CLI overrides)
    output_dir = Path(config.output.site_dir)
    final_posts_dir = Path(config.output.posts_dir)
    final_user_agent = user_agent if user_agent else config.input.user_agent

    ingester = Ingester(
        output_dir=output_dir,
        posts_dir=final_posts_dir,
        timeout=timeout,
        user_agent=final_user_agent,
        dry_run=dry_run,
        html_fixture=html_fixture,
        config=config,
    )

    # Read URLs from file
    try:
        url_list = ingester.read_urls(urls)
    except Exception as e:
        typer.echo(f"Error reading URLs file: {e}", err=True)
        raise typer.Exit(1)

    if not url_list:
        typer.echo("No URLs found in file", err=True)
        raise typer.Exit(1)

    typer.echo(f"Found {len(url_list)} URL(s) to process")
    if limit:
        typer.echo(f"Processing first {limit} URL(s)")
    typer.echo()

    # Process URLs
    results = ingester.ingest_urls(url_list, limit=limit)

    # Display results
    for result in results:
        status_symbol = {
            IngestStatus.CREATED: "✓",
            IngestStatus.UPDATED: "↻",
            IngestStatus.UNCHANGED: "=",
            IngestStatus.FAILED: "✗",
        }[result.status]

        status_text = result.status.value.upper()

        if result.status == IngestStatus.FAILED:
            typer.echo(f"{status_symbol} {status_text}: {result.url}")
            typer.echo(f"  Error: {result.error}")
        else:
            typer.echo(f"{status_symbol} {status_text}: {result.url}")
            if result.filename:
                typer.echo(f"  File: {result.filename}")

    # Summary
    typer.echo()
    created = sum(1 for r in results if r.status == IngestStatus.CREATED)
    updated = sum(1 for r in results if r.status == IngestStatus.UPDATED)
    unchanged = sum(1 for r in results if r.status == IngestStatus.UNCHANGED)
    failed = sum(1 for r in results if r.status == IngestStatus.FAILED)

    typer.echo(f"Summary: {created} created, {updated} updated, {unchanged} unchanged, {failed} failed")

    if failed > 0:
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
