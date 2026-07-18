"""
Logging Object - Encapsulates all logging functionality.

Composes a private (non-registry) stdlib logging.Logger with CSV formatting
and console/file/error-copy handlers:
- File logging with CSV format
- Console output with optional red coloring for errors
- Error log copies with thread filtering
- Thread-safe write operations
"""

import inspect
import logging
import os
import sys
import traceback
from typing import NoReturn, Optional, Union

from .utils.basic_utils import get_format_now_stamp
from .csv_log_formatter import CSV_LOG_HEADER, AppContextFilter, CsvLogFormatter
from .csv_file_handler import CsvFileHandler
from .color_console_handler import ColorConsoleHandler
from .error_copy_handler import ErrorCopyHandler


def _caller_classname(frame_offset: int) -> str:
    """Best-effort class name of the frame `frame_offset` hops above this call.

    Not a stdlib concept - stdlib's own `stacklevel` mechanism (used for
    Method/PID/Thread/etc.) only resolves function name/line/file, not
    "what class is `self` an instance of". This walks the same call depth
    independently, since it's called from the same spot `stacklevel` is.
    """
    classinfo = "no_class"
    try:
        frame = inspect.currentframe()
        for _ in range(frame_offset):
            if frame is None:
                break
            frame = frame.f_back
        if frame is not None:
            self_obj = frame.f_locals.get("self")
            classinfo = type(self_obj).__name__ if self_obj is not None else "no_class"
    except Exception:
        classinfo = "unknown_class"
    return classinfo


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

        self._app_name: str = app_name
        self._app_version: str = app_version
        self._include_stacktrace: bool = include_stacktrace
        self._console_output: bool = console_output

        # A private, non-registry Logger - deliberately NOT logging.getLogger(),
        # which returns the same global singleton for a given name forever.
        # Two independent LoggingObject instances must never share handlers.
        self._logger = logging.Logger(
            f"basic_framework.LoggingObject.{id(self):x}",
            level=logging.ERROR if error_only else logging.DEBUG,
        )
        self._logger.propagate = False
        self._logger.addFilter(AppContextFilter(app_name, app_version))

        formatter = CsvLogFormatter()

        self._log_filename: str = ""
        self._file_handler: Optional[CsvFileHandler] = None
        self._error_handler: Optional[ErrorCopyHandler] = None
        self._error_log_dir: Optional[str] = None

        if log_dir is not None:
            self._log_filename = f"{app_name}_log_{get_format_now_stamp(True)}"
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, f"{self._log_filename}.txt")

            self._file_handler = CsvFileHandler(log_file_path, CSV_LOG_HEADER)
            self._file_handler.setFormatter(formatter)
            self._logger.addHandler(self._file_handler)

            if copy_on_error:
                self._error_log_dir = os.path.join(log_dir, error_log_dir)
                os.makedirs(self._error_log_dir, exist_ok=True)
                self._error_handler = ErrorCopyHandler(
                    app_name, self._file_handler, self._error_log_dir, error_log_auto_copy_dir
                )
                # Must be added last: it reads the file handler's output, which
                # must already be flushed for this same record before it runs.
                self._logger.addHandler(self._error_handler)

        self._console_handler = ColorConsoleHandler(CSV_LOG_HEADER)
        self._console_handler.setFormatter(formatter)
        if console_output:
            self._logger.addHandler(self._console_handler)

        if not error_only:
            if self._file_handler is not None:
                self._file_handler.ensure_header()
            if console_output:
                self._console_handler.ensure_header()

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
        return self._file_handler.baseFilename if self._file_handler is not None else None

    @property
    def console_output(self) -> bool:
        """Get whether console output is enabled."""
        return self._console_output

    @console_output.setter
    def console_output(self, value: bool) -> None:
        """Set whether console output is enabled."""
        if value and not self._console_output:
            self._logger.addHandler(self._console_handler)
        elif not value and self._console_output:
            self._logger.removeHandler(self._console_handler)
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

        Note:
            Does NOT trigger the copy-on-error mechanism, even if is_error=True -
            only log_and_raise() does that. Matches historical behavior.
        """
        level = logging.ERROR if is_error else logging.INFO
        if not self._logger.isEnabledFor(level):
            return
        classinfo = _caller_classname(caller_frame_offset + 1)
        self._logger.log(
            level, msg, stacklevel=caller_frame_offset + 1, extra={"classinfo": classinfo}
        )

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
            beep_tone_error()
            raise error
        else:
            self._log_error_string(error, caller_frame_offset + 1)
            beep_tone_error()
            raise ValueError(error)

    def close(self) -> None:
        """Close all handlers and detach them from the logger."""
        for handler in (self._console_handler, self._file_handler, self._error_handler):
            if handler is None:
                continue
            self._logger.removeHandler(handler)
            try:
                handler.close()
            except Exception as e:
                print(f"Error closing log file: {e}", file=sys.stderr)
        self._file_handler = None
        self._error_handler = None

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

        self._emit_error(complete_msg, caller_frame_offset + 1)

    def _log_error_string(self, msg: str, caller_frame_offset: int) -> None:
        """
        Log an error message string.

        Args:
            msg: The error message.
            caller_frame_offset: Frame offset for caller info.
        """
        tagged_msg: str = f"[EXCEPTION_ERROR] {msg}"
        self._emit_error(tagged_msg, caller_frame_offset + 1)

    def _emit_error(self, msg: str, caller_frame_offset: int) -> None:
        """Log an ERROR-level record flagged for copy-on-error handling."""
        if not self._logger.isEnabledFor(logging.ERROR):
            return
        classinfo = _caller_classname(caller_frame_offset + 1)
        self._logger.error(
            msg,
            stacklevel=caller_frame_offset + 1,
            extra={"classinfo": classinfo, "is_error_copy": True},
        )
