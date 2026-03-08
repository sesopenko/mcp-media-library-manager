"""MCP tool implementations for the mcp-media-library-manager server."""

import shutil
from dataclasses import dataclass
from pathlib import Path

from mcp_media_library_manager.library_paths import (
    build_tv_episode_destination_path,
    find_existing_season_folder,
    find_existing_show_folder,
    is_destination_path_inside_root,
    is_source_path_inside_roots,
)


@dataclass
class IngestResult:
    """Result of a TV episode ingest operation.

    Attributes:
        success: True if the ingest succeeded, False if it failed.
        destination_path: The computed destination path (only set on success).
        error: An error message describing why the operation failed (only set on failure).
    """

    success: bool
    destination_path: str | None = None
    error: str | None = None


@dataclass
class IngestPrepResult:
    """Result of TV episode ingest preparation (validation and path computation).

    Attributes:
        success: True if preparation succeeded, False if it failed.
        source_path: The resolved source path (only set on success).
        destination_path: The computed destination path (only set on success).
        error: An error message describing why the operation failed (only set on failure).
    """

    success: bool
    source_path: str | None = None
    destination_path: str | None = None
    error: str | None = None


def prepare_tv_episode_ingest(
    source_file_path: str | Path,
    show_name: str,
    first_air_year: int,
    season_number: int,
    episode_number: int,
    source_roots: tuple[Path, ...],
    show_roots: tuple[Path, ...],
) -> IngestPrepResult:
    """Prepare a TV episode ingest by validating inputs and computing the destination path.

    This function performs all validation and path computation for a TV episode ingest
    without actually moving the file. It returns the source and destination paths if
    validation succeeds, allowing the caller to handle the file move separately.

    Args:
        source_file_path: Path to the source episode file to ingest.
        show_name: The TV show name.
        first_air_year: The year the show first aired.
        season_number: The season number (1-based).
        episode_number: The episode number (1-based).
        source_roots: Tuple of configured source root paths.
        show_roots: Tuple of configured show root paths.

    Returns:
        An IngestPrepResult with success=True and the source/destination paths on success,
        or success=False with an error message on failure.
    """
    # Validate source path is inside configured source roots
    is_inside, error = is_source_path_inside_roots(source_file_path, source_roots)
    if not is_inside:
        return IngestPrepResult(success=False, error=error)

    # Ensure source file exists
    source = Path(source_file_path).resolve()
    if not source.exists():
        return IngestPrepResult(success=False, error=f"Source file does not exist: {source}")

    if not source.is_file():
        return IngestPrepResult(success=False, error=f"Source path is not a file: {source}")

    # Validate all metadata by building the canonical path (discard the return value)
    show_root = show_roots[0]
    try:
        build_tv_episode_destination_path(
            show_root=show_root,
            show_name=show_name,
            first_air_year=first_air_year,
            season_number=season_number,
            episode_number=episode_number,
        )
    except ValueError as e:
        return IngestPrepResult(success=False, error=f"Invalid metadata: {e}")

    # Resolve actual show folder (case-insensitive match)
    actual_show_dir = find_existing_show_folder(show_root, show_name, first_air_year)
    if actual_show_dir is None:
        # No existing match; use canonical name
        actual_show_dir = show_root / f"{show_name} ({first_air_year})"

    # Resolve actual season folder (numeric match, ignoring zero-padding)
    actual_season_dir = find_existing_season_folder(actual_show_dir, season_number)
    if actual_season_dir is None:
        # No existing match; use canonical name with zero-padding
        actual_season_dir = actual_show_dir / f"Season {season_number:02d}"

    # Build destination file path
    episode_filename = f"S{season_number:02d}E{episode_number:02d}.mkv"
    dest = actual_season_dir / episode_filename
    dest_path_str = str(dest)

    # Validate destination path is inside configured show roots
    is_inside, error = is_destination_path_inside_root(dest_path_str, show_roots)
    if not is_inside:
        return IngestPrepResult(success=False, error=error)

    # Check if destination file already exists (no overwriting)
    dest = Path(dest_path_str).resolve()
    if dest.exists():
        return IngestPrepResult(
            success=False,
            error=f"Destination file already exists: {dest}",
        )

    # Create parent directories if they don't exist
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return IngestPrepResult(success=False, error=f"Failed to create destination directories: {e}")

    return IngestPrepResult(success=True, source_path=str(source), destination_path=str(dest_path_str))


def ingest_tv_episode(
    source_file_path: str | Path,
    show_name: str,
    first_air_year: int,
    season_number: int,
    episode_number: int,
    source_roots: tuple[Path, ...],
    show_roots: tuple[Path, ...],
) -> IngestResult:
    """Ingest a ripped TV episode into the media library.

    This function accepts structured metadata and safely ingests a TV episode file
    by computing the standardized destination path, validating all inputs against
    configured roots, creating missing directories, and moving the file to its
    destination. The operation is safe by default: no overwriting, no caller-controlled
    destination paths, and explicit rejection of ambiguous inputs.

    Args:
        source_file_path: Path to the source episode file to ingest.
        show_name: The TV show name.
        first_air_year: The year the show first aired.
        season_number: The season number (1-based).
        episode_number: The episode number (1-based).
        source_roots: Tuple of configured source root paths.
        show_roots: Tuple of configured show root paths.

    Returns:
        An IngestResult with success=True and the computed destination_path on success,
        or success=False with an error message on failure.
    """
    # Prepare the ingest (validate and compute paths)
    prep = prepare_tv_episode_ingest(
        source_file_path=source_file_path,
        show_name=show_name,
        first_air_year=first_air_year,
        season_number=season_number,
        episode_number=episode_number,
        source_roots=source_roots,
        show_roots=show_roots,
    )

    if not prep.success:
        return IngestResult(success=False, error=prep.error)

    # Type guard: both paths must be str at this point
    if prep.source_path is None or prep.destination_path is None:
        return IngestResult(success=False, error="Unexpected error: paths not computed")

    # Move the file to the destination
    try:
        shutil.move(prep.source_path, prep.destination_path)
    except OSError as e:
        return IngestResult(success=False, error=f"Failed to move file to destination: {e}")

    return IngestResult(success=True, destination_path=prep.destination_path)


def health_check() -> dict[str, str]:
    """Return a simple health status indicating the server is running.

    Returns:
        A dict with a single ``status`` key set to ``"ok"``.
    """
    return {"status": "ok"}
