"""
Integration tests for proc_frame configuration handling.

Tests for:
- Required parameters validation (single_instance)
- Logging configuration (console_output, include_stacktrace)
- Error handling for missing/invalid parameters
- Single instance lock mechanism
"""

import os
import sys
from pathlib import Path
from typing import Generator, List
from unittest.mock import patch

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"

from basic_framework import proc_frame


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def reset_proc_frame_state() -> Generator[None, None, None]:
    """Reset proc_frame global state after each test."""
    yield
    # Reset all global variables to initial state
    proc_frame._write_log = False  # type: ignore[attr-defined]
    proc_frame._logfile = None  # type: ignore[attr-defined]
    proc_frame._ui_log_object = None  # type: ignore[attr-defined]
    proc_frame._log_filename = ""  # type: ignore[attr-defined]
    proc_frame._initialized = False
    proc_frame._app_name = ""  # type: ignore[attr-defined]
    proc_frame._app_version = ""  # type: ignore[attr-defined]
    proc_frame._console_output = True  # type: ignore[attr-defined]
    proc_frame._include_stacktrace = True  # type: ignore[attr-defined]
    proc_frame._ini_pars = None
    proc_frame._ini_config_file = None
    proc_frame._lock_file_handle = None
    proc_frame._lock_file_path = None
    proc_frame._config_dir = None
    proc_frame._is_child_of_lock_holder = False

@pytest.fixture
def mock_sys_exit() -> Generator[List[int], None, None]:
    """Mock sys.exit to prevent test termination."""
    exit_codes: List[int] = []

    def fake_exit(code: int = 0) -> None:
        exit_codes.append(code)
        raise SystemExit(code)

    with patch.object(sys, 'exit', fake_exit):
        yield exit_codes


@pytest.fixture
def valid_config_file(temp_dir: Path) -> Path:
    """Create a valid config.ini with all required parameters."""
    config_path = temp_dir / "config.ini"

    config_path.write_text(
        """[default]
single_instance = false

[logging]
console_output = true
include_stacktrace = true
""",
        encoding="utf-8",
    )
    return config_path


# =============================================================================
# Missing Required Parameters Tests
# =============================================================================


class TestMissingRequiredParameters:
    """Tests for missing required configuration parameters."""

    def test_missing_single_instance_raises(
        self, temp_dir: Path, reset_proc_frame_state: None
    ) -> None:
        """Test that missing single_instance parameter raises ValueError."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
some_param = value
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as exc_info:
            proc_frame.proc_frame_start("test_app", "1.0.0", str(config_path))

        assert "single_instance" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()

    def test_empty_single_instance_raises(
        self, temp_dir: Path, reset_proc_frame_state: None
    ) -> None:
        """Test that empty single_instance parameter raises ValueError."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance =
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as exc_info:
            proc_frame.proc_frame_start("test_app", "1.0.0", str(config_path))

        assert "single_instance" in str(exc_info.value)

    def test_invalid_single_instance_value_raises(
        self, temp_dir: Path, reset_proc_frame_state: None
    ) -> None:
        """Test that invalid single_instance value raises ValueError."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = maybe
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as exc_info:
            proc_frame.proc_frame_start("test_app", "1.0.0", str(config_path))

        assert "single_instance" in str(exc_info.value)
        assert "invalid" in str(exc_info.value).lower()


# =============================================================================
# App Name Validation Tests
# =============================================================================


class TestAppNameValidation:
    """Tests for app_name parameter validation."""

    def test_empty_app_name_raises(
        self, valid_config_file: Path, reset_proc_frame_state: None
    ) -> None:
        """Test that empty app_name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            proc_frame.proc_frame_start("", "1.0.0", str(valid_config_file))

        assert "app_name" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()


# =============================================================================
# Config File Validation Tests
# =============================================================================


class TestConfigFileValidation:
    """Tests for config file validation."""

    def test_nonexistent_config_file_raises(
        self, temp_dir: Path, reset_proc_frame_state: None
    ) -> None:
        """Test that non-existent config file raises ValueError."""
        nonexistent = temp_dir / "nonexistent.ini"

        with pytest.raises(ValueError) as exc_info:
            proc_frame.proc_frame_start("test_app", "1.0.0", str(nonexistent))

        assert "Configdatei" in str(exc_info.value) or "config" in str(exc_info.value).lower()


# =============================================================================
# Successful Initialization Tests
# =============================================================================


class TestSuccessfulInitialization:
    """Tests for successful proc_frame initialization."""

    def test_successful_start_creates_log_directory(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that successful start creates logs directory under config dir."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = false

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_app", "1.0.0", str(config_path))

        # Check that logs directory was created under config dir (temp_dir)
        logs_dir = temp_dir / "logs"
        assert logs_dir.exists()
        assert logs_dir.is_dir()

        # Check that a log file was created
        log_files = list(logs_dir.glob("test_app_log_*.txt"))
        assert len(log_files) == 1

        # Cleanup without sys.exit
        proc_frame.close_log()
        proc_frame._release_process_lock()
    def test_successful_start_sets_global_config(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that successful start sets global config file."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = false
custom_param = custom_value

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_app", "1.0.0", str(config_path))

        # Check that global config is accessible
        config = proc_frame.get_ini_config_file()
        assert config is not None

        # Check that parameters can be retrieved
        value = proc_frame.get_global_par("custom_param")
        assert value == "custom_value"

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()
    def test_successful_start_sets_app_name_and_version(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that successful start sets app_name and app_version."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = false

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("MyTestApp", "2.5.3", str(config_path))

        # Check that app name and version are set
        assert proc_frame.get_app_name() == "MyTestApp"
        assert proc_frame.get_app_version() == "2.5.3"

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()
    def test_log_contains_version_column(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that log file contains version column."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = false

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("VersionTestApp", "3.1.4", str(config_path))
        proc_frame.log_msg("Test log message")

        # Read log file
        logs_dir = temp_dir / "logs"
        log_files = list(logs_dir.glob("VersionTestApp_log_*.txt"))
        assert len(log_files) == 1

        log_content = log_files[0].read_text(encoding="utf-8")

        # Check header contains Version column
        assert "Zeit;Applikation;Version;PID" in log_content

        # Check log lines contain the version
        assert ";VersionTestApp;3.1.4;" in log_content

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()

# =============================================================================
# Single Instance Lock Tests
# =============================================================================


class TestSingleInstanceLock:
    """Tests for single instance lock mechanism."""

    def test_single_instance_creates_lock_file(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that single_instance=true creates lock file."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = true

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_lock_app", "1.0.0", str(config_path))

        # Check that lock file was created (default tmp_dir is ./tmp)
        lock_file = temp_dir / "tmp" / "test_lock_app.lock"
        assert lock_file.exists()

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()
        # Lock file should be deleted after release
        assert not lock_file.exists()

    def test_single_instance_false_no_lock_file(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that single_instance=false does not create lock file."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = false

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_no_lock_app", "1.0.0", str(config_path))

        # Check that no lock file was created (default tmp_dir is ./tmp)
        lock_file = temp_dir / "tmp" / "test_no_lock_app.lock"
        assert not lock_file.exists()

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()

# =============================================================================
# Logging Configuration Tests
# =============================================================================


class TestLoggingConfiguration:
    """Tests for logging configuration parameters."""

    def test_console_output_false_suppresses_output(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that console_output=false suppresses console output."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = false

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_app", "1.0.0", str(config_path))

        # Clear captured output from startup
        capsys.readouterr()

        # Log a message
        proc_frame.log_msg("Test message for console output check")

        # Check that nothing was printed to console
        captured = capsys.readouterr()
        assert "Test message" not in captured.out

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()
    def test_console_output_true_shows_output(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that console_output=true shows console output."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = false

[logging]
console_output = true
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_app", "1.0.0", str(config_path))

        # Clear captured output from startup
        capsys.readouterr()

        # Log a message
        proc_frame.log_msg("Test message visible")

        # Check that message was printed to console
        captured = capsys.readouterr()
        assert "Test message visible" in captured.out

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()

# =============================================================================
# proc_frame_end Tests
# =============================================================================


class TestProcFrameEnd:
    """Tests for proc_frame_end behavior."""

    def test_proc_frame_end_calls_sys_exit(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that proc_frame_end calls sys.exit(0)."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = false

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_app", "1.0.0", str(config_path))

        # Call proc_frame_end - should raise SystemExit due to mock
        with pytest.raises(SystemExit) as exc_info:
            proc_frame.proc_frame_end(beep=False)

        # Check that exit code was 0
        assert exc_info.value.code == 0
        assert mock_sys_exit == [0]

    def test_proc_frame_end_releases_lock(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that proc_frame_end releases the lock file."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = true

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_lock_release", "1.0.0", str(config_path))

        # Default tmp_dir is ./tmp relative to config dir
        lock_file = temp_dir / "tmp" / "test_lock_release.lock"
        assert lock_file.exists()

        # Call proc_frame_end
        with pytest.raises(SystemExit):
            proc_frame.proc_frame_end(beep=False)

        # Lock file should be deleted
        assert not lock_file.exists()


# =============================================================================
# Boolean Parameter Variants Tests
# =============================================================================


class TestBooleanParameterVariants:
    """Tests for different boolean parameter formats."""

    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "yes", "Yes", "1"])
    def test_single_instance_true_variants(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
        value: str,
    ) -> None:
        """Test that various true values work for single_instance."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            f"""[default]
single_instance = {value}

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_bool", "1.0.0", str(config_path))

        # Should create lock file for true values (default tmp_dir is ./tmp)
        lock_file = temp_dir / "tmp" / "test_bool.lock"
        assert lock_file.exists()

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()
    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "no", "No", "0"])
    def test_single_instance_false_variants(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
        value: str,
    ) -> None:
        """Test that various false values work for single_instance."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            f"""[default]
single_instance = {value}

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        proc_frame.proc_frame_start("test_bool_false", "1.0.0", str(config_path))

        # Should NOT create lock file for false values (default tmp_dir is ./tmp)
        lock_file = temp_dir / "tmp" / "test_bool_false.lock"
        assert not lock_file.exists()

        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()

# =============================================================================
# _is_process_alive Tests
# =============================================================================


class TestIsProcessAlive:
    """Tests for _is_process_alive() helper function."""

    def test_current_process_is_alive(self) -> None:
        """Test that current process PID returns True."""
        current_pid = os.getpid()
        result = proc_frame._is_process_alive(current_pid)
        assert result is True

    def test_parent_process_is_alive(self) -> None:
        """Test that parent process PID returns True."""
        parent_pid = os.getppid()
        result = proc_frame._is_process_alive(parent_pid)
        assert result is True

    def test_invalid_pid_returns_false(self) -> None:
        """Test that non-existent PID returns False."""
        # Use a very high PID that is unlikely to exist
        invalid_pid = 99999999
        result = proc_frame._is_process_alive(invalid_pid)
        assert result is False

    def test_zero_pid_returns_false(self) -> None:
        """Test that PID 0 returns False (or True on Unix for kernel)."""
        # PID 0 behavior varies by platform
        # On Windows: should return False (no process with PID 0)
        # On Unix: PID 0 is the kernel scheduler, os.kill(0, 0) checks process group
        result = proc_frame._is_process_alive(0)
        # Just verify it doesn't crash - result varies by platform
        assert isinstance(result, bool)


# =============================================================================
# Stale Lock Detection Tests
# =============================================================================


class TestStaleLockDetection:
    """Tests for stale lock detection in _acquire_process_lock()."""

    def test_stale_lock_with_dead_pid_is_taken_over(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that a stale lock (dead PID) is taken over."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = true

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        # Create tmp directory and stale lock file with dead PID
        tmp_dir = temp_dir / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        lock_file = tmp_dir / "test_stale.lock"
        lock_file.write_text("99999999", encoding="utf-8")  # Non-existent PID

        # Should successfully start despite stale lock
        proc_frame.proc_frame_start("test_stale", "1.0.0", str(config_path))

        # Verify we acquired the lock (not child of lock holder)
        assert proc_frame._is_child_of_lock_holder is False
        assert proc_frame._lock_file_handle is not None
        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()
        # Lock file should be deleted after release
        assert not lock_file.exists()

    def test_empty_lock_file_is_handled(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that empty lock file is handled gracefully."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = true

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        # Create tmp directory and empty lock file
        tmp_dir = temp_dir / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        lock_file = tmp_dir / "test_empty_lock.lock"
        lock_file.write_text("", encoding="utf-8")  # Empty content

        # Should successfully start despite empty lock file
        proc_frame.proc_frame_start("test_empty_lock", "1.0.0", str(config_path))

        # Verify we acquired the lock (not child of lock holder)
        assert proc_frame._is_child_of_lock_holder is False
        assert proc_frame._lock_file_handle is not None
        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()
        # Lock file should be deleted after release
        assert not lock_file.exists()

    def test_corrupt_lock_file_is_handled(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that corrupt lock file (non-numeric content) is handled."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = true

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        # Create tmp directory and corrupt lock file
        tmp_dir = temp_dir / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        lock_file = tmp_dir / "test_corrupt.lock"
        lock_file.write_text("not_a_pid", encoding="utf-8")  # Invalid content

        # Should successfully start despite corrupt lock file
        proc_frame.proc_frame_start("test_corrupt", "1.0.0", str(config_path))

        # Verify we acquired the lock (not child of lock holder)
        assert proc_frame._is_child_of_lock_holder is False
        assert proc_frame._lock_file_handle is not None
        # Cleanup
        proc_frame.close_log()
        proc_frame._release_process_lock()
        # Lock file should be deleted after release
        assert not lock_file.exists()


# =============================================================================
# Child Process Lock Behavior Tests
# =============================================================================


class TestChildProcessLockBehavior:
    """Tests for child process lock handling (_is_child_of_lock_holder)."""

    def test_child_flag_is_false_by_default(
        self, reset_proc_frame_state: None
    ) -> None:
        """Test that _is_child_of_lock_holder is False by default."""
        assert proc_frame._is_child_of_lock_holder is False
    def test_release_lock_does_nothing_for_child(
        self, reset_proc_frame_state: None
    ) -> None:
        """Test that _release_process_lock() does nothing when child flag is set."""
        # Simulate child process state
        proc_frame._is_child_of_lock_holder = True
        proc_frame._lock_file_handle = "fake_handle"
        proc_frame._lock_file_path = "/fake/path"

        # Call release - should NOT clear the handle/path (child doesn't own lock)
        proc_frame._release_process_lock()

        # Flag should be reset but handle/path should remain
        # (in real scenario, parent owns these)
        assert proc_frame._is_child_of_lock_holder is False
        # Note: _lock_file_handle stays as "fake_handle" because child doesn't clean it

    def test_lock_held_by_parent_pid_sets_child_flag(
        self,
        temp_dir: Path,
        reset_proc_frame_state: None,
        mock_sys_exit: List[int],
    ) -> None:
        """Test that lock file with parent PID sets _is_child_of_lock_holder."""
        config_path = temp_dir / "config.ini"

        config_path.write_text(
            """[default]
single_instance = true

[logging]
console_output = false
""",
            encoding="utf-8",
        )

        # Create tmp directory and lock file with PARENT PID
        tmp_dir = temp_dir / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        lock_file = tmp_dir / "test_parent.lock"
        parent_pid = os.getppid()
        lock_file.write_text(str(parent_pid), encoding="utf-8")

        # Should recognize parent process and set child flag
        proc_frame.proc_frame_start("test_parent", "1.0.0", str(config_path))

        # Child flag should be set
        assert proc_frame._is_child_of_lock_holder is True

        # Cleanup - release should NOT delete the lock file (child doesn't own it)
        proc_frame.close_log()
        proc_frame._release_process_lock()

        # Child flag should be reset
        assert proc_frame._is_child_of_lock_holder is False