"""MCP tool implementations for the mcp-media-library-manager server."""

from dataclasses import dataclass
from pathlib import Path

from mcp_media_library_manager.library_paths import (
    build_tv_episode_destination_path,
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
    # Validate source path is inside configured source roots
    is_inside, error = is_source_path_inside_roots(source_file_path, source_roots)
    if not is_inside:
        return IngestResult(success=False, error=error)

    # Ensure source file exists
    source = Path(source_file_path).resolve()
    if not source.exists():
        return IngestResult(success=False, error=f"Source file does not exist: {source}")

    if not source.is_file():
        return IngestResult(success=False, error=f"Source path is not a file: {source}")

    # Try to build the destination path (validates all metadata)
    try:
        # We need to pick a show_root for the destination path
        # Use the first show_root as the target root
        show_root = show_roots[0]
        dest_path_str = build_tv_episode_destination_path(
            show_root=show_root,
            show_name=show_name,
            first_air_year=first_air_year,
            season_number=season_number,
            episode_number=episode_number,
        )
    except ValueError as e:
        return IngestResult(success=False, error=f"Invalid metadata: {e}")

    # Validate destination path is inside configured show roots
    is_inside, error = is_destination_path_inside_root(dest_path_str, show_roots)
    if not is_inside:
        return IngestResult(success=False, error=error)

    # Check if destination file already exists (no overwriting)
    dest = Path(dest_path_str).resolve()
    if dest.exists():
        return IngestResult(
            success=False,
            error=f"Destination file already exists: {dest}",
        )

    # Create parent directories if they don't exist
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return IngestResult(success=False, error=f"Failed to create destination directories: {e}")

    # Move the file to the destination
    try:
        source.replace(dest)
    except OSError as e:
        return IngestResult(success=False, error=f"Failed to move file to destination: {e}")

    return IngestResult(success=True, destination_path=str(dest_path_str))


def health_check() -> dict[str, str]:
    """Return a simple health status indicating the server is running.

    Returns:
        A dict with a single ``status`` key set to ``"ok"``.
    """
    return {"status": "ok"}
