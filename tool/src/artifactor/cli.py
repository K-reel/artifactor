"""Command-line interface for Artifactor."""

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from .generator import PostGenerator
from .ingest import Ingester, IngestStatus

# Main app
app = typer.Typer(
    help="Generate Jekyll HTML posts from article data.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Artifactor: Generate Jekyll HTML posts from article data.

    I treat my writing like an artifact pipeline.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


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
    out: Annotated[
        Path,
        typer.Option(
            "--out",
            help="Output directory for Jekyll site (default: site/)",
        ),
    ] = Path("site"),
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            help="Request timeout in seconds",
        ),
    ] = 20,
    user_agent: Annotated[
        str,
        typer.Option(
            "--user-agent",
            help="User-Agent header for requests",
        ),
    ] = "Artifactor/0.1 (+https://github.com/K-reel/artifactor)",
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
    html_fixture: Annotated[
        Optional[Path],
        typer.Option(
            "--html-fixture",
            help="HTML fixture file for offline testing (no network fetch)",
            exists=True,
            dir_okay=False,
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

    Offline mode:
        Use --html-fixture to provide a sample HTML file for testing without
        network requests. All URLs will be processed using this HTML content.

    Example:
        artifactor ingest --urls urls.txt --out site/
        artifactor ingest --urls urls.txt --out site/ --limit 5 --dry-run
        artifactor ingest --urls urls.txt --out site/ --html-fixture fixtures/sample.html --dry-run
    """
    if dry_run:
        typer.echo("[DRY RUN MODE - No files will be written]")
        typer.echo()

    if html_fixture:
        typer.echo(f"OFFLINE MODE: using {html_fixture} for all URLs")
        typer.echo()

    ingester = Ingester(
        output_dir=out,
        timeout=timeout,
        user_agent=user_agent,
        dry_run=dry_run,
        html_fixture=html_fixture,
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
