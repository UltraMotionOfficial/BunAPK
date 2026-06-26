"""Shared Rich consoles and the auth-acquisition gate used by all commands.

Kept as a small leaf module so both the CLI layer and the bundler can depend
on it without importing each other (no circular imports).
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from bunapk.auth import ensure_auth

# Shared consoles — stdout for normal output, stderr for errors.
console = Console()
err = Console(stderr=True)


def require_auth(
    arch: str = "arm64",
    dispenser: Optional[str] = None,
    *,
    force: bool = False,
) -> dict:
    """Return a valid auth token, or exit the program with a helpful error."""
    data = ensure_auth(arch=arch, dispenser_url=dispenser, force_refresh=force)
    if not data:
        err.print(
            "[red]Could not obtain an auth token from the dispenser. "
            "Check your network connection and try again.[/red]"
        )
        raise typer.Exit(code=1)
    return data
