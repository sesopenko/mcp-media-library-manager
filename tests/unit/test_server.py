"""Unit tests for MCP server and tool wrappers."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pytest

from mcp_media_library_manager.config import AppConfig, LoggingConfig, ServerConfig
from mcp_media_library_manager.logging import Logger


@pytest.fixture
def mock_logger() -> Logger:
    """Create a mock logger for testing."""
    return MagicMock(spec=Logger)


@pytest.fixture
def test_config() -> AppConfig:
    """Create a test configuration with temporary directories."""
    with TemporaryDirectory() as src_root:
        with TemporaryDirectory() as show_root:
            server = ServerConfig(
                host="localhost",
                port=8000,
                source_roots=(Path(src_root),),
                show_roots=(Path(show_root),),
            )
            logging = LoggingConfig(level="info")
            return AppConfig(server=server, logging=logging)


class TestIngestTvEpisodeTool:
    """Tests for the ingest_tv_episode MCP tool wrapper."""

    def test_tool_returns_success_on_successful_ingest(self) -> None:
        """Tool returns success=True when ingest succeeds."""
        # Import here to access module-level globals after patching
        from mcp_media_library_manager import server as server_module

        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                # Create source file
                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("fake data")

                # Set up module globals
                server_module._logger = MagicMock(spec=Logger)
                server_module._config = AppConfig(
                    server=ServerConfig(
                        host="localhost",
                        port=8000,
                        source_roots=source_roots,
                        show_roots=show_roots,
                    ),
                    logging=LoggingConfig(level="info"),
                )

                result = server_module.ingest_tv_episode(
                    source_file_path=str(source_file),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                assert result["success"] is True
                assert result["destination_path"] is not None
                assert result["error"] is None

    def test_tool_logs_invocation(self) -> None:
        """Tool logs when invoked."""
        from mcp_media_library_manager import server as server_module

        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                # Create source file
                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("fake data")

                # Set up module globals with a mock logger
                mock_logger = MagicMock(spec=Logger)
                server_module._logger = mock_logger
                server_module._config = AppConfig(
                    server=ServerConfig(
                        host="localhost",
                        port=8000,
                        source_roots=source_roots,
                        show_roots=show_roots,
                    ),
                    logging=LoggingConfig(level="info"),
                )

                server_module.ingest_tv_episode(
                    source_file_path=str(source_file),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                # Verify logger.info was called for invocation
                mock_logger.info.assert_any_call(
                    "ingest_tv_episode tool invoked",
                    source_file_path=str(source_file),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

    def test_tool_logs_success(self) -> None:
        """Tool logs success when ingest succeeds."""
        from mcp_media_library_manager import server as server_module

        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                # Create source file
                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("fake data")

                # Set up module globals with a mock logger
                mock_logger = MagicMock(spec=Logger)
                server_module._logger = mock_logger
                server_module._config = AppConfig(
                    server=ServerConfig(
                        host="localhost",
                        port=8000,
                        source_roots=source_roots,
                        show_roots=show_roots,
                    ),
                    logging=LoggingConfig(level="info"),
                )

                result = server_module.ingest_tv_episode(
                    source_file_path=str(source_file),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                # Verify logger.info was called for success with destination_path
                success_calls = [
                    call for call in mock_logger.info.call_args_list if call[0][0] == "TV episode ingest succeeded"
                ]
                assert len(success_calls) > 0
                assert success_calls[0][1]["destination_path"] == result["destination_path"]

    def test_tool_logs_failure_with_warning(self) -> None:
        """Tool logs failures with warning level."""
        from mcp_media_library_manager import server as server_module

        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                # Set up module globals with a mock logger
                mock_logger = MagicMock(spec=Logger)
                server_module._logger = mock_logger
                server_module._config = AppConfig(
                    server=ServerConfig(
                        host="localhost",
                        port=8000,
                        source_roots=source_roots,
                        show_roots=show_roots,
                    ),
                    logging=LoggingConfig(level="info"),
                )

                # Try to ingest a nonexistent file
                result = server_module.ingest_tv_episode(
                    source_file_path=str(Path(src_root) / "nonexistent.mkv"),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                assert result["success"] is False
                assert result["error"] is not None

                # Verify logger.warning was called for failure
                failure_calls = [
                    call for call in mock_logger.warning.call_args_list if call[0][0] == "TV episode ingest failed"
                ]
                assert len(failure_calls) > 0
                assert failure_calls[0][1]["error"] == result["error"]

    def test_tool_returns_error_when_source_outside_roots(self) -> None:
        """Tool returns error when source is outside configured roots."""
        from mcp_media_library_manager import server as server_module

        with TemporaryDirectory() as src_root1:
            with TemporaryDirectory() as src_root2:
                with TemporaryDirectory() as show_root:
                    # Configure only src_root1
                    source_roots = (Path(src_root1),)
                    show_roots = (Path(show_root),)

                    # Create source in src_root2 (not configured)
                    source_file = Path(src_root2) / "episode.mkv"
                    source_file.write_text("data")

                    # Set up module globals
                    server_module._logger = MagicMock(spec=Logger)
                    server_module._config = AppConfig(
                        server=ServerConfig(
                            host="localhost",
                            port=8000,
                            source_roots=source_roots,
                            show_roots=show_roots,
                        ),
                        logging=LoggingConfig(level="info"),
                    )

                    result = server_module.ingest_tv_episode(
                        source_file_path=str(source_file),
                        show_name="Test Show",
                        first_air_year=2020,
                        season_number=1,
                        episode_number=1,
                    )

                    assert result["success"] is False
                    assert result["error"] is not None
                    assert "not inside" in result["error"]

    def test_tool_returns_error_when_destination_collision(self) -> None:
        """Tool returns error when destination file already exists."""
        from mcp_media_library_manager import server as server_module

        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                # Create source file
                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("new data")

                # Pre-create destination file
                show_path = Path(show_root) / "Show (2020)" / "Season 01"
                show_path.mkdir(parents=True)
                dest_file = show_path / "S01E01.mkv"
                dest_file.write_text("existing data")

                # Set up module globals
                server_module._logger = MagicMock(spec=Logger)
                server_module._config = AppConfig(
                    server=ServerConfig(
                        host="localhost",
                        port=8000,
                        source_roots=source_roots,
                        show_roots=show_roots,
                    ),
                    logging=LoggingConfig(level="info"),
                )

                result = server_module.ingest_tv_episode(
                    source_file_path=str(source_file),
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                assert result["success"] is False
                assert result["error"] is not None
                assert "already exists" in result["error"]

    def test_tool_returns_error_when_not_initialized(self) -> None:
        """Tool returns error when server globals are not initialized."""
        from mcp_media_library_manager import server as server_module

        # Deliberately not set logger or config
        server_module._logger = None
        server_module._config = None

        result = server_module.ingest_tv_episode(
            source_file_path="/tmp/test.mkv",
            show_name="Test Show",
            first_air_year=2020,
            season_number=1,
            episode_number=1,
        )

        assert result["success"] is False
        assert result["error"] == "Server not properly initialized"
