"""Bundle orchestration: turn a package name into installable .apks files.

This drives the whole download pipeline:

  1. Parse the requested version(s).
  2. Build the (arch, density) device-profile permutations.
  3. Pre-flight authenticate every device session.
  4. For each version, fetch delivery URLs across all permutations, download
     every unique split in parallel, then package them into an ``.apks`` bundle
     (or save a standalone ``.apk`` for apps without splits).
"""

from __future__ import annotations

import shutil
import time
import zipfile
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.panel import Panel

from bunapk.auth import ensure_auth_for_profile
from bunapk.downloader import DownloadSpec, download_batch
from bunapk.manifest import read_apk_version
from bunapk.play import (
    AuthExpiredError,
    PlayAPIError,
    get_delivery,
    get_details,
    purchase,
)
from bunapk.profiles import build_permutations, device_profile_candidates, load_all_profiles
from bunapk.session import console, err, require_auth
from bunapk.utils import format_size, sanitize_filename

# Default coverage: all mobile architectures, densities (ldpi → xxxhdpi), and common languages.
DEFAULT_ARCHES = ["arm64-v8a", "armeabi-v7a"]
DEFAULT_DPIS = ["120", "160", "213", "240", "320", "480", "640"]
DEFAULT_LANGUAGES = [
    "ar", "de", "en", "es", "et", "fi", "fr", "hi", "hu", "in",
    "it", "ja", "ko", "ms", "nl", "pl", "pt", "ru", "sv", "th",
    "tr", "uk", "vi", "zh",
]

_CONFIG_DIR = Path.home() / ".config" / "bunapk"
_MAX_AUTH_ATTEMPTS = 6
_RETRY_DELAY = 2  # base seconds between localized auth retries (grows exponentially)
_RETRY_BACKOFF_CAP = 30  # ceiling for the exponential backoff delay, in seconds


def _parse_version_codes(versions_file: Optional[Path], limit: Optional[int]) -> list[Optional[int]]:
    """Return the list of version codes to process.

    ``[None]`` means "the latest version". Reading from a batch file validates
    every line up front and aborts before any download if one is malformed.
    """
    if versions_file is None:
        return [None]

    if not versions_file.exists():
        err.print(f"[red]Versions file not found: {versions_file}[/red]")
        raise typer.Exit(code=1)
    try:
        lines = versions_file.read_text().splitlines()
    except Exception as exc:
        err.print(f"[red]Failed to read versions file {versions_file}: {exc}[/red]")
        raise typer.Exit(code=1)

    version_codes: list[Optional[int]] = []
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if not all(c.isdigit() or c.isspace() for c in line):
            err.print(
                f"[red]Invalid character found in versions file at line {line_num}: {repr(line)}. "
                f"Version codes must contain numbers only (no spaces, letters, or special characters).[/red]"
            )
            raise typer.Exit(code=1)
        if not stripped.isdigit():
            err.print(
                f"[red]Invalid version format in versions file at line {line_num}: {repr(line)}. "
                f"Version codes must be a single continuous number.[/red]"
            )
            raise typer.Exit(code=1)
        version_codes.append(int(stripped))

    if not version_codes:
        err.print(f"[red]No version codes found in versions file {versions_file}.[/red]")
        raise typer.Exit(code=1)

    if limit is not None and limit > 0 and len(version_codes) > limit:
        rprint(f"[dim]Limiting to the first {limit} of {len(version_codes)} version codes.[/dim]")
        version_codes = version_codes[:limit]

    return version_codes


def _preflight_authenticate(
    pairs: list[tuple[str, str]],
    profile_map: dict[tuple[str, str], dict],
    profile_candidates_map: dict[tuple[str, str], list[dict]],
    dispenser: Optional[str],
) -> dict[tuple[str, str], dict]:
    """Authenticate every device session before any download begins.

    Each session gets a localized retry loop with exponential backoff to absorb
    transient dispenser / token-refresh failures. Retries rotate through
    alternate device profiles, so a session whose preferred profile the
    dispenser keeps rejecting can still succeed with a different device. The
    profile that ultimately works is written back into *profile_map* so any
    later mid-download re-auth reuses it. If every attempt for a single session
    is exhausted we abort, since proceeding would silently drop the splits only
    that session can deliver.
    """
    num_profiles = len(pairs)
    rprint(f"[bold]Pre-flight: authenticating {num_profiles} device session(s)...[/bold]")

    sessions: dict[tuple[str, str], dict] = {}
    for idx, (arch, density) in enumerate(pairs, 1):
        candidates = profile_candidates_map[(arch, density)]

        cache_path = _CONFIG_DIR / f"auth-{arch}-{density}.json"
        if not cache_path.exists():
            # Throttle fresh dispenser requests to avoid rate-limiting.
            time.sleep(3)

        auth_data = None
        working_profile = candidates[0]
        for attempt in range(1, _MAX_AUTH_ATTEMPTS + 1):
            # Rotate device profiles across retries so we don't keep hammering a
            # profile the dispenser refuses. First attempt may use the cache;
            # retries force a fresh token.
            candidate = candidates[(attempt - 1) % len(candidates)]
            auth_data = ensure_auth_for_profile(
                arch=arch,
                density=density,
                profile=candidate,
                dispenser_url=dispenser,
                force_refresh=attempt > 1,
            )
            if auth_data:
                working_profile = candidate
                break
            if attempt < _MAX_AUTH_ATTEMPTS:
                next_attempt = attempt + 1
                # Exponential backoff, capped, to ease dispenser rate-limiting.
                delay = min(_RETRY_DELAY * 2 ** (attempt - 1), _RETRY_BACKOFF_CAP)
                next_candidate = candidates[(next_attempt - 1) % len(candidates)]
                profile_note = ""
                if len(candidates) > 1 and next_candidate is not candidate:
                    model = next_candidate.get("Build.MODEL", "alternate device")
                    profile_note = f", switching profile to [bold]{model}[/bold]"
                rprint(
                    f"  [yellow][Attempt {next_attempt}/{_MAX_AUTH_ATTEMPTS}] "
                    f"Retrying authentication for {arch}-{density} in {delay}s"
                    f"{profile_note}...[/yellow]"
                )
                time.sleep(delay)

        if not auth_data:
            err.print(
                f"[red]Pre-flight authentication failed for session {arch}-{density} "
                f"after {_MAX_AUTH_ATTEMPTS} attempts. Aborting before download to "
                f"avoid skipping its split APKs. Retry, or adjust the requested "
                f"profiles.[/red]"
            )
            raise typer.Exit(code=1)

        # Remember the profile that actually worked for any later re-auth.
        profile_map[(arch, density)] = working_profile

        rprint(f"[bold blue][{idx}/{num_profiles}][/bold blue] Session [bold]{arch}[/bold] @ [bold]{density} dpi[/bold] authenticated.")
        sessions[(arch, density)] = auth_data

    rprint(f"[green bold]All {num_profiles} device session(s) authenticated.[/green bold]\n")
    return sessions


def _split_filename(split_name: str) -> str:
    """Map a Play split id to its archive file name inside the .apks bundle."""
    if split_name.startswith("config."):
        return f"split_config.{split_name[7:]}.apk"
    return f"split_{split_name}.apk"


def download_bundle(
    package: str,
    output: Path,
    versions_file: Optional[Path] = None,
    limit: Optional[int] = None,
) -> None:
    """Download and package *package* into installable .apks bundle(s)."""
    dispenser = None  # the default dispenser is always used

    arches = DEFAULT_ARCHES
    dpis = DEFAULT_DPIS
    languages = DEFAULT_LANGUAGES

    version_codes = _parse_version_codes(versions_file, limit)

    all_profiles = load_all_profiles()

    pairs = build_permutations(arches, dpis)
    num_profiles = len(pairs)

    # Build device-profile candidates for each permutation once (profiles depend
    # only on architecture + density, never on the version code). The first
    # candidate is the preferred device; the rest are auth fallbacks.
    profile_candidates_map: dict[tuple[str, str], list[dict]] = {
        (arch, density): device_profile_candidates(all_profiles, arch, density)
        for arch, density in pairs
    }
    # Canonical profile per session (the preferred candidate). Pre-flight
    # overwrites each entry with whichever profile actually authenticated, so a
    # mid-download re-auth reuses the device that worked.
    profile_map: dict[tuple[str, str], dict] = {
        key: cands[0] for key, cands in profile_candidates_map.items()
    }

    sessions = _preflight_authenticate(pairs, profile_map, profile_candidates_map, dispenser)

    for current_version in version_codes:
        target_version = current_version
        version_name = None
        app_name = None

        # Pre-fetch latest version code if not specified
        if not target_version:
            try:
                with console.status(f"Pre-fetching latest version code for [bold]{package}[/bold]..."):
                    init_auth = require_auth("arm64", dispenser)
                    details = get_details(package, init_auth)
                    target_version = details.version_code
                    version_name = details.version_string
                    app_name = details.title
                    rprint(f"Latest version code detected: [bold]{target_version}[/bold] ({details.version_string})")
            except Exception as exc:
                err.print(f"[red]Failed to pre-fetch latest version code: {exc}[/red]")
                raise typer.Exit(code=1)
        else:
            # Try to resolve version name for explicitly specified version
            try:
                init_auth = require_auth("arm64", dispenser)
                det = get_details(package, init_auth)
                app_name = det.title
                if det.version_code == target_version:
                    version_name = det.version_string
                else:
                    # Try armv7 profile details
                    det_auth_v7 = require_auth("armv7", dispenser)
                    det_v7 = get_details(package, det_auth_v7)
                    app_name = det_v7.title or app_name
                    if det_v7.version_code == target_version:
                        version_name = det_v7.version_string
            except Exception:
                pass

        if version_name:
            display_version = f"{version_name} ({target_version})"
        else:
            display_version = f"{target_version}"

        rprint(f"\n[bold green]>>> Processing version {display_version}...[/bold green]")

        output.mkdir(parents=True, exist_ok=True)
        temp_dir = output / f"tmp_{package}_{target_version}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        rprint(f"Queued [bold]{num_profiles}[/bold] device profile permutations to cover:")
        rprint(f"  Architectures : {arches}")
        rprint(f"  Densities     : {dpis}")
        if languages:
            rprint(f"  Languages     : {languages}")
        rprint()

        version_downloads: dict[int, dict[str, DownloadSpec]] = {}

        # 1. Loop through all permutations to fetch delivery URLs.
        # Every session was authenticated during pre-flight, so we reuse those
        # tokens here. A token may still expire mid-run (>50 min), in which case
        # we re-authenticate that one session in place and keep going — we never
        # skip a permutation, since each one carries unique split APKs.
        for idx, (arch, density) in enumerate(pairs, 1):
            rprint(f"[bold blue][{idx}/{num_profiles}][/bold blue] Processing permutation: [bold]{arch}[/bold] @ [bold]{density} dpi[/bold]")

            custom_profile = profile_map[(arch, density)]
            auth_data = sessions[(arch, density)]

            try:
                with console.status(f"  Acquiring download URLs for {arch}-{density} (vc {target_version})..."):
                    purchase(package, target_version, auth_data)
                    delivery = get_delivery(package, target_version, auth_data, languages=languages)
            except AuthExpiredError:
                rprint("  [yellow]Auth token expired, re-authenticating session...[/yellow]")
                auth_data = ensure_auth_for_profile(
                    arch=arch,
                    density=density,
                    profile=custom_profile,
                    dispenser_url=dispenser,
                    force_refresh=True,
                )
                if not auth_data:
                    err.print(
                        f"  [red]Re-authentication failed for session {arch}-{density}. "
                        f"Aborting to avoid skipping its split APKs.[/red]"
                    )
                    raise typer.Exit(code=1)
                sessions[(arch, density)] = auth_data
                try:
                    purchase(package, target_version, auth_data)
                    delivery = get_delivery(package, target_version, auth_data, languages=languages)
                except PlayAPIError as exc:
                    err.print(f"  [red]PlayAPIError after refresh: {exc}. Skipping.[/red]")
                    continue
            except PlayAPIError as exc:
                err.print(f"  [red]PlayAPIError: {exc}. Skipping.[/red]")
                continue

            if target_version not in version_downloads:
                version_downloads[target_version] = {}

            target_specs = version_downloads[target_version]

            # Add base APK
            if "base.apk" not in target_specs and delivery.download_url:
                target_specs["base.apk"] = DownloadSpec(
                    url=delivery.download_url,
                    dest=temp_dir / f"base_{target_version}.apk",
                    cookies=delivery.cookies,
                    label=f"base_{target_version}.apk",
                )

            # Add split APKs
            if delivery.splits:
                for split in delivery.splits:
                    fname = _split_filename(split.name)
                    if fname not in target_specs:
                        temp_name = f"{split.name}_{target_version}.apk"
                        target_specs[fname] = DownloadSpec(
                            url=split.url,
                            dest=temp_dir / temp_name,
                            label=temp_name,
                        )

        # Flatten download specs for execution
        all_specs = []
        seen_dests = set()
        for vc_specs in version_downloads.values():
            for spec in vc_specs.values():
                if spec.dest not in seen_dests:
                    all_specs.append(spec)
                    seen_dests.add(spec.dest)

        if not all_specs:
            err.print(f"[red]No download URLs could be retrieved for version {target_version}. Skipping.[/red]")
            try:
                temp_dir.rmdir()
            except OSError:
                pass
            continue

        rprint(f"\nCollected [bold]{len(all_specs)}[/bold] unique APK files to download for version {target_version}.")
        rprint("[dim]Downloading in parallel...[/dim]")

        # 2. Run downloads
        try:
            download_batch(all_specs)
        except Exception as exc:
            err.print(f"[red]Download batch failed for version {target_version}: {exc}[/red]")
            # Clean up temp files for this version
            for spec in all_specs:
                if spec.dest.exists():
                    try:
                        spec.dest.unlink()
                    except OSError:
                        pass
            try:
                temp_dir.rmdir()
            except OSError:
                pass
            continue

        # Try to resolve version name from downloaded base APK if not resolved yet
        base_temp_path = temp_dir / f"base_{target_version}.apk"
        if base_temp_path.exists():
            extracted_code, extracted_name = read_apk_version(base_temp_path)

            # Critical validation: ensure the downloaded APK actually matches the requested version code
            if extracted_code is not None and extracted_code != target_version:
                err.print(
                    f"[red]Error: Google Play returned version code {extracted_code} instead of the "
                    f"requested {target_version} (this happens when the requested version is inactive). "
                    f"Skipping this version to prevent file mismatch.[/red]"
                )
                # Cleanup temp files for this version
                for spec in all_specs:
                    if spec.dest.exists():
                        try:
                            spec.dest.unlink()
                        except OSError:
                            pass
                try:
                    temp_dir.rmdir()
                except OSError:
                    pass
                continue

            if not version_name and extracted_name:
                version_name = extracted_name
                display_version = f"{version_name} ({target_version})"

        # 3. Save files: package into .apks if split app, or move directly if standalone APK
        # Output name leads with the sanitized app name, e.g. "uTorrent 8.3.6 (7633).apks"
        safe_app_name = sanitize_filename(app_name or "")
        file_stem = f"{safe_app_name} {display_version}".strip() if safe_app_name else display_version

        is_standalone = (len(target_specs) == 1 and "base.apk" in target_specs)

        if is_standalone:
            standalone_name = f"{file_stem}.apk"
            standalone_path = output / standalone_name
            rprint(f"\n[bold green]Standalone APK detected. Saving directly to {standalone_name}...[/bold green]")
            try:
                base_spec = target_specs["base.apk"]
                if base_spec.dest.exists():
                    shutil.move(str(base_spec.dest), str(standalone_path))
                    rprint(Panel.fit(
                        f"[bold green]Successfully saved standalone APK![/bold green]\n"
                        f"Output : [bold]{standalone_path}[/bold]\n"
                        f"Size   : {format_size(standalone_path.stat().st_size)}",
                        title=f"Save Complete (vc {target_version})",
                    ))
            except Exception as exc:
                err.print(f"[red]Failed to save standalone APK for version {target_version}: {exc}[/red]")
        else:
            apks_name = f"{file_stem}.apks"
            apks_path = output / apks_name
            rprint(f"\n[bold green]Packaging split APKs into {apks_name}...[/bold green]")
            try:
                with zipfile.ZipFile(apks_path, "w", zipfile.ZIP_STORED) as zf:
                    for zip_fname, spec in target_specs.items():
                        if spec.dest.exists():
                            zf.write(spec.dest, arcname=zip_fname)
                rprint(Panel.fit(
                    f"[bold green]Successfully created APK bundle![/bold green]\n"
                    f"Output : [bold]{apks_path}[/bold]\n"
                    f"Size   : {format_size(apks_path.stat().st_size)}",
                    title=f"Package Complete (vc {target_version})",
                ))
            except Exception as exc:
                err.print(f"[red]Packaging failed for version {target_version}: {exc}[/red]")

        # Cleanup temp files
        for spec in all_specs:
            if spec.dest.exists():
                try:
                    spec.dest.unlink()
                except OSError:
                    pass

        try:
            temp_dir.rmdir()
        except OSError:
            pass

    rprint(Panel.fit(
        f"[bold green]Successfully completed all batch downloads![/bold green]\n"
        f"Output directory : [bold]{output}[/bold]",
        title="Batch Operation Complete",
    ))
