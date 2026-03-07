"""Unit tests for config loading."""

import tomllib
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from mcp_media_library_manager.config import AppConfig, LoggingConfig, ServerConfig, load_config

VALID_TOML = b"""
[server]
host = "0.0.0.0"
port = 8080
source_roots = "/media/source"
show_roots = "/media/shows"

[logging]
level = "debug"
"""


def test_load_config_returns_correct_types() -> None:
    """load_config returns an AppConfig with correctly typed nested dataclasses."""
    with patch("builtins.open", mock_open(read_data=VALID_TOML)):
        config = load_config(Path("config.toml"))

    assert isinstance(config, AppConfig)
    assert isinstance(config.server, ServerConfig)
    assert isinstance(config.logging, LoggingConfig)


def test_load_config_server_values() -> None:
    """load_config correctly parses [server] section values."""
    with patch("builtins.open", mock_open(read_data=VALID_TOML)):
        config = load_config(Path("config.toml"))

    assert config.server.host == "0.0.0.0"
    assert config.server.port == 8080


def test_load_config_logging_values() -> None:
    """load_config correctly parses [logging] section values."""
    with patch("builtins.open", mock_open(read_data=VALID_TOML)):
        config = load_config(Path("config.toml"))

    assert config.logging.level == "debug"


def test_load_config_missing_file_raises() -> None:
    """load_config raises FileNotFoundError when the file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.toml"))


def test_load_config_missing_section_raises() -> None:
    """load_config raises KeyError when a required section is missing."""
    incomplete = b"""
[server]
host = "localhost"
port = 8080
"""
    with patch("builtins.open", mock_open(read_data=incomplete)):
        with pytest.raises(KeyError):
            load_config(Path("config.toml"))


def test_load_config_invalid_toml_raises() -> None:
    """load_config raises TOMLDecodeError when the file is malformed."""
    with patch("builtins.open", mock_open(read_data=b"not valid toml [[[[")):
        with pytest.raises(tomllib.TOMLDecodeError):
            load_config(Path("config.toml"))


def test_load_config_source_roots_single_path() -> None:
    """load_config parses source_roots as a single path string."""
    with patch("builtins.open", mock_open(read_data=VALID_TOML)):
        config = load_config(Path("config.toml"))

    assert config.server.source_roots == (Path("/media/source"),)
    assert isinstance(config.server.source_roots, tuple)


def test_load_config_show_roots_single_path() -> None:
    """load_config parses show_roots as a single path string."""
    with patch("builtins.open", mock_open(read_data=VALID_TOML)):
        config = load_config(Path("config.toml"))

    assert config.server.show_roots == (Path("/media/shows"),)
    assert isinstance(config.server.show_roots, tuple)


def test_load_config_source_roots_comma_separated() -> None:
    """load_config parses comma-separated source_roots into multiple Path objects."""
    toml_data = b"""
[server]
host = "0.0.0.0"
port = 8080
source_roots = "/media/source1,/media/source2,/media/source3"
show_roots = "/media/shows"

[logging]
level = "debug"
"""
    with patch("builtins.open", mock_open(read_data=toml_data)):
        config = load_config(Path("config.toml"))

    assert config.server.source_roots == (
        Path("/media/source1"),
        Path("/media/source2"),
        Path("/media/source3"),
    )


def test_load_config_show_roots_comma_separated() -> None:
    """load_config parses comma-separated show_roots into multiple Path objects."""
    toml_data = b"""
[server]
host = "0.0.0.0"
port = 8080
source_roots = "/media/source"
show_roots = "/media/shows1,/media/shows2"

[logging]
level = "debug"
"""
    with patch("builtins.open", mock_open(read_data=toml_data)):
        config = load_config(Path("config.toml"))

    assert config.server.show_roots == (
        Path("/media/shows1"),
        Path("/media/shows2"),
    )


def test_load_config_roots_whitespace_handling() -> None:
    """load_config strips whitespace from comma-separated paths."""
    toml_data = b"""
[server]
host = "0.0.0.0"
port = 8080
source_roots = " /media/source1 , /media/source2 "
show_roots = " /media/shows1 , /media/shows2 "

[logging]
level = "debug"
"""
    with patch("builtins.open", mock_open(read_data=toml_data)):
        config = load_config(Path("config.toml"))

    assert config.server.source_roots == (
        Path("/media/source1"),
        Path("/media/source2"),
    )
    assert config.server.show_roots == (
        Path("/media/shows1"),
        Path("/media/shows2"),
    )


def test_load_config_missing_source_roots_raises() -> None:
    """load_config raises KeyError when source_roots is missing."""
    toml_data = b"""
[server]
host = "0.0.0.0"
port = 8080
show_roots = "/media/shows"

[logging]
level = "debug"
"""
    with patch("builtins.open", mock_open(read_data=toml_data)):
        with pytest.raises(KeyError, match="source_roots"):
            load_config(Path("config.toml"))


def test_load_config_missing_show_roots_raises() -> None:
    """load_config raises KeyError when show_roots is missing."""
    toml_data = b"""
[server]
host = "0.0.0.0"
port = 8080
source_roots = "/media/source"

[logging]
level = "debug"
"""
    with patch("builtins.open", mock_open(read_data=toml_data)):
        with pytest.raises(KeyError, match="show_roots"):
            load_config(Path("config.toml"))


def test_load_config_empty_source_roots_raises() -> None:
    """load_config raises ValueError when source_roots is empty."""
    toml_data = b"""
[server]
host = "0.0.0.0"
port = 8080
source_roots = ""
show_roots = "/media/shows"

[logging]
level = "debug"
"""
    with patch("builtins.open", mock_open(read_data=toml_data)):
        with pytest.raises(ValueError, match="cannot be empty"):
            load_config(Path("config.toml"))


def test_load_config_empty_show_roots_raises() -> None:
    """load_config raises ValueError when show_roots is empty."""
    toml_data = b"""
[server]
host = "0.0.0.0"
port = 8080
source_roots = "/media/source"
show_roots = ""

[logging]
level = "debug"
"""
    with patch("builtins.open", mock_open(read_data=toml_data)):
        with pytest.raises(ValueError, match="cannot be empty"):
            load_config(Path("config.toml"))


def test_load_config_empty_path_entries_in_comma_separated_raises() -> None:
    """load_config raises ValueError when comma-separated paths have empty entries."""
    toml_data = b"""
[server]
host = "0.0.0.0"
port = 8080
source_roots = "/media/source1,,/media/source2"
show_roots = "/media/shows"

[logging]
level = "debug"
"""
    with patch("builtins.open", mock_open(read_data=toml_data)):
        with pytest.raises(ValueError, match="cannot contain empty entries"):
            load_config(Path("config.toml"))
