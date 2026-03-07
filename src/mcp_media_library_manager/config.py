"""Configuration loading for the mcp-media-library-manager server.

Reads a TOML config file and returns typed dataclass instances for each
section. The default config path is ``config.toml`` in the working directory;
pass ``--config <path>`` at the CLI to override.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ServerConfig:
    """Network binding settings and filesystem roots for the MCP server."""

    host: str
    port: int
    source_roots: tuple[Path, ...]
    show_roots: tuple[Path, ...]


@dataclass
class LoggingConfig:
    """Logging behaviour settings."""

    level: str


@dataclass
class AppConfig:
    """Top-level application configuration, parsed from a TOML file."""

    server: ServerConfig
    logging: LoggingConfig


def _parse_roots(raw: str | list) -> tuple[Path, ...]:
    """Parse filesystem roots from TOML configuration.

    Accepts either a single string path, a comma-separated string of paths,
    or a list of strings. Normalizes all entries to Path objects and validates
    that no root is empty.

    Args:
        raw: A single path string, comma-separated paths string, or list of path strings.

    Returns:
        A tuple of normalized Path objects.

    Raises:
        ValueError: If raw is empty, contains empty path entries, or is of an invalid type.
    """
    if isinstance(raw, str):
        # Handle both single path and comma-separated paths
        if not raw.strip():
            raise ValueError("Root paths cannot be empty")
        paths = [p.strip() for p in raw.split(",")]
    elif isinstance(raw, list):
        paths = raw
    else:
        raise ValueError(f"Root paths must be a string or list, got {type(raw).__name__}")

    # Validate and normalize
    if not paths:
        raise ValueError("At least one root path must be configured")

    normalized: list[Path] = []
    for p in paths:
        if isinstance(p, str):
            p_str = p.strip()
            if not p_str:
                raise ValueError("Root paths cannot contain empty entries")
            normalized.append(Path(p_str))
        else:
            raise ValueError(f"Root paths must be strings, got {type(p).__name__}")

    return tuple(normalized)


def load_config(path: Path = Path("config.toml")) -> AppConfig:
    """Load and validate application configuration from a TOML file.

    Args:
        path: Path to the TOML configuration file.
            Defaults to ``config.toml`` in the working directory.

    Returns:
        A fully populated :class:`AppConfig` instance.

    Raises:
        FileNotFoundError: If the config file does not exist at *path*.
        KeyError: If a required section or key is missing from the file.
        ValueError: If configuration values are invalid or empty.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
    """
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    # Fail fast on missing sections
    if "server" not in raw:
        raise KeyError("Missing required [server] section in configuration")
    if "logging" not in raw:
        raise KeyError("Missing required [logging] section in configuration")

    # Validate server section keys
    server_section = raw["server"]
    required_server_keys = {"host", "port", "source_roots", "show_roots"}
    missing_keys = required_server_keys - set(server_section.keys())
    if missing_keys:
        raise KeyError(f"Missing required keys in [server] section: {', '.join(sorted(missing_keys))}")

    # Parse server config with explicit validation
    try:
        source_roots = _parse_roots(server_section["source_roots"])
        show_roots = _parse_roots(server_section["show_roots"])
    except ValueError as e:
        raise ValueError(f"Invalid configuration in [server]: {e}") from e

    server = ServerConfig(
        host=server_section["host"],
        port=int(server_section["port"]),
        source_roots=source_roots,
        show_roots=show_roots,
    )

    logging = LoggingConfig(
        level=raw["logging"]["level"],
    )
    return AppConfig(server=server, logging=logging)
