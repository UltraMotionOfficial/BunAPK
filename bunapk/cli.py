"""Typer CLI — command routing for the bundle downloader (default), info, search.

This module is intentionally thin: it defines the commands and their flags, and
delegates the real work to :mod:`bunapk.bundler` and :mod:`bunapk.play`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
import typer
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from typer.core import TyperGroup

from bunapk.bundler import download_bundle
from bunapk.play import AuthExpiredError, PlayAPIError, get_details, search_apps
from bunapk.session import console, err, require_auth
from bunapk.utils import default_output_dir, resolve_output_dir

# Resolved once at import: the OS-aware folder downloads land in by default
# (Termux -> /storage/emulated/0/BunAPK, otherwise ~/Downloads/BunAPK).
DEFAULT_OUTPUT_DIR = default_output_dir()


def _downloader_usage_panel() -> Panel:
    """Boxed 'Downloader Usage' panel shown at the top of `bunapk --help`.

    Styled to match Typer's own Options/Commands panels (rounded box, dim
    border, left-aligned title).
    """
    body = Group(
        Text.from_markup(
            "Download split APK bundles from the Google Play Store."
        ),
        Text.from_markup(
            "\nRun [bold]bunapk PACKAGE[/] to fetch every architecture, density "
            "and language\nsplit and package them into one installable "
            "[bold].apks[/] bundle:"
        ),
        Text.from_markup("\n    [cyan]bunapk com.example.app[/]\n"),
        Text.from_markup(
            "  [bold]-o[/] PATH   Output directory for the finished bundle "
            f"[dim](default: {DEFAULT_OUTPUT_DIR})[/]"
        ),
        Text.from_markup(
            "  [bold]-i[/] FILE   Batch mode — a text file with one version "
            "code per line"
        ),
        Text.from_markup(
            "  [bold]-l, --limit[/] N   Cap the number of versions processed "
            "from the batch file"
        ),
    )
    return Panel(
        body,
        border_style="dim",
        title="Downloader Usage",
        title_align="left",
    )


class DefaultCommandGroup(TyperGroup):
    """CLI group that treats a bare package name as the download command.

    There is no ``download`` sub-command to type: ``bunapk com.example.app``
    downloads an ``.apks`` bundle directly. Any first argument that is neither a
    registered sub-command (``info`` / ``search``) nor an option flag is
    rewritten to ``download <args>`` *before* parsing, so it routes to the
    hidden bundle downloader, while ``info`` and ``search`` keep working as
    normal sub-commands.

    The rewrite happens in ``parse_args`` — which runs before command
    resolution — rather than by catching a "no such command" error during
    resolution. Typer vendors its own Click fork, so the error raised at that
    point is ``typer._click``'s ``UsageError``, not the upstream
    ``click.UsageError``; the two are unrelated classes and cannot be caught
    across that boundary. Rewriting the args list sidesteps exceptions entirely.
    """

    default_command = "download"

    def parse_args(self, ctx, args):
        if args and not args[0].startswith("-") and args[0] not in self.commands:
            # Bare package name → route to the default bundle downloader.
            args = [self.default_command, *args]
        return super().parse_args(ctx, args)

    def format_help(self, ctx, formatter):
        """Render help as styled Rich panels only.

        Replaces Typer's default layout: the bare ``Usage:`` line and the
        floating help docstring are dropped in favour of a boxed 'Downloader
        Usage' panel, followed by the standard Options and Commands panels.
        """
        from typer import rich_utils as ru

        help_console = ru._get_rich_console()
        markup_mode = getattr(self, "rich_markup_mode", "rich") or "rich"

        help_console.print(_downloader_usage_panel())

        options = [
            p for p in self.get_params(ctx)
            if isinstance(p, click.Option) and not getattr(p, "hidden", False)
        ]
        if options:
            ru._print_options_panel(
                name=ru.OPTIONS_PANEL_TITLE,
                params=options,
                ctx=ctx,
                markup_mode=markup_mode,
                console=help_console,
            )

        commands = []
        for name in self.list_commands(ctx):
            cmd = self.get_command(ctx, name)
            if cmd is not None and not cmd.hidden:
                commands.append(cmd)
        if commands:
            cmd_len = max(len(cmd.name or "") for cmd in commands)
            ru._print_commands_panel(
                name=ru.COMMANDS_PANEL_TITLE,
                commands=commands,
                markup_mode=markup_mode,
                console=help_console,
                cmd_len=cmd_len,
            )


app = typer.Typer(
    name="bunapk",
    cls=DefaultCommandGroup,
    help="Download split APK bundles from the Google Play Store.",
    add_completion=False,
    no_args_is_help=True,
)


# ── info ──────────────────────────────────────────────────────────────────────


@app.command()
def info(
    package: str = typer.Argument(..., help="Package name (e.g. com.example.app)."),
) -> None:
    """Show app details from Google Play."""
    auth_data = require_auth("arm64")

    with console.status(f"Fetching details for [bold]{package}[/bold]..."):
        try:
            try:
                details = get_details(package, auth_data)
            except AuthExpiredError:
                auth_data = require_auth("arm64", force=True)
                details = get_details(package, auth_data)
        except PlayAPIError as exc:
            err.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)

    table = Table(title=details.title or package, show_header=False, title_style="bold")
    table.add_column("Field", style="dim")
    table.add_column("Value")
    table.add_row("Package", details.package)
    table.add_row("Version", f"{details.version_string} ({details.version_code})")
    table.add_row("Developer", details.developer or "N/A")
    table.add_row("Rating", details.rating or "N/A")
    table.add_row("Downloads", details.downloads or "N/A")
    console.print(table)


# ── search ────────────────────────────────────────────────────────────────────


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query."),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results."),
) -> None:
    """Search for apps on Google Play."""
    auth_data = require_auth("arm64")

    with console.status(f"Searching for [bold]{query}[/bold]..."):
        try:
            try:
                results = search_apps(query, auth_data, limit=limit)
            except AuthExpiredError:
                auth_data = require_auth("arm64", force=True)
                results = search_apps(query, auth_data, limit=limit)
        except PlayAPIError as exc:
            err.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        raise typer.Exit()

    table = Table(title=f"Results for \"{query}\"")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold")
    table.add_column("Package")
    for i, app_item in enumerate(results, 1):
        table.add_row(str(i), app_item["title"], app_item["package"])
    console.print(table)


# ── download (default command) ─────────────────────────────────────────────────


@app.command("download", hidden=True)
def download(
    package: str = typer.Argument(..., help="Package name (e.g. com.example.app)."),
    output: Path = typer.Option(
        DEFAULT_OUTPUT_DIR,
        "--output", "-o",
        help=(
            "Where to save files. A plain name (e.g. 'my_apps') goes inside your "
            "Downloads folder; an absolute path is used as-is. Created if missing."
        ),
    ),
    versions_file: Optional[Path] = typer.Option(
        None,
        "--input", "-i",
        help="Path to a text file of version codes (one per line) for batch downloads."
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit", "-l",
        help="Cap the number of versions processed from the batch file."
    ),
) -> None:
    """Download base APK and splits for all device profiles, packaging them into .apks."""
    download_bundle(package, resolve_output_dir(output), versions_file=versions_file, limit=limit)


# ── entry point ────────────────────────────────────────────────────────────────

# Real sub-commands. Anything else (and not an option flag) is a package name
# routed to the hidden `download` command. Package names always contain a dot,
# so they can never collide with these.
_SUBCOMMANDS = {"download", "info", "search"}


def main() -> None:
    """Console-script entry point with bare-package-name routing.

    Rewrites ``sys.argv`` *before* Typer/Click ever parses it: a first argument
    that is neither a real sub-command nor an option flag (``-``/``--``) has
    ``download`` spliced in front of it, so ``bunapk com.example.app`` runs
    the downloader without the word ``download``. Doing this at the entry point
    is independent of Typer's vendored Click internals — the most robust place
    to route. ``info`` / ``search`` and ``--help`` pass through untouched.
    """
    if len(sys.argv) > 1:
        first = sys.argv[1]
        if first not in _SUBCOMMANDS and not first.startswith("-"):
            sys.argv.insert(1, "download")
    app()


if __name__ == "__main__":
    main()
