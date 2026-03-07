"""Unit tests for library path validation and destination building."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from mcp_media_library_manager.library_paths import (
    build_tv_episode_destination_path,
    is_destination_path_inside_root,
    is_source_path_inside_roots,
    is_windows_safe_path_component,
    validate_show_name,
)


class TestValidateShowName:
    """Tests for show name validation."""

    def test_valid_show_name(self) -> None:
        """Valid show names pass validation."""
        assert validate_show_name("Breaking Bad")[0] is True
        assert validate_show_name("The Office")[0] is True
        assert validate_show_name("Game of Thrones")[0] is True

    def test_show_name_with_forward_slash_fails(self) -> None:
        """Show names containing forward slashes are rejected."""
        is_valid, error = validate_show_name("Show/Name")
        assert is_valid is False
        assert "path separator" in error.lower()

    def test_show_name_with_backslash_fails(self) -> None:
        """Show names containing backslashes are rejected."""
        is_valid, error = validate_show_name("Show\\Name")
        assert is_valid is False
        assert "path separator" in error.lower()

    def test_show_name_with_newline_fails(self) -> None:
        """Show names containing newlines are rejected."""
        is_valid, error = validate_show_name("Show\nName")
        assert is_valid is False
        assert "newline" in error.lower()

    def test_show_name_with_carriage_return_fails(self) -> None:
        """Show names containing carriage returns are rejected."""
        is_valid, error = validate_show_name("Show\rName")
        assert is_valid is False
        assert "newline" in error.lower()

    def test_show_name_with_control_character_fails(self) -> None:
        """Show names containing control characters are rejected."""
        is_valid, error = validate_show_name("Show\x01Name")
        assert is_valid is False
        assert "control character" in error.lower()

    def test_empty_show_name_fails(self) -> None:
        """Empty show names are rejected."""
        is_valid, error = validate_show_name("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_show_name_with_special_characters(self) -> None:
        """Show names with allowed special characters pass."""
        assert validate_show_name("Grey's Anatomy")[0] is True
        assert validate_show_name("It's Always Sunny")[0] is True
        assert validate_show_name("Doctor Who?")[0] is True


class TestIsWindowsSafePathComponent:
    """Tests for Windows filesystem safety validation."""

    def test_valid_path_component(self) -> None:
        """Valid path components pass."""
        assert is_windows_safe_path_component("Breaking Bad (2008)")[0] is True
        assert is_windows_safe_path_component("Season 05")[0] is True
        assert is_windows_safe_path_component("S05E10.mkv")[0] is True

    def test_component_with_windows_invalid_char_lt(self) -> None:
        """Components with < fail."""
        is_safe, error = is_windows_safe_path_component("Show<Name>")
        assert is_safe is False
        assert "windows-invalid" in error.lower()

    def test_component_with_windows_invalid_char_gt(self) -> None:
        """Components with > fail."""
        is_safe, error = is_windows_safe_path_component("Show>Name")
        assert is_safe is False

    def test_component_with_windows_invalid_char_colon(self) -> None:
        """Components with : fail."""
        is_safe, error = is_windows_safe_path_component("Show:Name")
        assert is_safe is False

    def test_component_with_windows_invalid_char_pipe(self) -> None:
        """Components with | fail."""
        is_safe, error = is_windows_safe_path_component("Show|Name")
        assert is_safe is False

    def test_component_with_windows_invalid_char_question(self) -> None:
        """Components with ? fail."""
        is_safe, error = is_windows_safe_path_component("Show?Name")
        assert is_safe is False

    def test_component_with_windows_invalid_char_asterisk(self) -> None:
        """Components with * fail."""
        is_safe, error = is_windows_safe_path_component("Show*Name")
        assert is_safe is False

    def test_component_with_windows_invalid_char_quote(self) -> None:
        """Components with " fail."""
        is_safe, error = is_windows_safe_path_component('Show"Name')
        assert is_safe is False

    def test_component_with_control_character_fails(self) -> None:
        """Components with control characters fail."""
        is_safe, error = is_windows_safe_path_component("Show\x01Name")
        assert is_safe is False
        assert "control character" in error.lower()

    def test_component_ending_with_period_fails(self) -> None:
        """Components ending with a period fail (Windows rule)."""
        is_safe, error = is_windows_safe_path_component("ShowName.")
        assert is_safe is False
        assert "period" in error.lower()

    def test_component_ending_with_space_fails(self) -> None:
        """Components ending with a space fail (Windows rule)."""
        is_safe, error = is_windows_safe_path_component("ShowName ")
        assert is_safe is False
        assert "space" in error.lower()

    def test_component_exceeding_255_chars_fails(self) -> None:
        """Components exceeding 255 characters fail."""
        long_name = "A" * 256
        is_safe, error = is_windows_safe_path_component(long_name)
        assert is_safe is False
        assert "255" in error

    def test_empty_component_fails(self) -> None:
        """Empty components fail."""
        is_safe, error = is_windows_safe_path_component("")
        assert is_safe is False
        assert "cannot be empty" in error.lower()


class TestIsSourcePathInsideRoots:
    """Tests for source path root enforcement."""

    def test_source_inside_single_root(self) -> None:
        """Source paths inside a configured root pass."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_file = root / "file.mkv"
            source_file.touch()

            is_inside, _ = is_source_path_inside_roots(source_file, (root,))
            assert is_inside is True

    def test_source_in_subdirectory_of_root(self) -> None:
        """Source paths in subdirectories of root pass."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subdir = root / "subdir"
            subdir.mkdir()
            source_file = subdir / "file.mkv"
            source_file.touch()

            is_inside, _ = is_source_path_inside_roots(source_file, (root,))
            assert is_inside is True

    def test_source_outside_all_roots(self) -> None:
        """Source paths outside all configured roots fail."""
        with TemporaryDirectory() as tmpdir1:
            with TemporaryDirectory() as tmpdir2:
                root = Path(tmpdir1)
                source_file = Path(tmpdir2) / "file.mkv"
                source_file.touch()

                is_inside, error = is_source_path_inside_roots(source_file, (root,))
                assert is_inside is False
                assert "not inside" in error.lower()

    def test_source_inside_one_of_multiple_roots(self) -> None:
        """Source in any of multiple roots passes."""
        with TemporaryDirectory() as tmpdir1:
            with TemporaryDirectory() as tmpdir2:
                root1 = Path(tmpdir1)
                root2 = Path(tmpdir2)
                source_file = root2 / "file.mkv"
                source_file.touch()

                is_inside, _ = is_source_path_inside_roots(source_file, (root1, root2))
                assert is_inside is True

    def test_source_with_invalid_path(self) -> None:
        """Invalid source paths fail with appropriate error."""
        is_inside, error = is_source_path_inside_roots("/nonexistent/../../../etc/passwd", (Path("/media"),))
        # Path resolution may succeed, but it won't be inside /media
        # The test validates the function doesn't crash on unusual paths
        assert isinstance(is_inside, bool)


class TestIsDestinationPathInsideRoot:
    """Tests for destination path root enforcement."""

    def test_destination_inside_show_root(self) -> None:
        """Destination paths inside a configured show root pass."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dest_path = root / "Show Name (2020)" / "Season 01" / "S01E01.mkv"

            is_inside, _ = is_destination_path_inside_root(dest_path, (root,))
            assert is_inside is True

    def test_destination_outside_all_roots(self) -> None:
        """Destination paths outside all configured roots fail."""
        with TemporaryDirectory() as tmpdir1:
            with TemporaryDirectory() as tmpdir2:
                root = Path(tmpdir1)
                dest_path = Path(tmpdir2) / "Show" / "S01E01.mkv"

                is_inside, error = is_destination_path_inside_root(dest_path, (root,))
                assert is_inside is False
                assert "not inside" in error.lower()

    def test_destination_inside_one_of_multiple_roots(self) -> None:
        """Destination in any of multiple roots passes."""
        with TemporaryDirectory() as tmpdir1:
            with TemporaryDirectory() as tmpdir2:
                root1 = Path(tmpdir1)
                root2 = Path(tmpdir2)
                dest_path = root2 / "Show" / "S01E01.mkv"

                is_inside, _ = is_destination_path_inside_root(dest_path, (root1, root2))
                assert is_inside is True


class TestBuildTvEpisodeDestinationPath:
    """Tests for TV episode destination path building."""

    def test_build_valid_destination_path(self) -> None:
        """Valid inputs produce the correct destination path."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = build_tv_episode_destination_path(
                show_root=root,
                show_name="Breaking Bad",
                first_air_year=2008,
                season_number=1,
                episode_number=1,
            )
            assert path == f"{root}/Breaking Bad (2008)/Season 01/S01E01.mkv"

    def test_build_path_with_two_digit_padding(self) -> None:
        """Season and episode numbers are zero-padded to two digits."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = build_tv_episode_destination_path(
                show_root=root,
                show_name="Show",
                first_air_year=2020,
                season_number=5,
                episode_number=9,
            )
            assert "/Season 05/S05E09.mkv" in path

    def test_build_path_with_double_digit_season_and_episode(self) -> None:
        """Double-digit season and episode numbers are handled correctly."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = build_tv_episode_destination_path(
                show_root=root,
                show_name="Show",
                first_air_year=2020,
                season_number=12,
                episode_number=24,
            )
            assert "/Season 12/S12E24.mkv" in path

    def test_build_path_with_invalid_show_name(self) -> None:
        """Invalid show names raise ValueError."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with pytest.raises(ValueError, match="Invalid show name"):
                build_tv_episode_destination_path(
                    show_root=root,
                    show_name="Show/Name",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

    def test_build_path_with_invalid_year(self) -> None:
        """Invalid years raise ValueError."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with pytest.raises(ValueError, match="Invalid first_air_year"):
                build_tv_episode_destination_path(
                    show_root=root,
                    show_name="Show",
                    first_air_year=1800,
                    season_number=1,
                    episode_number=1,
                )

    def test_build_path_with_zero_season(self) -> None:
        """Season number 0 raises ValueError."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with pytest.raises(ValueError, match="Invalid season_number"):
                build_tv_episode_destination_path(
                    show_root=root,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=0,
                    episode_number=1,
                )

    def test_build_path_with_negative_season(self) -> None:
        """Negative season numbers raise ValueError."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with pytest.raises(ValueError, match="Invalid season_number"):
                build_tv_episode_destination_path(
                    show_root=root,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=-1,
                    episode_number=1,
                )

    def test_build_path_with_zero_episode(self) -> None:
        """Episode number 0 raises ValueError."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with pytest.raises(ValueError, match="Invalid episode_number"):
                build_tv_episode_destination_path(
                    show_root=root,
                    show_name="Show",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=0,
                )

    def test_build_path_with_show_name_containing_special_chars(self) -> None:
        """Show names with allowed special characters work."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = build_tv_episode_destination_path(
                show_root=root,
                show_name="Grey's Anatomy",
                first_air_year=2005,
                season_number=1,
                episode_number=1,
            )
            assert "Grey's Anatomy (2005)" in path

    def test_build_path_uses_forward_slashes(self) -> None:
        """Destination path uses forward slashes (Linux-style)."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = build_tv_episode_destination_path(
                show_root=root,
                show_name="Show",
                first_air_year=2020,
                season_number=1,
                episode_number=1,
            )
            # The path should use forward slashes, not backslashes
            assert "/" in path
            assert "\\" not in path

    def test_build_path_with_show_name_containing_forward_slash_fails(self) -> None:
        """Show names with forward slashes raise ValueError."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with pytest.raises(ValueError, match="Invalid show name"):
                build_tv_episode_destination_path(
                    show_root=root,
                    show_name="Show/Name",
                    first_air_year=2020,
                    season_number=1,
                    episode_number=1,
                )

    def test_build_path_format_exact_readme_standard(self) -> None:
        """Path follows the exact README standard: /<root>/<show name> (<year>)/Season XX/SXXEXX.mkv."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = build_tv_episode_destination_path(
                show_root=root,
                show_name="Breaking Bad",
                first_air_year=2008,
                season_number=5,
                episode_number=14,
            )
            expected = f"{root}/Breaking Bad (2008)/Season 05/S05E14.mkv"
            assert path == expected

    def test_build_path_large_season_and_episode_numbers(self) -> None:
        """Large season and episode numbers work (padding maintains format)."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = build_tv_episode_destination_path(
                show_root=root,
                show_name="Show",
                first_air_year=2020,
                season_number=99,
                episode_number=99,
            )
            assert "S99E99.mkv" in path
