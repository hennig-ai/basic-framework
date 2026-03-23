"""
Unit tests for LoggingObject class.
"""

import os
import tempfile
import threading
from pathlib import Path
from typing import Generator

import pytest

# Disable beeps for all tests in this module
os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"


@pytest.fixture
def temp_log_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestLoggingObjectInit:
    """Tests for LoggingObject initialization."""

    def test_init_creates_log_file(self, temp_log_dir: Path) -> None:
        """Test that initialization creates log file."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
        )

        assert logger.log_filepath is not None
        assert os.path.exists(logger.log_filepath)
        logger.close()

    def test_init_creates_log_with_header(self, temp_log_dir: Path) -> None:
        """Test that log file contains CSV header."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
        )

        log_path = logger.log_filepath
        logger.close()

        assert log_path is not None  # Type narrowing for mypy
        with open(log_path, 'r', encoding='utf-8') as f:
            header = f.readline()

        assert "Timestamp;Application;Version;PID;ThreadID;ThreadName;Class;Method;Message" in header

    def test_init_empty_app_name_raises(self, temp_log_dir: Path) -> None:
        """Test that empty app_name raises ValueError."""
        from basic_framework.logging_object import LoggingObject

        with pytest.raises(ValueError) as exc_info:
            LoggingObject(
                app_name="",
                app_version="1.0.0",
                log_dir=str(temp_log_dir),
            )

        assert "app_name" in str(exc_info.value)

    def test_init_empty_app_version_raises(self, temp_log_dir: Path) -> None:
        """Test that empty app_version raises ValueError."""
        from basic_framework.logging_object import LoggingObject

        with pytest.raises(ValueError) as exc_info:
            LoggingObject(
                app_name="TestApp",
                app_version="",
                log_dir=str(temp_log_dir),
            )

        assert "app_version" in str(exc_info.value)

    def test_init_invalid_auto_copy_dir_raises(self, temp_log_dir: Path) -> None:
        """Test that non-existent auto_copy_dir raises ValueError."""
        from basic_framework.logging_object import LoggingObject

        with pytest.raises(ValueError) as exc_info:
            LoggingObject(
                app_name="TestApp",
                app_version="1.0.0",
                log_dir=str(temp_log_dir),
                error_log_auto_copy_dir="/nonexistent/path",
            )

        assert "error_log_auto_copy_dir" in str(exc_info.value)


class TestLoggingObjectProperties:
    """Tests for LoggingObject properties."""

    def test_app_name_property(self, temp_log_dir: Path) -> None:
        """Test app_name property."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="MyTestApp",
            app_version="2.0.0",
            log_dir=str(temp_log_dir),
        )

        assert logger.app_name == "MyTestApp"
        logger.close()

    def test_app_version_property(self, temp_log_dir: Path) -> None:
        """Test app_version property."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="3.1.4",
            log_dir=str(temp_log_dir),
        )

        assert logger.app_version == "3.1.4"
        logger.close()

    def test_log_filename_property(self, temp_log_dir: Path) -> None:
        """Test log_filename property contains app name."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
        )

        assert "TestApp" in logger.log_filename
        assert "_log_" in logger.log_filename
        logger.close()


class TestLoggingObjectLogMsg:
    """Tests for LoggingObject.log_msg()."""

    def test_log_msg_writes_to_file(self, temp_log_dir: Path) -> None:
        """Test that log_msg writes to log file."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            console_output=False,
        )

        logger.log_msg("Test message")
        log_path = logger.log_filepath
        logger.close()

        assert log_path is not None  # Type narrowing for mypy
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "Test message" in content
        assert "TestApp" in content
        assert "1.0.0" in content

    def test_log_msg_includes_thread_info(self, temp_log_dir: Path) -> None:
        """Test that log_msg includes thread information."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            console_output=False,
        )

        logger.log_msg("Thread test")
        log_path = logger.log_filepath
        logger.close()

        assert log_path is not None  # Type narrowing for mypy
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should include MainThread or similar thread name
        assert "Thread" in content or "Main" in content

    def test_log_msg_console_output_can_be_disabled(self, temp_log_dir: Path, capsys) -> None:
        """Test that console output can be disabled."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            console_output=False,
        )

        logger.log_msg("Silent message")
        logger.close()

        captured = capsys.readouterr()
        assert "Silent message" not in captured.out


class TestLoggingObjectLogAndRaise:
    """Tests for LoggingObject.log_and_raise()."""

    def test_log_and_raise_with_string_raises_value_error(self, temp_log_dir: Path) -> None:
        """Test that log_and_raise with string raises ValueError."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            console_output=False,
        )

        with pytest.raises(ValueError) as exc_info:
            logger.log_and_raise("Test error message")

        assert "Test error message" in str(exc_info.value)
        logger.close()

    def test_log_and_raise_with_exception_reraises(self, temp_log_dir: Path) -> None:
        """Test that log_and_raise with exception re-raises it."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            console_output=False,
        )

        original_exception = RuntimeError("Original error")

        with pytest.raises(RuntimeError) as exc_info:
            logger.log_and_raise(original_exception)

        assert exc_info.value is original_exception
        logger.close()

    def test_log_and_raise_logs_to_file(self, temp_log_dir: Path) -> None:
        """Test that log_and_raise writes to log file."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            console_output=False,
        )

        log_path = logger.log_filepath

        try:
            logger.log_and_raise("Error to log")
        except ValueError:
            pass

        logger.close()

        assert log_path is not None  # Type narrowing for mypy
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "Error to log" in content


class TestLoggingObjectThreadSafety:
    """Tests for thread-safe logging."""

    def test_concurrent_log_writes(self, temp_log_dir: Path) -> None:
        """Test that concurrent log writes don't interleave."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            console_output=False,
        )

        messages_per_thread = 50
        num_threads = 5

        def write_logs(thread_num: int) -> None:
            for i in range(messages_per_thread):
                logger.log_msg(f"Thread {thread_num} message {i}")

        threads = [
            threading.Thread(target=write_logs, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        log_path = logger.log_filepath
        logger.close()

        assert log_path is not None  # Type narrowing for mypy
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Header + (num_threads * messages_per_thread) messages
        expected_lines = 1 + (num_threads * messages_per_thread)
        assert len(lines) == expected_lines


class TestMultipleLoggerInstances:
    """Tests for multiple LoggingObject instances."""

    def test_separate_log_files(self, temp_log_dir: Path) -> None:
        """Test that separate instances write to separate files."""
        from basic_framework.logging_object import LoggingObject

        log_dir1 = temp_log_dir / "logs1"
        log_dir2 = temp_log_dir / "logs2"

        logger1 = LoggingObject(
            app_name="App1",
            app_version="1.0.0",
            log_dir=str(log_dir1),
            console_output=False,
        )

        logger2 = LoggingObject(
            app_name="App2",
            app_version="2.0.0",
            log_dir=str(log_dir2),
            console_output=False,
        )

        logger1.log_msg("Message from App1")
        logger2.log_msg("Message from App2")

        path1 = logger1.log_filepath
        path2 = logger2.log_filepath

        logger1.close()
        logger2.close()

        assert path1 is not None  # Type narrowing for mypy
        assert path2 is not None  # Type narrowing for mypy
        with open(path1, 'r', encoding='utf-8') as f:
            content1 = f.read()

        with open(path2, 'r', encoding='utf-8') as f:
            content2 = f.read()

        assert "App1" in content1
        assert "App2" in content2
        assert "App2" not in content1
        assert "App1" not in content2


class TestLoggingObjectClose:
    """Tests for LoggingObject.close()."""

    def test_close_sets_logfile_to_none(self, temp_log_dir: Path) -> None:
        """Test that close sets log_filepath to None."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
        )

        assert logger.log_filepath is not None
        logger.close()
        assert logger.log_filepath is None

    def test_double_close_is_safe(self, temp_log_dir: Path) -> None:
        """Test that calling close twice is safe."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
        )

        logger.close()
        # Should not raise
        logger.close()


class TestLoggingObjectErrorLogCopies:
    """Tests for error log copy functionality."""

    def test_error_log_dir_created_when_copy_on_error_enabled(self, temp_log_dir: Path) -> None:
        """Test that error log directory is created when copy_on_error is True."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            copy_on_error=True,
            error_log_dir="my_errors",
        )

        error_dir = temp_log_dir / "my_errors"
        assert error_dir.exists()
        logger.close()

    def test_no_error_log_dir_when_copy_on_error_disabled(self, temp_log_dir: Path) -> None:
        """Test that error log directory is not created when copy_on_error is False."""
        from basic_framework.logging_object import LoggingObject

        logger = LoggingObject(
            app_name="TestApp",
            app_version="1.0.0",
            log_dir=str(temp_log_dir),
            copy_on_error=False,
        )

        error_dir = temp_log_dir / "errors"
        assert not error_dir.exists()
        logger.close()
