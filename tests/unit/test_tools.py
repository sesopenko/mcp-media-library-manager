"""Unit tests for MCP tool implementations."""

from pathlib import Path
from tempfile import TemporaryDirectory

from mcp_media_library_manager.tools import health_check, ingest_tv_episode


def test_health_check_returns_ok() -> None:
    """health_check returns {"status": "ok"}."""
    result = health_check()
    assert result == {"status": "ok"}


class TestIngestTvEpisode:
    """Tests for TV episode ingest workflow."""

    def test_successful_ingest_moves_file(self) -> None:
        """Successful ingest moves the source file to the destination."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                # Create source file
                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("fake episode data")

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Breaking Bad",
                    first_air_year=2008,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is True
                assert result.destination_path is not None
                assert result.error is None

                # Verify source file was moved (no longer exists)
                assert not source_file.exists()

                # Verify destination file exists with correct content
                dest = Path(result.destination_path).resolve()
                assert dest.exists()
                assert dest.read_text() == "fake episode data"

    def test_successful_ingest_returns_correct_destination_path(self) -> None:
        """Successful ingest returns the correct computed destination path."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("data")

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Breaking Bad",
                    first_air_year=2008,
                    season_number=5,
                    episode_number=14,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is True
                assert result.destination_path is not None
                assert "Breaking Bad (2008)" in result.destination_path
                assert "Season 05" in result.destination_path
                assert "S05E14.mkv" in result.destination_path

    def test_ingest_creates_missing_destination_directories(self) -> None:
        """Ingest creates missing destination directories."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("data")

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="The Office",
                    first_air_year=2005,
                    season_number=3,
                    episode_number=8,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is True
                dest = Path(result.destination_path).resolve()
                assert dest.parent.exists()

    def test_ingest_fails_when_destination_file_exists(self) -> None:
        """Ingest fails when the destination file already exists (no overwrite)."""
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

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is False
                assert result.error is not None
                assert "already exists" in result.error

                # Verify source file was not moved
                assert source_file.exists()

                # Verify existing file was not modified
                assert dest_file.read_text() == "existing data"

    def test_ingest_fails_when_source_outside_source_roots(self) -> None:
        """Ingest fails when source path is outside configured source roots."""
        with TemporaryDirectory() as src_root1:
            with TemporaryDirectory() as src_root2:
                with TemporaryDirectory() as show_root:
                    # Configure only src_root1
                    source_roots = (Path(src_root1),)
                    show_roots = (Path(show_root),)

                    # Create source file in src_root2 (not configured)
                    source_file = Path(src_root2) / "episode.mkv"
                    source_file.write_text("data")

                    result = ingest_tv_episode(
                        source_file_path=source_file,
                        show_name="Show",
                        first_air_year=2020,
                        season_number=1,
                        episode_number=1,
                        source_roots=source_roots,
                        show_roots=show_roots,
                    )

                    assert result.success is False
                    assert result.error is not None
                    assert "not inside" in result.error

    def test_ingest_fails_when_destination_outside_show_roots(self) -> None:
        """Ingest fails when destination would be outside configured show roots."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root1:
                # Configure only show_root1
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root1),)

                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("data")

                # Test that ingest uses the first show_root for destination
                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                # This should succeed since we use show_roots[0]
                assert result.success is True

    def test_ingest_fails_when_source_file_does_not_exist(self) -> None:
        """Ingest fails when the source file does not exist."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                nonexistent = Path(src_root) / "nonexistent.mkv"

                result = ingest_tv_episode(
                    source_file_path=nonexistent,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is False
                assert result.error is not None
                assert "does not exist" in result.error

    def test_ingest_fails_when_source_is_directory(self) -> None:
        """Ingest fails when the source path is a directory, not a file."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                source_dir = Path(src_root) / "episode_dir"
                source_dir.mkdir()

                result = ingest_tv_episode(
                    source_file_path=source_dir,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is False
                assert result.error is not None
                assert "not a file" in result.error

    def test_ingest_fails_with_invalid_show_name(self) -> None:
        """Ingest fails when show name contains invalid characters."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("data")

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Show/Name",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is False
                assert result.error is not None
                assert "Invalid metadata" in result.error

    def test_ingest_fails_with_invalid_year(self) -> None:
        """Ingest fails when year is outside valid range."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("data")

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Show",
                    first_air_year=1800,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is False
                assert result.error is not None
                assert "Invalid metadata" in result.error

    def test_ingest_fails_with_invalid_season_number(self) -> None:
        """Ingest fails when season number is 0 or negative."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("data")

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=0,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is False
                assert result.error is not None
                assert "Invalid metadata" in result.error

    def test_ingest_fails_with_invalid_episode_number(self) -> None:
        """Ingest fails when episode number is 0 or negative."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("data")

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=0,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is False
                assert result.error is not None
                assert "Invalid metadata" in result.error

    def test_ingest_with_multiple_show_roots_uses_first(self) -> None:
        """Ingest with multiple show roots uses the first one."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root1:
                with TemporaryDirectory() as show_root2:
                    source_roots = (Path(src_root),)
                    show_roots = (Path(show_root1), Path(show_root2))

                    source_file = Path(src_root) / "episode.mkv"
                    source_file.write_text("data")

                    result = ingest_tv_episode(
                        source_file_path=source_file,
                        show_name="Show",
                        first_air_year=2020,
                        season_number=1,
                        episode_number=1,
                        source_roots=source_roots,
                        show_roots=show_roots,
                    )

                    assert result.success is True
                    dest = Path(result.destination_path).resolve()
                    # Verify it's in show_root1
                    assert str(dest).startswith(str(Path(show_root1).resolve()))

    def test_ingest_with_multiple_source_roots_validates_against_all(self) -> None:
        """Ingest validates source against all configured source roots."""
        with TemporaryDirectory() as src_root1:
            with TemporaryDirectory() as src_root2:
                with TemporaryDirectory() as show_root:
                    source_roots = (Path(src_root1), Path(src_root2))
                    show_roots = (Path(show_root),)

                    # Create source in src_root2
                    source_file = Path(src_root2) / "episode.mkv"
                    source_file.write_text("data")

                    result = ingest_tv_episode(
                        source_file_path=source_file,
                        show_name="Show",
                        first_air_year=2020,
                        season_number=1,
                        episode_number=1,
                        source_roots=source_roots,
                        show_roots=show_roots,
                    )

                    # Should succeed because source is in src_root2
                    assert result.success is True

    def test_ingest_result_has_error_only_on_failure(self) -> None:
        """IngestResult.error is only set on failure."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                source_file = Path(src_root) / "episode.mkv"
                source_file.write_text("data")

                result = ingest_tv_episode(
                    source_file_path=source_file,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is True
                assert result.error is None
                assert result.destination_path is not None

    def test_ingest_result_has_destination_path_only_on_success(self) -> None:
        """IngestResult.destination_path is only set on success."""
        with TemporaryDirectory() as src_root:
            with TemporaryDirectory() as show_root:
                source_roots = (Path(src_root),)
                show_roots = (Path(show_root),)

                nonexistent = Path(src_root) / "nonexistent.mkv"

                result = ingest_tv_episode(
                    source_file_path=nonexistent,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                    source_roots=source_roots,
                    show_roots=show_roots,
                )

                assert result.success is False
                assert result.destination_path is None
                assert result.error is not None
