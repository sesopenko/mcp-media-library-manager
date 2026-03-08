"""Unit tests for MCP server and tool wrappers."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from mcp_media_library_manager.config import AppConfig, LoggingConfig, ServerConfig
from mcp_media_library_manager.ingest_queue import IngestQueue
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
        """Tool returns success=True when ingest is queued."""
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
                server_module._ingest_queue = IngestQueue(logger=mock_logger)
                server_module._ingest_queue.start()

                result = server_module.ingest_tv_episode(
                    source_file_path=str(source_file),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                server_module._ingest_queue.shutdown()

                assert result["success"] is True
                assert result["queued"] is True
                assert "job_id" in result
                assert result["destination_path"] is not None
                # Verify job_id is a valid UUID
                UUID(result["job_id"])

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
                server_module._ingest_queue = IngestQueue(logger=mock_logger)
                server_module._ingest_queue.start()

                server_module.ingest_tv_episode(
                    source_file_path=str(source_file),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                server_module._ingest_queue.shutdown()

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
        """Tool logs when ingest is queued."""
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
                server_module._ingest_queue = IngestQueue(logger=mock_logger)
                server_module._ingest_queue.start()

                result = server_module.ingest_tv_episode(
                    source_file_path=str(source_file),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                server_module._ingest_queue.shutdown()

                # Verify logger.info was called for queueing with destination_path
                queued_calls = [
                    info_call
                    for info_call in mock_logger.info.call_args_list
                    if info_call[0][0] == "TV episode ingest queued"
                ]
                assert len(queued_calls) > 0
                assert queued_calls[0][1]["destination_path"] == result["destination_path"]

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
                server_module._ingest_queue = IngestQueue(logger=mock_logger)
                server_module._ingest_queue.start()

                # Try to ingest a nonexistent file
                result = server_module.ingest_tv_episode(
                    source_file_path=str(Path(src_root) / "nonexistent.mkv"),
                    show_name="Test Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                server_module._ingest_queue.shutdown()

                assert result["success"] is False
                assert result["error"] is not None

                # Verify logger.warning was called for validation failure
                failure_calls = [
                    warn_call
                    for warn_call in mock_logger.warning.call_args_list
                    if warn_call[0][0] == "TV episode ingest validation failed"
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
                    server_module._ingest_queue = IngestQueue(logger=mock_logger)
                    server_module._ingest_queue.start()

                    result = server_module.ingest_tv_episode(
                        source_file_path=str(source_file),
                        show_name="Test Show",
                        first_air_year=2020,
                        season_number=1,
                        episode_number=1,
                    )

                    server_module._ingest_queue.shutdown()

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
                server_module._ingest_queue = IngestQueue(logger=mock_logger)
                server_module._ingest_queue.start()

                result = server_module.ingest_tv_episode(
                    source_file_path=str(source_file),
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

                server_module._ingest_queue.shutdown()

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


class TestListQueuedIngestionsTool:
    """Tests for the list_queued_ingestions MCP tool."""

    def test_returns_empty_list_when_queue_empty(self) -> None:
        """list_queued_ingestions returns empty list when no jobs queued."""
        from mcp_media_library_manager import server as server_module

        mock_logger = MagicMock(spec=Logger)
        server_module._ingest_queue = IngestQueue(logger=mock_logger)

        result = server_module.list_queued_ingestions()

        assert "jobs" in result
        assert result["jobs"] == []

    def test_returns_correct_job_fields(self) -> None:
        """list_queued_ingestions returns correct fields for queued jobs."""
        from mcp_media_library_manager import server as server_module

        mock_logger = MagicMock(spec=Logger)
        queue = IngestQueue(logger=mock_logger)
        server_module._ingest_queue = queue

        job_id = queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )

        result = server_module.list_queued_ingestions()

        assert "jobs" in result
        assert len(result["jobs"]) == 1
        job = result["jobs"][0]
        assert job["job_id"] == job_id
        assert job["show_name"] == "Breaking Bad"
        assert job["first_air_year"] == 2008
        assert job["season_number"] == 1
        assert job["episode_number"] == 1
        assert job["destination"] == "/media/Breaking Bad (2008)/Season 01/S01E01.mkv"

    def test_returns_error_when_not_initialized(self) -> None:
        """list_queued_ingestions returns error when queue not initialized."""
        from mcp_media_library_manager import server as server_module

        server_module._ingest_queue = None

        result = server_module.list_queued_ingestions()

        assert result["success"] is False
        assert result["error"] == "Server not properly initialized"
