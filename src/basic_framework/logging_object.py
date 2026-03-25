"""
Logging Object - Encapsulates all logging functionality.

Provides:
- File logging with CSV format
- Console output with optional red coloring for errors
- Error log copies with thread filtering
- Thread-safe write operations
"""

import os
import sys
import inspect
import threading
import traceback
import shutil
from datetime import datetime
from typing import Optional, Dict, Tuple, TextIO, NoReturn, Union

from .utils.basic_utils import get_format_now_stamp


CSV_LOG_HEADER: str = "Timestamp;Application;Version;PID;ThreadID;ThreadName;Class;Method;Message"


class LoggingObject:
    """
    Encapsulates logging state and operations.

    Replaces the global logging variables in proc_frame.py with
    an object-oriented approach while maintaining API compatibility.

    Attributes:
        app_name: Application name for log entries.
        app_version: Application version for log entries.
        log_filename: Log filename without path.
        log_filepath: Full path to the log file.
    """

    def __init__(
        self,
        app_name: str,
        app_version: str,
        log_dir: Optional[str] = None,
        *,
        console_output: bool = True,
        include_stacktrace: bool = True,
        copy_on_error: bool = True,
        error_log_dir: str = "errors",
        error_log_auto_copy_dir: Optional[str] = None,
        error_only: bool = False,
    ) -> None:
        """
        Initialize the LoggingObject.

        Args:
            app_name: Application name for log entries.
            app_version: Application version for log entries.
            log_dir: Directory where log files will be created.
                     If None, only console output is used (no file logging).
            console_output: Whether to output to console (default: True).
            include_stacktrace: Whether to include stacktraces (default: True).
            copy_on_error: Whether to copy logs on error (default: True).
                           Ignored when log_dir is None.
            error_log_dir: Subdirectory name for error logs (default: "errors").
                           Ignored when log_dir is None.
            error_log_auto_copy_dir: Optional auto-copy directory for error logs.
                                     Ignored when log_dir is None.
            error_only: If True, log_msg() is silenced and only log_and_raise()
                        writes output. Not changeable at runtime.

        Raises:
            ValueError: If app_name or app_version is empty.
            ValueError: If error_log_auto_copy_dir is specified but does not exist.
        """
        # Validation (CLAUDE.md: No graceful degradation)
        if not app_name:
            raise ValueError("app_name is required and cannot be empty")
        if not app_version:
            raise ValueError("app_version is required and cannot be empty")
        if error_log_auto_copy_dir and not os.path.isdir(error_log_auto_copy_dir):
            raise ValueError(
                f"error_log_auto_copy_dir '{error_log_auto_copy_dir}' "
                f"does not exist or is not a directory"
            )

        # Store configuration
        self._app_name: str = app_name
        self._app_version: str = app_version
        self._console_output: bool = console_output
        self._include_stacktrace: bool = include_stacktrace
        self._error_only: bool = error_only
        self._log_dir: Optional[str] = log_dir

        # Thread safety
        self._write_lock = threading.Lock()

        # Header tracking for lazy writing in error_only mode
        self._header_written: bool = False

        # Initialize log file (only when log_dir is provided)
        self._log_filename: str = ""
        self._logfile: Optional[TextIO] = None

        if log_dir is not None:
            self._copy_on_error: bool = copy_on_error
            self._log_filename = f"{app_name}_log_{get_format_now_stamp(True)}"
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, f"{self._log_filename}.txt")

            self._logfile = open(log_file_path, 'w', encoding='utf-8')
            if not self._error_only:
                self._logfile.write(f"{CSV_LOG_HEADER}\n")
                self._logfile.flush()
                self._header_written = True
        else:
            self._copy_on_error = False
            if self._console_output and not self._error_only:
                print(CSV_LOG_HEADER)
                self._header_written = True

        # Error log setup
        self._error_log_dir: Optional[str] = None
        self._error_log_auto_copy_dir: Optional[str] = error_log_auto_copy_dir
        self._error_log_state: Dict[int, Tuple[str, str, str, int]] = {}

        if self._copy_on_error and log_dir is not None:
            self._error_log_dir = os.path.join(log_dir, error_log_dir)
            os.makedirs(self._error_log_dir, exist_ok=True)

    @property
    def app_name(self) -> str:
        """Get the application name."""
        return self._app_name

    @property
    def app_version(self) -> str:
        """Get the application version."""
        return self._app_version

    @property
    def log_filename(self) -> str:
        """Get the log filename (without path)."""
        return self._log_filename

    @property
    def log_filepath(self) -> Optional[str]:
        """Get the full log file path."""
        if self._logfile:
            return self._logfile.name
        return None

    @property
    def console_output(self) -> bool:
        """Get whether console output is enabled."""
        return self._console_output

    @console_output.setter
    def console_output(self, value: bool) -> None:
        """Set whether console output is enabled."""
        self._console_output = value

    def log_msg(
        self, msg: str, caller_frame_offset: int = 1, *, is_error: bool = False
    ) -> None:
        """
        Log a message with timestamp and caller information.

        Args:
            msg: The message to log.
            caller_frame_offset: Number of frames to go back for caller info.
                Default is 1 (direct caller). Use 2 when called from a wrapper.
            is_error: If True, console output is printed in red.
        """
        if self._error_only and not is_error:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        pid = os.getpid()

        current_thread = threading.current_thread()
        thread_id = current_thread.ident
        thread_name = current_thread.name

        # Extract caller info
        func, classinfo = self._get_caller_info(caller_frame_offset + 1)

        formatted_msg = (
            f"{timestamp};{self._app_name};{self._app_version};"
            f"{pid};{thread_id};{thread_name};{classinfo};{func};{msg}"
        )

        # Thread-safe console + file output
        with self._write_lock:
            # Lazy header: write on first actual output in error_only mode
            if not self._header_written:
                if self._console_output:
                    print(CSV_LOG_HEADER)
                if self._logfile:
                    self._logfile.write(f"{CSV_LOG_HEADER}\n")
                self._header_written = True

            if self._console_output:
                if is_error:
                    self._print_red_unlocked(formatted_msg)
                else:
                    print(formatted_msg)

            if self._logfile:
                self._logfile.write(f"{formatted_msg}\n")
                self._logfile.flush()

    def log_and_raise(self, error: Union[str, Exception], caller_frame_offset: int = 1) -> NoReturn:
        """
        Log an error and raise an exception.

        Args:
            error: Error message string or Exception object.
            caller_frame_offset: Number of frames to go back for caller info.

        Raises:
            ValueError if string provided, original exception if Exception provided.
        """
        # Import beep function at call time to avoid circular imports
        from .proc_frame import beep_tone_error

        if isinstance(error, Exception):
            self._log_exception(error, caller_frame_offset + 1)
            self._safe_copy_log_on_error()
            beep_tone_error()
            raise error
        else:
            self._log_error_string(error, caller_frame_offset + 1)
            self._safe_copy_log_on_error()
            beep_tone_error()
            raise ValueError(error)

    def _safe_copy_log_on_error(self) -> None:
        """
        Safely copy log on error, catching any exceptions.

        This wrapper ensures that failures in the error log copy mechanism
        do not prevent the original exception from being raised.
        Errors are printed to stderr for debugging.
        """
        try:
            self._copy_log_on_error()
        except Exception as copy_error:
            print(
                f"[WARNING] Failed to copy error log: {type(copy_error).__name__}: {copy_error}",
                file=sys.stderr
            )

    def close(self) -> None:
        """Close the log file."""
        with self._write_lock:
            if self._logfile:
                try:
                    self._logfile.close()
                except Exception as e:
                    print(f"Error closing log file: {e}", file=sys.stderr)
                finally:
                    self._logfile = None

    def _get_caller_info(self, frame_offset: int) -> Tuple[str, str]:
        """
        Extract caller method and class info from call stack.

        Args:
            frame_offset: Number of frames to go back (1 = direct caller).

        Returns:
            Tuple of (function_name, class_name).
        """
        func = "unknown"
        classinfo = "no_class"

        try:
            current_frame = inspect.currentframe()
            caller_frame = current_frame

            # Navigate up the call stack
            for _ in range(frame_offset + 1):
                if caller_frame is None:
                    break
                caller_frame = caller_frame.f_back

            if caller_frame:
                func = caller_frame.f_code.co_name
                self_obj = caller_frame.f_locals.get('self')
                if self_obj:
                    classinfo = type(self_obj).__name__
                else:
                    classinfo = "no_class"
        except Exception:
            func = "unknown"
            classinfo = "unknown_class"

        return func, classinfo

    def _print_red_unlocked(self, text: str) -> None:
        """
        Print text in red color to console (NOT thread-safe, caller must hold lock).

        Args:
            text: The text to print in red.
        """
        RED = "\033[91m"
        RESET = "\033[0m"

        if sys.platform == 'win32':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)

        print(f"{RED}{text}{RESET}")

    def _log_exception(self, exception: Exception, caller_frame_offset: int) -> None:
        """
        Log an exception with stack trace.

        Args:
            exception: The exception to log.
            caller_frame_offset: Frame offset for caller info.
        """
        exc_msg: str = str(exception)
        exc_type_name: str = type(exception).__name__

        complete_msg: str = f"[EXCEPTION_ERROR] [{exc_type_name}] {exc_msg}"

        if self._include_stacktrace and exception.__traceback__ is not None:
            stack_trace: str = ''.join(traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__
            ))
            complete_msg = f"{complete_msg}\n\n{'='*60}\nStack Trace:\n{'='*60}\n{stack_trace}"

        self.log_msg(complete_msg, caller_frame_offset + 1, is_error=True)

    def _log_error_string(self, msg: str, caller_frame_offset: int) -> None:
        """
        Log an error message string.

        Args:
            msg: The error message.
            caller_frame_offset: Frame offset for caller info.
        """
        tagged_msg: str = f"[EXCEPTION_ERROR] {msg}"
        self.log_msg(tagged_msg, caller_frame_offset + 1, is_error=True)

    def _copy_log_on_error(self) -> None:
        """
        Copy current log file to error directory if copy_on_error is enabled.

        Creates a subdirectory in the error log directory with timestamp as name,
        then creates two copies of the current log file:
        1. Full copy: <appname>_<pid>_<tid>.txt
        2. Filtered copy: <appname>_<pid>_<tid>_filtered.txt
        """
        if not self._copy_on_error or self._error_log_dir is None or self._logfile is None:
            return

        current_tid = threading.current_thread().ident
        if current_tid is None:
            return

        src_path = self._logfile.name

        # Flush to ensure all data is written
        with self._write_lock:
            if self._logfile:
                self._logfile.flush()

        # Read all lines from source
        with open(src_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()

        current_line_count = len(all_lines)

        if current_tid in self._error_log_state:
            # Append only new lines to existing files
            error_subdir, full_path, filtered_path, last_line_count = self._error_log_state[current_tid]

            if current_line_count > last_line_count:
                new_lines = all_lines[last_line_count:]

                with open(full_path, 'a', encoding='utf-8') as f:
                    f.writelines(new_lines)

                self._error_log_state[current_tid] = (
                    error_subdir, full_path, filtered_path, current_line_count
                )

                self._auto_copy_error_logs(error_subdir)
        else:
            # First error for this thread
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pid = os.getpid()

            error_subdir = os.path.join(self._error_log_dir, timestamp)
            os.makedirs(error_subdir, exist_ok=True)

            filename_base = f"{self._app_name}_{pid}_{current_tid}"

            # Full copy
            dst_path_full = os.path.join(error_subdir, f"{filename_base}.txt")
            shutil.copy2(src_path, dst_path_full)

            # Filtered copy
            main_tid = threading.main_thread().ident
            relevant_tids = {str(main_tid), str(current_tid)}
            dst_path_filtered = os.path.join(error_subdir, f"{filename_base}_filtered.txt")
            self._write_filtered_log(all_lines, dst_path_filtered, relevant_tids)

            self._error_log_state[current_tid] = (
                error_subdir, dst_path_full, dst_path_filtered, current_line_count
            )

            self._auto_copy_error_logs(error_subdir)

    def _auto_copy_error_logs(self, error_subdir: str) -> None:
        """
        Copy error log subdirectory to the auto-copy directory if configured.

        Args:
            error_subdir: Path to the error log subdirectory.
        """
        if self._error_log_auto_copy_dir is None:
            return

        subdir_name = os.path.basename(error_subdir)
        dst_subdir = os.path.join(self._error_log_auto_copy_dir, subdir_name)

        if os.path.exists(dst_subdir):
            shutil.rmtree(dst_subdir)

        shutil.copytree(error_subdir, dst_subdir)

    def _write_filtered_log(
        self, lines: list[str], dst_path: str, relevant_tids: set[str]
    ) -> None:
        """
        Write a filtered copy of the log file containing only relevant threads.

        Args:
            lines: All lines from the source log file.
            dst_path: Path for the filtered output file.
            relevant_tids: Set of thread IDs (as strings) to include.
        """
        if not lines:
            return

        filtered_lines: list[str] = []
        include_current_entry = False

        # Always include header
        filtered_lines.append(lines[0])

        for line in lines[1:]:
            parts = line.split(';')

            if len(parts) >= 9:
                tid = parts[4]
                include_current_entry = tid in relevant_tids

            if include_current_entry:
                filtered_lines.append(line)

        with open(dst_path, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)
