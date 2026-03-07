"""FastMCP server entrypoint for the mcp-media-library-manager server.

Run with::

    uv run python -m mcp_media_library_manager

or via the installed script::

    mcp-media-library-manager
"""

import argparse
from pathlib import Path

import fastmcp

from mcp_media_library_manager.config import AppConfig, load_config
from mcp_media_library_manager.logging import Logger, make_logger
from mcp_media_library_manager.tools import (
    health_check as _health_check,
)
from mcp_media_library_manager.tools import (
    ingest_tv_episode as _ingest_tv_episode,
)

mcp = fastmcp.FastMCP("mcp-media-library-manager")

_logger: Logger | None = None
_config: AppConfig | None = None


@mcp.tool()
def health_check() -> dict[str, str]:
    """Return a simple health status indicating the server is running.

    Returns:
        A dict with a single ``status`` key set to ``"ok"``.
    """
    return _health_check()


@mcp.tool()
def ingest_tv_episode(
    source_file_path: str,
    show_name: str,
    first_air_year: int,
    season_number: int,
    episode_number: int,
) -> dict[str, bool | str | None]:
    """Ingest a ripped TV episode into the media library.

    This tool accepts structured metadata for a TV episode and safely places it
    in the media library at a standardized location. The destination path is
    computed server-side from validated inputs and cannot be controlled by the
    caller. The operation rejects unsafe inputs and refuses to overwrite
    existing files.

    Args:
        source_file_path: Path to the source episode file to ingest.
        show_name: The TV show name.
        first_air_year: The year the show first aired.
        season_number: The season number (1-based).
        episode_number: The episode number (1-based).

    Returns:
        A dict with keys:
        - ``success`` (bool): True if the ingest succeeded, False otherwise.
        - ``destination_path`` (str|None): The computed destination path on success.
        - ``error`` (str|None): An error message describing the failure reason.
    """
    if _logger is None or _config is None:
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

    result = _ingest_tv_episode(
        source_file_path=source_file_path,
        show_name=show_name,
        first_air_year=first_air_year,
        season_number=season_number,
        episode_number=episode_number,
        source_roots=_config.server.source_roots,
        show_roots=_config.server.show_roots,
    )

    if result.success:
        _logger.info(
            "TV episode ingest succeeded",
            destination_path=result.destination_path,
        )
    else:
        _logger.warning(
            "TV episode ingest failed",
            error=result.error,
        )

    return {
        "success": result.success,
        "destination_path": result.destination_path,
        "error": result.error,
    }


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

    global _logger, _config
    _logger = make_logger(config.logging.level)
    _config = config

    mcp.run(
        transport="streamable-http",
        host=config.server.host,
        port=config.server.port,
    )
