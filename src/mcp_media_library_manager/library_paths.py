"""Path validation and destination building for TV episode ingest operations.

This module provides pure, deterministic path handling logic for constructing
safe, standardized TV episode destination paths and enforcing filesystem root
boundaries.
"""

from pathlib import Path

# Characters invalid on Windows filesystems
# https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
WINDOWS_INVALID_CHARS = set('<>:"|?*\x00')


def validate_show_name(show_name: str) -> tuple[bool, str]:
    """Validate a show name for use in filesystem paths.

    Rejects names containing path separator characters (/ and \\) and other
    characters unsafe for cross-platform filesystem use.

    Args:
        show_name: The show name to validate.

    Returns:
        A tuple of (is_valid: bool, error_message: str). If valid, error_message
        is an empty string. If invalid, error_message explains why.
    """
    if not show_name:
        return False, "Show name cannot be empty"

    # Check for path separators
    if "/" in show_name or "\\" in show_name:
        return False, "Show name cannot contain path separator characters (/ or \\)"

    # Check for newlines and other problematic characters
    if "\n" in show_name or "\r" in show_name:
        return False, "Show name cannot contain newline characters"

    # Check for control characters (but not tab)
    for char in show_name:
        if ord(char) < 0x20 and char not in ("\t",):  # Allow tab but not other control chars
            return False, f"Show name contains invalid control character (U+{ord(char):04X})"

    return True, ""


def is_windows_safe_path_component(component: str) -> tuple[bool, str]:
    """Check if a path component is safe for Windows filesystems.

    Args:
        component: A single path component (folder or filename, no separators).

    Returns:
        A tuple of (is_safe: bool, error_message: str).
    """
    if not component:
        return False, "Path component cannot be empty"

    if len(component) > 255:
        return False, "Path component exceeds 255 characters"

    # Check for Windows-invalid characters
    for char in component:
        if char in WINDOWS_INVALID_CHARS:
            return False, f"Path component contains Windows-invalid character: {repr(char)}"

    # Check for control characters (except tab)
    for char in component:
        if ord(char) < 0x20:
            return False, f"Path component contains control character: U+{ord(char):04X}"

    # Check for trailing periods or spaces (Windows filesystem rules)
    if component.endswith(".") or component.endswith(" "):
        return False, "Path component cannot end with period or space"

    return True, ""


def is_source_path_inside_roots(source_path: str | Path, source_roots: tuple[Path, ...]) -> tuple[bool, str]:
    """Check if a source path is contained within one of the configured source roots.

    Args:
        source_path: The source file path to validate.
        source_roots: Tuple of configured source root paths.

    Returns:
        A tuple of (is_inside: bool, message: str). If inside, message is empty.
        If outside, message explains why.
    """
    try:
        source = Path(source_path).resolve()
    except (ValueError, RuntimeError) as e:
        return False, f"Could not resolve source path: {e}"

    for root in source_roots:
        try:
            root_resolved = root.resolve()
            # Check if source is inside root
            source.relative_to(root_resolved)
            return True, ""
        except ValueError:
            # source is not relative to this root, continue checking others
            continue

    roots_str = ", ".join(str(r) for r in source_roots)
    return False, f"Source path {source} is not inside any configured source root ({roots_str})"


def is_destination_path_inside_root(dest_path: str | Path, show_roots: tuple[Path, ...]) -> tuple[bool, str]:
    """Check if a destination path is contained within one of the configured show roots.

    Args:
        dest_path: The destination file path to validate.
        show_roots: Tuple of configured show root paths.

    Returns:
        A tuple of (is_inside: bool, message: str).
    """
    try:
        dest = Path(dest_path).resolve()
    except (ValueError, RuntimeError) as e:
        return False, f"Could not resolve destination path: {e}"

    for root in show_roots:
        try:
            root_resolved = root.resolve()
            dest.relative_to(root_resolved)
            return True, ""
        except ValueError:
            continue

    roots_str = ", ".join(str(r) for r in show_roots)
    return False, f"Destination path {dest} is not inside any configured show root ({roots_str})"


def build_tv_episode_destination_path(
    show_root: Path,
    show_name: str,
    first_air_year: int,
    season_number: int,
    episode_number: int,
) -> str:
    """Build a standardized TV episode destination path.

    Constructs the destination path using the format:
    `/<show_root>/<show_name> (<year>)/Season XX/SXXEXX.mkv`

    All path components are validated for Windows compatibility and cross-platform safety.

    Args:
        show_root: The base show root path.
        show_name: The TV show name.
        first_air_year: The year the show first aired.
        season_number: The season number (1-based).
        episode_number: The episode number (1-based).

    Returns:
        The full destination path as a string (using forward slashes).

    Raises:
        ValueError: If any input fails validation.
    """
    # Validate show name
    is_valid, error = validate_show_name(show_name)
    if not is_valid:
        raise ValueError(f"Invalid show name: {error}")

    # Validate year (should be a reasonable year)
    if not isinstance(first_air_year, int) or first_air_year < 1900 or first_air_year > 2100:
        raise ValueError(f"Invalid first_air_year: {first_air_year} (must be between 1900 and 2100)")

    # Validate season and episode numbers
    if not isinstance(season_number, int) or season_number < 1:
        raise ValueError(f"Invalid season_number: {season_number} (must be >= 1)")
    if not isinstance(episode_number, int) or episode_number < 1:
        raise ValueError(f"Invalid episode_number: {episode_number} (must be >= 1)")

    # Build show folder name: "Show Name (YYYY)"
    show_folder = f"{show_name} ({first_air_year})"
    is_safe, error = is_windows_safe_path_component(show_folder)
    if not is_safe:
        raise ValueError(f"Show folder name is unsafe for Windows: {error}")

    # Build season folder name: "Season XX"
    season_folder = f"Season {season_number:02d}"
    is_safe, error = is_windows_safe_path_component(season_folder)
    if not is_safe:
        raise ValueError(f"Season folder name is unsafe for Windows: {error}")

    # Build episode filename: "SXXEXX.mkv"
    episode_filename = f"S{season_number:02d}E{episode_number:02d}.mkv"
    is_safe, error = is_windows_safe_path_component(episode_filename)
    if not is_safe:
        raise ValueError(f"Episode filename is unsafe for Windows: {error}")

    # Construct the full path
    # Using forward slashes as per requirement "Linux-style forward-slash structure"
    full_path = f"{show_root}/{show_folder}/Season {season_number:02d}/S{season_number:02d}E{episode_number:02d}.mkv"

    return full_path
