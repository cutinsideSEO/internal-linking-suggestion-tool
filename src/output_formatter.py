"""Output formatting module for console and CSV export."""

import csv
from datetime import datetime
from pathlib import Path
from typing import TextIO

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .link_finder import LinkSuggestion
from .utils import truncate_text


console = Console()


def print_table(
    suggestions: list[LinkSuggestion],
    source_url: str,
    keywords_count: int,
    max_rows: int = None
) -> None:
    """
    Print suggestions as a formatted table to the console.

    Args:
        suggestions: List of LinkSuggestion objects
        source_url: The original source URL analyzed
        keywords_count: Number of keywords extracted
        max_rows: Maximum rows to display (None for all)
    """
    # Print header
    console.print()
    console.print(Panel(
        f"[bold]Internal Linking Suggestions[/bold]\n"
        f"Source: [cyan]{source_url}[/cyan]",
        expand=False
    ))

    # Print summary stats
    console.print(
        f"\n[green]Keywords extracted:[/green] {keywords_count}  |  "
        f"[green]Suggestions found:[/green] {len(suggestions)}\n"
    )

    if not suggestions:
        console.print("[yellow]No internal linking opportunities found.[/yellow]")
        return

    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Suggested Anchor Text", style="green", width=30)
    table.add_column("Target URL", style="blue", width=50)
    table.add_column("Rank", justify="center", width=6)
    table.add_column("Score", justify="right", width=8)

    # Add rows
    display_suggestions = suggestions[:max_rows] if max_rows else suggestions

    for i, s in enumerate(display_suggestions, 1):
        table.add_row(
            str(i),
            truncate_text(s.anchor_text, 28),
            truncate_text(s.target_url, 48),
            str(s.position),
            f"{s.keyword_score:.1f}"
        )

    console.print(table)

    # Show truncation notice if applicable
    if max_rows and len(suggestions) > max_rows:
        console.print(
            f"\n[dim]Showing {max_rows} of {len(suggestions)} suggestions. "
            f"See CSV for complete results.[/dim]"
        )


def print_errors(errors: list[str]) -> None:
    """
    Print error messages to the console.

    Args:
        errors: List of error messages
    """
    if not errors:
        return

    console.print()
    console.print("[yellow]Warnings/Errors:[/yellow]")
    for error in errors:
        console.print(f"  [dim]- {error}[/dim]")


def export_csv(
    suggestions: list[LinkSuggestion],
    source_url: str,
    output_path: str = None
) -> str:
    """
    Export suggestions to a CSV file.

    Args:
        suggestions: List of LinkSuggestion objects
        source_url: The original source URL analyzed
        output_path: Output file path (auto-generated if None)

    Returns:
        The path to the created CSV file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"suggestions_{timestamp}.csv"

    path = Path(output_path)

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'Suggested Anchor Text',
            'Target URL',
            'Target Title',
            'Position',
            'Keyword Score',
            'Source URL'
        ])

        # Write data rows
        for s in suggestions:
            writer.writerow([
                s.anchor_text,
                s.target_url,
                s.target_title,
                s.position,
                round(s.keyword_score, 2),
                source_url
            ])

    return str(path.absolute())


def write_csv_to_stream(
    suggestions: list[LinkSuggestion],
    source_url: str,
    stream: TextIO
) -> None:
    """
    Write suggestions as CSV to a stream.

    Args:
        suggestions: List of LinkSuggestion objects
        source_url: The original source URL analyzed
        stream: Output stream to write to
    """
    writer = csv.writer(stream)

    # Write header
    writer.writerow([
        'Suggested Anchor Text',
        'Target URL',
        'Target Title',
        'Position',
        'Keyword Score',
        'Source URL'
    ])

    # Write data rows
    for s in suggestions:
        writer.writerow([
            s.anchor_text,
            s.target_url,
            s.target_title,
            s.position,
            round(s.keyword_score, 2),
            source_url
        ])


def format_progress(current: int, total: int, keyword: str) -> str:
    """
    Format a progress message for keyword processing.

    Args:
        current: Current keyword number
        total: Total keywords
        keyword: Current keyword being processed

    Returns:
        Formatted progress string
    """
    return f"[{current}/{total}] Searching: {truncate_text(keyword, 40)}"
