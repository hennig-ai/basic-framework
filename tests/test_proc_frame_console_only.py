"""
Tests for proc_frame console-only mode (no config file).

Tests that proc_frame_start() works without a config_file_path,
producing structured CSV logging to stdout without file logging.
"""

import os
import re
from typing import Generator

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"

from basic_framework import proc_frame


@pytest.fixture(autouse=True)
def reset_proc_frame_state() -> Generator[None, None, None]:
    """Reset proc_frame global state before and after each test."""
    # Close existing logger if any
    if proc_frame._default_logger is not None:
        proc_frame._default_logger.close()

    proc_frame._default_logger = None
    proc_frame._initialized = False
    proc_frame._ini_config_file = None
    proc_frame._config_dir = None
    proc_frame._lock_file_handle = None
    proc_frame._lock_file_path = None

    yield

    if proc_frame._default_logger is not None:
        proc_frame._default_logger.close()

    proc_frame._default_logger = None
    proc_frame._initialized = False
    proc_frame._ini_config_file = None
    proc_frame._config_dir = None
    proc_frame._lock_file_handle = None
    proc_frame._lock_file_path = None


class TestConsoleOnlyInit:
    """Tests for proc_frame_start() without config file."""

    def test_start_without_config(self, capsys) -> None:
        """Test that proc_frame_start works without config_file_path."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        assert proc_frame._initialized is True
        assert proc_frame._default_logger is not None

    def test_no_ini_config_loaded(self) -> None:
        """Test that no INI config is loaded in console-only mode."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        assert proc_frame._ini_config_file is None

    def test_no_config_dir_set(self) -> None:
        """Test that config_dir remains None in console-only mode."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        assert proc_frame._config_dir is None

    def test_no_lock_file(self) -> None:
        """Test that no lock file is created in console-only mode."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        assert proc_frame._lock_file_handle is None
        assert proc_frame._lock_file_path is None


class TestConsoleOnlyLogging:
    """Tests for structured CSV logging to stdout."""

    def test_csv_header_printed_on_init(self, capsys) -> None:
        """Test that CSV header line is printed to stdout on init."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert lines[0] == "Timestamp;Application;Version;PID;ThreadID;ThreadName;Class;Method;Message"

    def test_log_msg_csv_format(self, capsys) -> None:
        """Test that log_msg produces CSV-formatted output on stdout."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        proc_frame.log_msg("Hello console")
        captured = capsys.readouterr()

        # CSV format: timestamp;app;version;pid;tid;thread_name;class;method;msg
        parts = captured.out.strip().split("\n")
        # Last line should be our message (first line is "Prozess gestartet.")
        log_line = parts[-1]
        fields = log_line.split(";")
        assert len(fields) >= 9
        assert fields[1] == "test_app"
        assert fields[2] == "1.0.0"
        assert "Hello console" in fields[8]

    def test_log_msg_no_fallback_tag(self, capsys) -> None:
        """Test that LOGGING_FALLBACK tag is NOT present after init."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        proc_frame.log_msg("No fallback")
        captured = capsys.readouterr()

        assert "LOGGING_FALLBACK" not in captured.out

    def test_log_msg_includes_timestamp(self, capsys) -> None:
        """Test that structured log includes proper timestamp."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        proc_frame.log_msg("Timestamp check")
        captured = capsys.readouterr()

        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", captured.out) is not None

    def test_log_msg_includes_pid(self, capsys) -> None:
        """Test that structured log includes PID."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        proc_frame.log_msg("PID check")
        captured = capsys.readouterr()

        pid = str(os.getpid())
        assert pid in captured.out


class TestConsoleOnlyNoFileLogging:
    """Tests that no log files are created in console-only mode."""

    def test_no_log_file_created(self, tmp_path) -> None:
        """Test that no log files or directories are created."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            proc_frame.proc_frame_start("test_app", "1.0.0")

            # No logs/ directory should exist
            assert not (tmp_path / "logs").exists()
        finally:
            os.chdir(original_cwd)

    def test_get_log_filename_empty(self) -> None:
        """Test that get_log_filename returns empty string."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        assert proc_frame.get_log_filename() == ""


class TestConsoleOnlyLogAndRaise:
    """Tests for log_and_raise in console-only mode."""

    def test_log_and_raise_string(self) -> None:
        """Test log_and_raise with string raises ValueError."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        with pytest.raises(ValueError, match="test error"):
            proc_frame.log_and_raise("test error")

    def test_log_and_raise_exception(self) -> None:
        """Test log_and_raise with exception preserves type."""
        proc_frame.proc_frame_start("test_app", "1.0.0")

        with pytest.raises(RuntimeError, match="runtime error"):
            proc_frame.log_and_raise(RuntimeError("runtime error"))


class TestConsoleOnlyValidation:
    """Tests that validation still works in console-only mode."""

    def test_empty_app_name_raises(self) -> None:
        """Test that empty app_name raises ValueError."""
        with pytest.raises(ValueError, match="app_name"):
            proc_frame.proc_frame_start("", "1.0.0")

    def test_empty_app_version_raises(self) -> None:
        """Test that empty app_version raises ValueError."""
        with pytest.raises(ValueError, match="app_version"):
            proc_frame.proc_frame_start("test_app", "")
