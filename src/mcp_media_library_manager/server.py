"""FastMCP server entrypoint for the mcp-media-library-manager server.

Run with::

    uv run python -m mcp_media_library_manager

or via the installed script::

    mcp-media-library-manager
"""

import argparse
import signal
import sys
from pathlib import Path
from typing import Any

import fastmcp

from mcp_media_library_manager.config import AppConfig, load_config
from mcp_media_library_manager.ingest_queue import IngestQueue
from mcp_media_library_manager.logging import Logger, make_logger
from mcp_media_library_manager.tools import (
    health_check as _health_check,
)
from mcp_media_library_manager.tools import (
    prepare_tv_episode_ingest as _prepare_tv_episode_ingest,
)

mcp = fastmcp.FastMCP("mcp-media-library-manager")

_logger: Logger | None = None
_config: AppConfig | None = None
_ingest_queue: IngestQueue | None = None


@mcp.tool()
def health_check() -> dict[str, str]:
    """Return a simple health status indicating the server is running.

    Returns:
        A dict with a single ``status`` key set to ``"ok"``.
    """
    return _health_check()


@mcp.tool()
def list_queued_ingestions() -> dict[str, list[dict[str, str | int]] | bool | str]:
    """Return the list of currently queued ingest jobs.

    Returns:
        A dict with a ``jobs`` key containing a list of job objects, each with:
        - ``job_id`` (str): Unique identifier for the job.
        - ``show_name`` (str): The TV show name.
        - ``first_air_year`` (int): The year the show first aired.
        - ``season_number`` (int): The season number.
        - ``episode_number`` (int): The episode number.
        - ``destination`` (str): The computed destination path.

        If the server is not properly initialized, returns an error dict.
    """
    if _ingest_queue is None:
        return {
            "success": False,
            "error": "Server not properly initialized",
        }

    jobs = _ingest_queue.list_jobs()
    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "show_name": job.show_name,
                "first_air_year": job.first_air_year,
                "season_number": job.season_number,
                "episode_number": job.episode_number,
                "destination": job.destination_path,
            }
            for job in jobs
        ]
    }


@mcp.tool()
def ingest_tv_episode(
    source_file_path: str,
    show_name: str,
    first_air_year: int,
    season_number: int,
    episode_number: int,
) -> dict[str, bool | str | None]:
    """Ingest a ripped TV episode into the media library.

    This tool accepts structured metadata for a TV episode and queues the file move
    for asynchronous processing. The destination path is computed server-side from
    validated inputs and cannot be controlled by the caller. The operation rejects
    unsafe inputs and refuses to overwrite existing files.

    Args:
        source_file_path: Path to the source episode file to ingest.
        show_name: The TV show name.
        first_air_year: The year the show first aired.
        season_number: The season number (1-based).
        episode_number: The episode number (1-based).

    Returns:
        A dict with keys on success:
        - ``success`` (bool): True if the ingest was queued.
        - ``queued`` (bool): True if the file move is queued.
        - ``job_id`` (str): The unique ID for this ingest job.
        - ``destination_path`` (str): The computed destination path.
        - ``message`` (str): A human-readable status message.

        On validation failure:
        - ``success`` (bool): False if validation failed.
        - ``error`` (str): An error message describing the failure reason.
    """
    if _logger is None or _config is None or _ingest_queue is None:
        return {
            "success": False,
            "error": "Server not properly initialized",
        }

    _logger.info(
        "ingest_tv_episode tool invoked",
        source_file_path=source_file_path,
        show_name=show_name,
        first_air_year=first_air_year,
        season_number=season_number,
        episode_number=episode_number,
    )

    # Prepare the ingest (validate and compute paths)
    prep = _prepare_tv_episode_ingest(
        source_file_path=source_file_path,
        show_name=show_name,
        first_air_year=first_air_year,
        season_number=season_number,
        episode_number=episode_number,
        source_roots=_config.server.source_roots,
        show_roots=_config.server.show_roots,
    )

    if not prep.success:
        _logger.warning(
            "TV episode ingest validation failed",
            error=prep.error,
        )
        return {
            "success": False,
            "error": prep.error,
        }

    # Type guard: both paths must be str at this point
    if prep.source_path is None or prep.destination_path is None:
        return {
            "success": False,
            "error": "Unexpected error: paths not computed",
        }

    # Enqueue the file move
    job_id = _ingest_queue.add_job(
        show_name=show_name,
        first_air_year=first_air_year,
        season_number=season_number,
        episode_number=episode_number,
        source_path=prep.source_path,
        destination_path=prep.destination_path,
    )

    _logger.info(
        "TV episode ingest queued",
        job_id=job_id,
        destination_path=prep.destination_path,
    )

    return {
        "success": True,
        "queued": True,
        "job_id": job_id,
        "destination_path": prep.destination_path,
        "message": f"File move queued. Job ID: {job_id}",
    }


def _handle_shutdown_signal(signum: int, frame: Any) -> None:  # noqa: ARG001
    """Handle OS shutdown signals (SIGTERM, SIGINT).

    Args:
        signum: The signal number.
        frame: The current stack frame (unused).
    """
    if _logger is None:
        sys.exit(0)

    _logger.info("Shutdown signal received", signal=signum)

    if _ingest_queue is None:
        sys.exit(0)

    _ingest_queue.shutdown()
    sys.exit(0)


def main() -> None:
    """Parse CLI arguments, load configuration, and start the MCP server."""
    parser = argparse.ArgumentParser(description="mcp-media-library-manager MCP server")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Path to config.toml (default: config.toml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    global _logger, _config, _ingest_queue
    _logger = make_logger(config.logging.level)
    _config = config
    _ingest_queue = IngestQueue(logger=_logger)
    _ingest_queue.start()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    signal.signal(signal.SIGINT, _handle_shutdown_signal)

    mcp.run(
        transport="streamable-http",
        host=config.server.host,
        port=config.server.port,
    )
