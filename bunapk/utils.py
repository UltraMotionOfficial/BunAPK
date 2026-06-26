"""Small, dependency-free helpers shared across BunAPK."""

from __future__ import annotations

import os
import re
from pathlib import Path

# Folder name BunAPK creates inside the platform's download location.
APP_DIR_NAME = "BunAPK"


def _is_termux() -> bool:
    """Return True when running inside Termux on Android.

    Checks the env markers Termux sets, then falls back to the well-known
    install prefix on disk, so detection works even from a stripped env.
    """
    if os.environ.get("TERMUX_VERSION"):
        return True
    if "com.termux" in os.environ.get("PREFIX", ""):
        return True
    return os.path.isdir("/data/data/com.termux/files/usr")


def download_base_dir() -> Path:
    """Return the base folder BunAPK saves into (the OS 'Downloads' area).

    - **Termux (Android):** ``/storage/emulated/0`` (shared storage, so files
      are visible to other apps and file managers)
    - **macOS / Linux / Windows:** ``~/Downloads``

    ``pathlib`` resolves the home directory and joins path segments correctly on
    every OS (including Windows backslashes), so no manual path handling needed.
    """
    if _is_termux():
        shared = Path("/storage/emulated/0")
        if shared.is_dir():
            return shared
    return Path.home() / "Downloads"


def default_output_dir() -> Path:
    """Default download directory: ``<Downloads>/BunAPK``.

    Created lazily by the downloader when a run starts — never as a side effect
    of importing this module.
    """
    return download_base_dir() / APP_DIR_NAME


def resolve_output_dir(value: "Path | str") -> Path:
    """Resolve a user-supplied ``-o`` value to an absolute folder.

    - An **absolute path** (or one starting with ``~``) is used exactly as given.
    - A **plain name or relative path** is placed *inside* the OS download
      folder, so ``-o myfolder`` becomes ``<Downloads>/myfolder`` instead of a
      stray folder next to wherever the command happened to be run.
    """
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return download_base_dir() / path


def format_size(size_bytes: int | float) -> str:
    """Format a byte count as a human-readable string (e.g. ``12.3 MB``)."""
    if not size_bytes:
        return "Unknown"
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def sanitize_filename(name: str) -> str:
    """Make *name* safe to use as part of a file name.

    Strips characters illegal on common filesystems (path separators, the
    Windows-reserved set, and control chars), collapses whitespace, and trims
    leading/trailing dots and spaces.
    """
    if not name:
        return ""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.strip(". ")
