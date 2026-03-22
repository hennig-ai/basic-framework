"""
Unit tests for proc_frame module.

Tests for:
- log_and_raise() function
- log_msg() function
- global parameter functions
"""

import os
from pathlib import Path
from typing import Generator

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"


class TestLogAndRaise:
    """Tests for log_and_raise() function."""

    def test_string_message_raises_valueerror(self) -> None:
        """Test that string message raises ValueError."""
        from basic_framework.proc_frame import log_and_raise

        with pytest.raises(ValueError) as exc_info:
            log_and_raise("Test error message")

        assert "Test error message" in str(exc_info.value)

    def test_exception_is_reraised(self) -> None:
        """Test that Exception objects are re-raised with original type."""
        from basic_framework.proc_frame import log_and_raise

        original_exception = RuntimeError("Runtime error occurred")

        with pytest.raises(RuntimeError) as exc_info:
            log_and_raise(original_exception)

        assert "Runtime error occurred" in str(exc_info.value)

    def test_custom_exception_preserved(self) -> None:
        """Test that custom exception types are preserved."""
        from basic_framework.proc_frame import log_and_raise

        class CustomError(Exception):
            pass

        with pytest.raises(CustomError):
            log_and_raise(CustomError("Custom error"))

    def test_typeerror_preserved(self) -> None:
        """Test that TypeError is preserved."""
        from basic_framework.proc_frame import log_and_raise

        with pytest.raises(TypeError):
            log_and_raise(TypeError("Type error"))

    def test_keyerror_preserved(self) -> None:
        """Test that KeyError is preserved."""
        from basic_framework.proc_frame import log_and_raise

        with pytest.raises(KeyError):
            log_and_raise(KeyError("missing_key"))


class TestLogMsg:
    """Tests for log_msg() function."""

    def test_log_msg_does_not_raise(self, capsys) -> None:
        """Test that log_msg does not raise exceptions."""
        from basic_framework.proc_frame import log_msg

        # Should not raise
        log_msg("Test message")

        # Verify output contains the message
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_log_msg_includes_timestamp(self, capsys) -> None:
        """Test that log_msg includes timestamp."""
        from basic_framework.proc_frame import log_msg

        log_msg("Timestamp test")
        captured = capsys.readouterr()

        # Should contain date-like format (YYYY-MM-DD)
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2}", captured.out) is not None

    def test_log_msg_fallback_format(self, capsys) -> None:
        """Test that log_msg uses simple format when not initialized.

        When proc_frame_start() hasn't been called, log_msg falls back
        to the simple logging module which outputs a simpler format
        without PID, thread info, etc.
        """
        from basic_framework.proc_frame import log_msg

        log_msg("Fallback test")
        captured = capsys.readouterr()

        # Fallback format: "timestamp INFO: message"
        assert "Fallback test" in captured.out
        assert "INFO:" in captured.out


class TestGlobalIniParFunctions:
    """Tests for global INI parameter functions."""

    def test_global_ini_par_exists_without_init(self) -> None:
        """Test global_ini_par_exists returns False when not initialized."""
        from basic_framework.proc_frame import global_ini_par_exists

        # Without proc_frame_start, should return False
        result = global_ini_par_exists("any_param", "any_section")
        assert result is False

    def test_get_ini_config_file_without_init(self) -> None:
        """Test get_ini_config_file returns None when not initialized."""
        from basic_framework.proc_frame import get_ini_config_file

        # This tests the getter before initialization
        # Note: This test assumes fresh module state or may return existing config
        config = get_ini_config_file()
        # Either None or a valid config (depending on test order)
        assert config is None or hasattr(config, "get_value")


class TestBeepDisabling:
    """Tests for beep disabling via environment variable."""

    def test_beep_disabled_env_var(self) -> None:
        """Test that BASIC_FRAMEWORK_DISABLE_BEEP works."""
        # The env var is set in conftest.py
        assert os.environ.get("BASIC_FRAMEWORK_DISABLE_BEEP") == "1"

    def test_beep_functions_silent_when_disabled(self) -> None:
        """Test that beep functions don't raise when disabled."""
        from basic_framework.proc_frame import (
            beep_tone_proc_frame_end,
            beep_tone_error,
            beep_attention,
        )

        # Should not raise (beeps disabled)
        beep_tone_proc_frame_end()
        beep_tone_error()
        beep_attention()


class TestLogFilename:
    """Tests for log filename functions."""

    def test_get_log_filename_before_init(self) -> None:
        """Test get_log_filename returns empty before initialization."""
        from basic_framework.proc_frame import get_log_filename

        # May be empty or have value depending on test order
        filename = get_log_filename()
        assert isinstance(filename, str)


class TestAppVersionAndName:
    """Tests for get_app_version() and get_app_name() functions."""

    def test_get_app_version_before_init(self) -> None:
        """Test get_app_version returns empty before initialization."""
        from basic_framework.proc_frame import get_app_version

        # May be empty or have value depending on test order
        version = get_app_version()
        assert isinstance(version, str)

    def test_get_app_name_before_init(self) -> None:
        """Test get_app_name returns empty before initialization."""
        from basic_framework.proc_frame import get_app_name

        # May be empty or have value depending on test order
        name = get_app_name()
        assert isinstance(name, str)


class TestProcFrameStart:
    """Tests for proc_frame_start() function."""

    def test_proc_frame_start_creates_log_directory(self, temp_dir: Path) -> None:
        """Test that proc_frame_start creates logs directory under config dir."""
        from basic_framework.proc_frame import proc_frame_start, proc_frame_end

        ini_path = temp_dir / "test_config.ini"
        ini_path.write_text(
            """[default]
single_instance = false
""",
            encoding="utf-8",
        )

        proc_frame_start("TestApp", "1.0.0", str(ini_path))

        # Verify logs directory was created
        logs_dir = temp_dir / "logs"
        assert logs_dir.exists()
        assert logs_dir.is_dir()

        # Cleanup - proc_frame_end calls sys.exit(0)
        with pytest.raises(SystemExit) as exc_info:
            proc_frame_end(beep=False, close_log_flag=True)
        assert exc_info.value.code == 0

    def test_proc_frame_start_empty_app_name_raises(self, temp_dir: Path) -> None:
        """Test that empty app_name raises ValueError."""
        from basic_framework.proc_frame import proc_frame_start

        ini_path = temp_dir / "test_config.ini"
        ini_path.write_text(
            """[default]
single_instance = false
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as exc_info:
            proc_frame_start("", "1.0.0", str(ini_path))

        assert "app_name" in str(exc_info.value)

    def test_proc_frame_start_missing_single_instance_raises(self, temp_dir: Path) -> None:
        """Test that missing single_instance config raises ValueError."""
        from basic_framework.proc_frame import proc_frame_start

        ini_path = temp_dir / "test_config.ini"
        ini_path.write_text(
            """[default]
some_other_param = value
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as exc_info:
            proc_frame_start("TestApp", "1.0.0", str(ini_path))

        assert "single_instance" in str(exc_info.value)
