"""Device profiles for Google Play API authentication.

Loads Aurora Store .properties files from the profiles/ directory.
Profiles are rotated during token acquisition for reliability.
"""

from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parent / "profiles"

FALLBACK_PROFILE = {
    "UserReadableName": "Generic ARM64 Device",
    "Build.HARDWARE": "qcom",
    "Build.RADIO": "unknown",
    "Build.BOOTLOADER": "unknown",
    "Build.FINGERPRINT": "google/sunfish/sunfish:13/TQ3A.230805.001/10316531:user/release-keys",
    "Build.BRAND": "google",
    "Build.DEVICE": "sunfish",
    "Build.VERSION.SDK_INT": "33",
    "Build.VERSION.RELEASE": "13",
    "Build.MODEL": "Pixel 4a",
    "Build.MANUFACTURER": "Google",
    "Build.PRODUCT": "sunfish",
    "Build.ID": "TQ3A.230805.001",
    "Build.TYPE": "user",
    "Build.TAGS": "release-keys",
    "Build.SUPPORTED_ABIS": "arm64-v8a,armeabi-v7a,armeabi",
    "Platforms": "arm64-v8a,armeabi-v7a,armeabi",
    "Screen.Density": "440",
    "Screen.Width": "1080",
    "Screen.Height": "2340",
    "Locales": "en-US",
    "SharedLibraries": (
        "android.ext.shared,android.test.base,android.test.mock,android.test.runner,"
        "com.android.future.usb.accessory,com.android.location.provider,"
        "com.android.media.remotedisplay,com.android.mediadrm.signer,"
        "com.android.nfc_extras,com.google.android.gms,com.google.android.maps,"
        "javax.obex,org.apache.http.legacy"
    ),
    "Features": (
        "android.hardware.audio.output,android.hardware.bluetooth,"
        "android.hardware.bluetooth_le,android.hardware.camera,"
        "android.hardware.camera.autofocus,android.hardware.camera.flash,"
        "android.hardware.camera.front,android.hardware.faketouch,"
        "android.hardware.fingerprint,android.hardware.location,"
        "android.hardware.location.gps,android.hardware.location.network,"
        "android.hardware.microphone,android.hardware.nfc,"
        "android.hardware.screen.landscape,android.hardware.screen.portrait,"
        "android.hardware.sensor.accelerometer,android.hardware.sensor.compass,"
        "android.hardware.sensor.gyroscope,android.hardware.sensor.light,"
        "android.hardware.sensor.proximity,android.hardware.telephony,"
        "android.hardware.touchscreen,android.hardware.touchscreen.multitouch,"
        "android.hardware.touchscreen.multitouch.distinct,"
        "android.hardware.touchscreen.multitouch.jazzhand,"
        "android.hardware.usb.accessory,android.hardware.usb.host,"
        "android.hardware.wifi,android.hardware.wifi.direct,"
        "android.software.app_widgets,android.software.backup,"
        "android.software.home_screen,android.software.input_methods,"
        "android.software.live_wallpaper,android.software.print,"
        "android.software.webview"
    ),
    "GSF.version": "223616055",
    "Vending.version": "82151710",
    "Vending.versionString": "21.5.17-21 [0] [PR] 326734551",
    "Roaming": "mobile-notroaming",
    "TimeZone": "America/New_York",
    "CellOperator": "310260",
    "SimOperator": "310260",
    "Client": "android-google",
    "GL.Version": "196610",
    "GL.Extensions": (
        "GL_OES_EGL_image,GL_OES_EGL_image_external,GL_OES_EGL_sync,"
        "GL_OES_vertex_half_float,GL_OES_framebuffer_object,"
        "GL_OES_rgb8_rgba8,GL_OES_compressed_ETC1_RGB8_texture,"
        "GL_EXT_texture_format_BGRA8888,GL_OES_texture_npot,"
        "GL_OES_packed_depth_stencil,GL_OES_depth24,"
        "GL_OES_depth_texture,GL_OES_texture_float,"
        "GL_OES_texture_half_float,GL_OES_element_index_uint,"
        "GL_OES_vertex_array_object"
    ),
}

# Tested priority order — profiles that work best with Aurora dispenser and
# restricted apps (banking apps like Chase). Pixel 9a first for arm64.
_PRIORITY_ARM64 = [
    "14-pixel-9a", "05-samsung-f34-5g", "19-xperia-5", "20-oppo-r17",
    "07-xiaomi-mi-a1", "10-redmi-note-12-4g", "15-nothing-phone-1",
    "11-redmi-7", "22-huawei-mate-20", "04-galaxy-s25-ultra",
]
_PRIORITY_ARMV7 = ["16-samsung-j5-prime", "09-samsung-a13-5g", "12-realme-5-pro", "08-bravia-vu2"]


def _load_properties(filepath: Path) -> dict:
    """Parse a Java-style .properties file into a dict."""
    profile: dict[str, str] = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                profile[key] = val
    return profile


def load_all_profiles() -> dict:
    """Load every .properties file from the profiles directory."""
    profiles: dict[str, dict] = {}
    if not PROFILES_DIR.exists():
        return profiles
    for fp in sorted(PROFILES_DIR.glob("*.properties")):
        profile = _load_properties(fp)
        platforms = profile.get("Platforms", "")
        if "arm64-v8a" in platforms:
            arch = "arm64"
        elif "armeabi-v7a" in platforms:
            arch = "armv7"
        elif "x86" in platforms:
            arch = "x86"
        else:
            arch = "unknown"
        profiles[fp.stem] = {
            "name": profile.get("UserReadableName", fp.stem),
            "arch": arch,
            "profile": profile,
        }
    return profiles


_ALL = load_all_profiles()

ARM64_PROFILES: list[tuple[str, dict]] = [
    (k, d["profile"]) for k, d in _ALL.items() if d["arch"] == "arm64"
]
ARMV7_PROFILES: list[tuple[str, dict]] = [
    (k, d["profile"]) for k, d in _ALL.items() if d["arch"] == "armv7"
]


def get_priority_profiles(arch: str = "arm64") -> list[tuple[str, dict]]:
    """Return profiles ordered by reliability (best first)."""
    if arch == "armv7":
        priority, pool = _PRIORITY_ARMV7, ARMV7_PROFILES
    else:
        priority, pool = _PRIORITY_ARM64, ARM64_PROFILES

    seen: set[str] = set()
    result: list[tuple[str, dict]] = []

    for key in priority:
        for pkey, profile in pool:
            if pkey == key and pkey not in seen:
                result.append((pkey, profile))
                seen.add(pkey)
                break

    for pkey, profile in pool:
        if pkey not in seen:
            result.append((pkey, profile))
            seen.add(pkey)

    return result


# ---------------------------------------------------------------------------
# Device-profile selection for split-APK delivery
#
# To make Google Play hand over every architecture / density / language split,
# we present it a series of synthetic device profiles — one per (arch, density)
# permutation. The helpers below pick the closest real profile for a target and
# tailor it so the requested splits are delivered.
# ---------------------------------------------------------------------------

# Priority profile stems per architecture (best-known to work with the dispenser)
_BASE_PRIORITY_ARM64 = [
    "14-pixel-9a", "05-samsung-f34-5g", "19-xperia-5", "20-oppo-r17",
    "07-xiaomi-mi-a1", "10-redmi-note-12-4g", "15-nothing-phone-1",
    "11-redmi-7", "22-huawei-mate-20", "04-galaxy-s25-ultra",
]
_BASE_PRIORITY_ARMV7 = ["16-samsung-j5-prime", "09-samsung-a13-5g", "12-realme-5-pro"]

# Above this density (xxxhdpi) we synthesize a Nexus 6P profile so 640dpi splits
# are reliably delivered.
_XXXHDPI_THRESHOLD = 560


def supported_abis(target_arch: str) -> str:
    """Return the ``SUPPORTED_ABIS`` list a device of *target_arch* would report."""
    if target_arch == "arm64-v8a":
        return "arm64-v8a,armeabi-v7a,armeabi"
    elif target_arch == "armeabi-v7a":
        return "armeabi-v7a,armeabi"
    elif target_arch == "x86":
        return "x86,armeabi-v7a,armeabi"
    elif target_arch == "x86_64":
        return "x86_64,x86,arm64-v8a,armeabi-v7a,armeabi"
    return target_arch


def _nexus_6p_profile(target_arch: str, target_density: str) -> dict:
    """Synthesize a Nexus 6P base for xxxhdpi so 640dpi splits are delivered."""
    nexus_6p = FALLBACK_PROFILE.copy()
    nexus_6p["UserReadableName"] = f"Custom {target_arch} Nexus 6P 640"
    nexus_6p["Build.MANUFACTURER"] = "Huawei"
    nexus_6p["Build.MODEL"] = "Nexus 6P"
    nexus_6p["Build.BRAND"] = "google"
    nexus_6p["Build.DEVICE"] = "angler"
    nexus_6p["Build.PRODUCT"] = "angler"
    nexus_6p["Build.FINGERPRINT"] = "google/angler/angler:8.1.0/OPM7.181205.001/5086250:user/release-keys"
    nexus_6p["Screen.Density"] = str(target_density)
    nexus_6p["Screen.Width"] = "1440"
    nexus_6p["Screen.Height"] = "2560"
    nexus_6p["Platforms"] = supported_abis(target_arch)
    nexus_6p["Build.SUPPORTED_ABIS"] = supported_abis(target_arch)
    return nexus_6p


def _ranked_base_profiles(all_profiles: dict, target_arch: str, target_density: str) -> list[dict]:
    """Return compatible base profiles for the target, closest density first.

    The first element matches the legacy single-pick behaviour; the remaining
    elements are fallbacks the caller can try if the preferred profile fails to
    authenticate.
    """
    try:
        target_density_int = int(target_density)
    except ValueError:
        target_density_int = 480

    if target_density_int >= _XXXHDPI_THRESHOLD:
        # For xxxhdpi, a custom Nexus 6P is the only reliable base.
        return [_nexus_6p_profile(target_arch, target_density)]

    # 1. Gather compatible priority profiles for the target architecture
    if target_arch == "arm64-v8a":
        priority_stems = _BASE_PRIORITY_ARM64
    elif target_arch == "armeabi-v7a":
        priority_stems = _BASE_PRIORITY_ARMV7
    else:
        priority_stems = list(all_profiles.keys())

    compatible_profiles = []
    for stem in priority_stems:
        if stem in all_profiles:
            d = all_profiles[stem]
            profile = d["profile"]
            platforms = profile.get("Platforms", "")
            name = d.get("name", "").lower()
            features = profile.get("Features", "").lower()
            if "tv" in name or "bravia" in name or "android.software.leanback" in features:
                continue
            if target_arch in platforms:
                compatible_profiles.append(profile)

    if not compatible_profiles:
        return [FALLBACK_PROFILE.copy()]

    # 2. For 32-bit targets (armeabi-v7a or x86), prefer strict 32-bit profiles (no arm64-v8a)
    if target_arch in ("armeabi-v7a", "x86"):
        strict = [p for p in compatible_profiles if "arm64-v8a" not in p.get("Platforms", "")]
        candidates = strict if strict else compatible_profiles
    else:
        candidates = compatible_profiles

    # 3. Rank by closeness of native density to the target. A *stable* sort keeps
    # priority order among equally-close profiles, so the first element is
    # identical to the previous min()-based single pick.
    def _density_diff(p: dict) -> int:
        try:
            native_density = int(p.get("Screen.Density", "480"))
        except ValueError:
            native_density = 480
        return abs(native_density - target_density_int)

    return sorted(candidates, key=_density_diff)


def select_base_profile(all_profiles: dict, target_arch: str, target_density: str) -> dict:
    """Pick the best base profile for *target_arch* at *target_density*.

    Returns a fresh dict (safe to mutate). Falls back to ``FALLBACK_PROFILE``
    when no compatible profile is found.
    """
    ranked = _ranked_base_profiles(all_profiles, target_arch, target_density)
    return ranked[0].copy() if ranked else FALLBACK_PROFILE.copy()


def _tailor_profile(base: dict, target_arch: str, target_density: str, label: str) -> dict:
    """Pin a base profile to the requested arch + density (returns a fresh dict)."""
    profile = base.copy()
    profile["Screen.Density"] = str(target_density)
    profile["Platforms"] = supported_abis(target_arch)
    profile["Build.SUPPORTED_ABIS"] = supported_abis(target_arch)
    profile["UserReadableName"] = label
    return profile


def device_profile(all_profiles: dict, target_arch: str, target_density: str) -> dict:
    """Return a synthetic device profile pinned to *target_arch* + *target_density*."""
    base = select_base_profile(all_profiles, target_arch, target_density)
    return _tailor_profile(
        base, target_arch, target_density, f"Custom {target_arch} {target_density}dpi Device"
    )


def device_profile_candidates(
    all_profiles: dict, target_arch: str, target_density: str, max_candidates: int = 4
) -> list[dict]:
    """Return up to *max_candidates* synthetic profiles for the target, best first.

    The first entry is equivalent to :func:`device_profile`; the rest are
    distinct fallback devices so authentication can rotate to a different
    profile when the dispenser repeatedly rejects one (common for some 32-bit
    armeabi profiles).
    """
    bases = _ranked_base_profiles(all_profiles, target_arch, target_density)
    candidates: list[dict] = []
    seen_models: set[str] = set()
    for base in bases:
        model = base.get("Build.MODEL", "")
        if model and model in seen_models:
            continue
        seen_models.add(model)
        label = f"Custom {target_arch} {target_density}dpi {model or 'Device'}"
        candidates.append(_tailor_profile(base, target_arch, target_density, label))
        if len(candidates) >= max_candidates:
            break

    if not candidates:
        candidates.append(device_profile(all_profiles, target_arch, target_density))
    return candidates


def build_permutations(arches: list[str], dpis: list[str]) -> list[tuple[str, str]]:
    """Build the optimal ``(arch, density)`` permutations to query.

    All densities are queried on arm64-v8a (the most compatible arch) to harvest
    density splits, plus each non-arm64 arch at a standard density for its
    architecture-specific splits.
    """
    pairs: list[tuple[str, str]] = []
    for density in dpis:
        pairs.append(("arm64-v8a", density))

    standard_density = "320" if "320" in dpis else (dpis[0] if dpis else "480")
    for arch in arches:
        if arch != "arm64-v8a":
            pairs.append((arch, standard_density))

    return pairs
