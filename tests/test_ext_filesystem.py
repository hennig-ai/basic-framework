"""
Unit tests for ext_filesystem module.

Tests for:
- file_exists()
- directory_exists()
- file_must_exist()
- directory_must_exist()
- remember_replacement() / replace_path()
- ext_file_copy()
- ext_file_delete()
"""

import os
from pathlib import Path

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"

from basic_framework.ext_filesystem import (
    file_exists,
    directory_exists,
    file_must_exist,
    directory_must_exist,
    remember_replacement,
    replace_path,
    ext_file_copy,
    ext_file_delete,
    get_files_in_directory,
    file_last_modified,
    ext_get_folder,
    C_DIR_SEPARATOR,
)


# =============================================================================
# file_exists Tests
# =============================================================================


class TestFileExists:
    """Tests for file_exists() function."""

    def test_existing_file_returns_true(self, temp_dir: Path) -> None:
        """Test that existing file returns True."""
        test_file = temp_dir / "existing.txt"
        test_file.write_text("content")
        assert file_exists(str(test_file)) is True

    def test_nonexistent_file_returns_false(self, temp_dir: Path) -> None:
        """Test that non-existent file returns False."""
        nonexistent = temp_dir / "nonexistent.txt"
        assert file_exists(str(nonexistent)) is False

    def test_directory_returns_false(self, temp_dir: Path) -> None:
        """Test that directory path returns False for file_exists."""
        assert file_exists(str(temp_dir)) is False

    def test_hyperlink_returns_false(self) -> None:
        """Test that HTTP URLs return False."""
        assert file_exists("http://example.com/file.txt") is False
        assert file_exists("https://example.com/file.txt") is False


# =============================================================================
# directory_exists Tests
# =============================================================================


class TestDirectoryExists:
    """Tests for directory_exists() function."""

    def test_existing_directory_returns_true(self, temp_dir: Path) -> None:
        """Test that existing directory returns True."""
        assert directory_exists(str(temp_dir)) is True

    def test_nonexistent_directory_returns_false(self, temp_dir: Path) -> None:
        """Test that non-existent directory returns False."""
        nonexistent = temp_dir / "nonexistent_dir"
        assert directory_exists(str(nonexistent)) is False

    def test_file_returns_false(self, temp_dir: Path) -> None:
        """Test that file path returns False for directory_exists."""
        test_file = temp_dir / "file.txt"
        test_file.write_text("content")
        assert directory_exists(str(test_file)) is False

    def test_hyperlink_returns_false(self) -> None:
        """Test that HTTP URLs return False."""
        assert directory_exists("http://example.com/dir") is False


# =============================================================================
# file_must_exist Tests
# =============================================================================


class TestFileMustExist:
    """Tests for file_must_exist() function."""

    def test_existing_file_no_raise(self, temp_dir: Path) -> None:
        """Test that existing file does not raise."""
        test_file = temp_dir / "existing.txt"
        test_file.write_text("content")
        # Should not raise
        file_must_exist(str(test_file))

    def test_nonexistent_file_raises(self, temp_dir: Path) -> None:
        """Test that non-existent file raises ValueError."""
        nonexistent = temp_dir / "nonexistent.txt"
        with pytest.raises(ValueError) as exc_info:
            file_must_exist(str(nonexistent))
        assert "MustExist" in str(exc_info.value)
        assert "nicht gefunden" in str(exc_info.value)

    def test_hyperlink_skipped(self) -> None:
        """Test that HTTP URLs are skipped (no validation)."""
        # Should not raise for hyperlinks
        file_must_exist("http://example.com/file.txt")


# =============================================================================
# directory_must_exist Tests
# =============================================================================


class TestDirectoryMustExist:
    """Tests for directory_must_exist() function."""

    def test_existing_directory_no_raise(self, temp_dir: Path) -> None:
        """Test that existing directory does not raise."""
        # Should not raise
        directory_must_exist(str(temp_dir))

    def test_nonexistent_directory_raises(self, temp_dir: Path) -> None:
        """Test that non-existent directory raises ValueError."""
        nonexistent = temp_dir / "nonexistent_dir"
        with pytest.raises(ValueError) as exc_info:
            directory_must_exist(str(nonexistent))
        assert "MustExist" in str(exc_info.value)
        assert "nicht gefunden" in str(exc_info.value)

    def test_hyperlink_skipped(self) -> None:
        """Test that HTTP URLs are skipped."""
        # Should not raise for hyperlinks
        directory_must_exist("https://example.com/dir")


# =============================================================================
# Path Replacement Tests
# =============================================================================


class TestPathReplacement:
    """Tests for remember_replacement() and replace_path() functions."""

    def test_replace_path_without_replacement(self) -> None:
        """Test replace_path returns original when no replacement set."""
        # Reset any previous replacement
        from basic_framework import ext_filesystem
        ext_filesystem._replace_this = ""
        ext_filesystem._replace_by = ""

        path = "C:\\test\\file.txt"
        assert replace_path(path) == path

    def test_remember_and_replace(self) -> None:
        """Test remember_replacement and replace_path work together."""
        remember_replacement("http://server/share=C:\\local\\share")

        # Path that matches
        result = replace_path("http://server/share/subdir/file.txt")
        assert result == "C:\\local\\share/subdir/file.txt"

        # Path that doesn't match
        result2 = replace_path("C:\\other\\path.txt")
        assert result2 == "C:\\other\\path.txt"

    def test_remember_replacement_invalid_format_raises(self) -> None:
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            remember_replacement("invalid_no_equals")

    def test_remember_replacement_non_http_raises(self) -> None:
        """Test that non-HTTP source raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            remember_replacement("ftp://server=C:\\local")
        assert "Unzulässiges Replacement" in str(exc_info.value)


# =============================================================================
# ext_file_copy Tests
# =============================================================================


class TestExtFileCopy:
    """Tests for ext_file_copy() function."""

    def test_copy_file_success(self, temp_dir: Path) -> None:
        """Test successful file copy."""
        source = temp_dir / "source.txt"
        source.write_text("test content")
        target = temp_dir / "target.txt"

        ext_file_copy(str(source), str(target))

        assert target.exists()
        assert target.read_text() == "test content"

    def test_copy_nonexistent_source_raises(self, temp_dir: Path) -> None:
        """Test that copying non-existent source raises."""
        source = temp_dir / "nonexistent.txt"
        target = temp_dir / "target.txt"

        with pytest.raises(ValueError) as exc_info:
            ext_file_copy(str(source), str(target))
        assert "existiert nicht" in str(exc_info.value)

    def test_copy_existing_target_no_overwrite_raises(self, temp_dir: Path) -> None:
        """Test that existing target without overwrite raises."""
        source = temp_dir / "source.txt"
        source.write_text("source content")
        target = temp_dir / "target.txt"
        target.write_text("existing content")

        with pytest.raises(ValueError) as exc_info:
            ext_file_copy(str(source), str(target), overwrite=False)
        assert "existiert schon" in str(exc_info.value)

    def test_copy_with_overwrite(self, temp_dir: Path) -> None:
        """Test copy with overwrite=True succeeds."""
        source = temp_dir / "source.txt"
        source.write_text("new content")
        target = temp_dir / "target.txt"
        target.write_text("old content")

        ext_file_copy(str(source), str(target), overwrite=True)

        assert target.read_text() == "new content"

    def test_copy_to_nonexistent_directory_raises(self, temp_dir: Path) -> None:
        """Test that copying to non-existent directory raises."""
        source = temp_dir / "source.txt"
        source.write_text("content")
        target = temp_dir / "nonexistent_dir" / "target.txt"

        with pytest.raises(ValueError) as exc_info:
            ext_file_copy(str(source), str(target))
        assert "existiert nicht" in str(exc_info.value)


# =============================================================================
# ext_file_delete Tests
# =============================================================================


class TestExtFileDelete:
    """Tests for ext_file_delete() function."""

    def test_delete_existing_file(self, temp_dir: Path) -> None:
        """Test deleting an existing file."""
        test_file = temp_dir / "to_delete.txt"
        test_file.write_text("content")

        ext_file_delete(str(test_file))

        assert not test_file.exists()

    def test_delete_nonexistent_file_raises(self, temp_dir: Path) -> None:
        """Test that deleting non-existent file raises."""
        nonexistent = temp_dir / "nonexistent.txt"

        with pytest.raises(ValueError) as exc_info:
            ext_file_delete(str(nonexistent))
        assert "nicht gefunden" in str(exc_info.value)


# =============================================================================
# get_files_in_directory Tests
# =============================================================================


class TestGetFilesInDirectory:
    """Tests for get_files_in_directory() function."""

    def test_get_files_returns_dict(self, temp_dir: Path) -> None:
        """Test that function returns dictionary of files."""
        # Create test files
        (temp_dir / "file1.txt").write_text("1")
        (temp_dir / "file2.txt").write_text("2")

        result = get_files_in_directory(str(temp_dir))

        assert isinstance(result, dict)
        assert len(result) == 2

    def test_get_files_excludes_directories(self, temp_dir: Path) -> None:
        """Test that subdirectories are excluded."""
        (temp_dir / "file.txt").write_text("content")
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        result = get_files_in_directory(str(temp_dir))

        assert len(result) == 1
        for path in result.keys():
            assert "subdir" not in path

    def test_get_files_nonexistent_dir_raises(self, temp_dir: Path) -> None:
        """Test that non-existent directory raises."""
        nonexistent = temp_dir / "nonexistent_dir"

        with pytest.raises(ValueError):
            get_files_in_directory(str(nonexistent))


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_dir_separator_constant(self) -> None:
        """Test C_DIR_SEPARATOR constant."""
        assert C_DIR_SEPARATOR == "\\"


# =============================================================================
# file_last_modified Tests
# =============================================================================


class TestFileLastModified:
    """Tests for file_last_modified() function."""

    def test_returns_datetime_for_existing_file(self, temp_dir: Path) -> None:
        """Test that file_last_modified returns datetime for existing file."""
        from datetime import datetime

        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        result = file_last_modified(str(test_file))

        assert result is not None
        assert isinstance(result, datetime)

    def test_returns_recent_datetime(self, temp_dir: Path) -> None:
        """Test that returned datetime is recent (within last minute)."""
        from datetime import datetime, timedelta

        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        result = file_last_modified(str(test_file))
        now = datetime.now()

        assert result is not None
        # File should be modified within last minute
        assert (now - result) < timedelta(minutes=1)

    def test_nonexistent_file_raises(self, temp_dir: Path) -> None:
        """Test that non-existent file raises ValueError."""
        nonexistent = temp_dir / "nonexistent.txt"

        with pytest.raises(ValueError) as exc_info:
            file_last_modified(str(nonexistent))
        assert "nicht gefunden" in str(exc_info.value)


# =============================================================================
# ext_get_folder Tests
# =============================================================================


class TestExtGetFolder:
    """Tests for ext_get_folder() function."""

    def test_returns_path_for_existing_directory(self, temp_dir: Path) -> None:
        """Test that ext_get_folder returns Path for existing directory."""
        result = ext_get_folder(str(temp_dir))

        assert result is not None
        assert isinstance(result, Path)
        assert result == temp_dir

    def test_nonexistent_directory_raises(self, temp_dir: Path) -> None:
        """Test that non-existent directory raises ValueError."""
        nonexistent = temp_dir / "nonexistent_dir"

        with pytest.raises(ValueError) as exc_info:
            ext_get_folder(str(nonexistent))
        assert "existiert nicht" in str(exc_info.value)

    def test_file_path_raises(self, temp_dir: Path) -> None:
        """Test that file path (not directory) raises ValueError."""
        test_file = temp_dir / "file.txt"
        test_file.write_text("content")

        with pytest.raises(ValueError) as exc_info:
            ext_get_folder(str(test_file))
        assert "existiert nicht" in str(exc_info.value)
