"""CLI entry point for the Internal Linking Suggestion Tool."""

import sys

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config
from .dataforseo_client import AuthenticationError
from .link_finder import InternalLinkFinder
from .output_formatter import print_table, print_errors, export_csv
from .scraper import ScrapingError
from .utils import validate_url

console = Console()


def download_nltk_data():
    """Download required NLTK data if not already present."""
    import nltk
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        console.print("[dim]Downloading NLTK stopwords...[/dim]")
        nltk.download('stopwords', quiet=True)

    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        console.print("[dim]Downloading NLTK punkt tokenizer...[/dim]")
        nltk.download('punkt', quiet=True)

    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        console.print("[dim]Downloading NLTK punkt_tab tokenizer...[/dim]")
        nltk.download('punkt_tab', quiet=True)


@click.command()
@click.argument('url')
@click.option(
    '-o', '--output',
    default='suggestions.csv',
    help='Output CSV file path'
)
@click.option(
    '-k', '--max-keywords',
    default=None,
    type=int,
    help=f'Maximum keywords to extract (default: {Config.MAX_KEYWORDS})'
)
@click.option(
    '-d', '--depth',
    default=None,
    type=int,
    help=f'Search depth per keyword (default: {Config.SEARCH_DEPTH})'
)
@click.option(
    '--no-csv',
    is_flag=True,
    help='Skip CSV export, only show console output'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Show detailed progress information'
)
@click.option(
    '--max-display',
    default=20,
    type=int,
    help='Maximum rows to display in console (default: 20)'
)
def main(
    url: str,
    output: str,
    max_keywords: int,
    depth: int,
    no_csv: bool,
    verbose: bool,
    max_display: int
):
    """
    Find internal linking opportunities for a given URL.

    Analyzes the content of the provided URL, extracts relevant keywords,
    and searches for internal pages that could be linked to using those
    keywords as anchor text.

    Example:

        python -m src.main https://example.com/blog/my-post

        python -m src.main https://example.com/page -o results.csv -k 20
    """
    # Download NLTK data if needed
    download_nltk_data()

    # Validate URL
    if not validate_url(url):
        console.print(f"[red]Error:[/red] Invalid URL: {url}")
        console.print("Please provide a valid HTTP or HTTPS URL.")
        sys.exit(1)

    # Validate credentials
    try:
        Config.validate()
    except ValueError as e:
        console.print(f"[red]Configuration Error:[/red] {str(e)}")
        sys.exit(1)

    console.print()
    console.print(f"[bold]Analyzing:[/bold] [cyan]{url}[/cyan]")
    console.print()

    try:
        # Initialize finder
        finder = InternalLinkFinder(verbose=verbose)

        keywords_found = 0

        # Use progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            # Scraping task
            task = progress.add_task("Scraping page content...", total=None)

            def on_progress(current, total, keyword):
                nonlocal keywords_found
                keywords_found = total
                progress.update(
                    task,
                    description=f"[{current}/{total}] Searching: {keyword[:30]}..."
                )

            # Run the finder
            suggestions, errors = finder.find_opportunities(
                source_url=url,
                max_keywords=max_keywords,
                search_depth=depth,
                on_keyword_progress=on_progress
            )

        # Print results
        print_table(
            suggestions=suggestions,
            source_url=url,
            keywords_count=keywords_found,
            max_rows=max_display
        )

        # Print any errors/warnings
        print_errors(errors)

        # Export CSV if requested
        if not no_csv and suggestions:
            csv_path = export_csv(
                suggestions=suggestions,
                source_url=url,
                output_path=output
            )
            console.print(f"\n[green]Results exported to:[/green] {csv_path}")

        console.print()

        # Exit with error code if no suggestions found
        if not suggestions:
            sys.exit(1)

    except AuthenticationError as e:
        console.print(f"\n[red]Authentication Error:[/red] {str(e)}")
        console.print("Please check your DataForSEO credentials in the .env file.")
        sys.exit(1)

    except ScrapingError as e:
        console.print(f"\n[red]Scraping Error:[/red] {str(e)}")
        console.print("The URL could not be accessed or has no extractable content.")
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)

    except Exception as e:
        console.print(f"\n[red]Unexpected Error:[/red] {str(e)}")
        if verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == '__main__':
    main()
