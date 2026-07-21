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
from typing import Dict, NoReturn, Optional, Union

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
        level: int = logging.DEBUG,
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
                        writes output. Not changeable at runtime. Takes
                        precedence over `level` (forces the effective level to
                        logging.ERROR regardless of what `level` is).
            level: Global threshold below which log_msg()/log_debug()/
                   log_info()/log_warning() calls are suppressed (e.g.
                   logging.WARNING silences DEBUG/INFO). Must not exceed
                   logging.ERROR - errors must always be logged, so ERROR is
                   the highest configurable threshold. Not changeable at
                   runtime.

        Raises:
            ValueError: If app_name or app_version is empty.
            ValueError: If error_log_auto_copy_dir is specified but does not exist.
            ValueError: If level is higher than logging.ERROR.
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
        if level > logging.ERROR:
            raise ValueError(
                f"level must not exceed logging.ERROR ({logging.ERROR}) - "
                f"errors must always be logged, got {level}"
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
            level=logging.ERROR if error_only else level,
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

        # Lazy header: if the effective threshold suppresses INFO (error_only,
        # or level=WARNING/ERROR), don't write a header until something is
        # actually emitted - avoids a header-only file/console when nothing
        # routine ever gets logged.
        if self._logger.isEnabledFor(logging.INFO):
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
        self,
        msg: str,
        caller_frame_offset: int = 1,
        *,
        is_error: bool = False,
        level: int = logging.INFO,
    ) -> None:
        """
        Log a message with timestamp and caller information.

        Args:
            msg: The message to log.
            caller_frame_offset: Number of frames to go back for caller info.
                Default is 1 (direct caller). Use 2 when called from a wrapper.
            is_error: If True, console output is printed in red. Equivalent to
                level=logging.ERROR; takes precedence over `level` if both are
                given, preserving pre-existing call sites unchanged.
            level: Standard library log level (logging.DEBUG/INFO/WARNING/
                ERROR/CRITICAL). Ignored if is_error=True.

        Note:
            Does NOT trigger the copy-on-error mechanism, even at ERROR level -
            only log_error()/log_and_raise() do that. Matches historical behavior.
        """
        resolved_level = logging.ERROR if is_error else level
        self._log(resolved_level, msg, caller_frame_offset + 1)

    def log_debug(self, msg: str, caller_frame_offset: int = 1) -> None:
        """Log a DEBUG-level message. Facade over log_msg(level=logging.DEBUG)."""
        self.log_msg(msg, caller_frame_offset + 1, level=logging.DEBUG)

    def log_info(self, msg: str, caller_frame_offset: int = 1) -> None:
        """Log an INFO-level message. Facade over log_msg(level=logging.INFO)."""
        self.log_msg(msg, caller_frame_offset + 1, level=logging.INFO)

    def log_warning(self, msg: str, caller_frame_offset: int = 1) -> None:
        """Log a WARNING-level message. Facade over log_msg(level=logging.WARNING)."""
        self.log_msg(msg, caller_frame_offset + 1, level=logging.WARNING)

    def log_error(self, error: Union[str, Exception], caller_frame_offset: int = 1) -> None:
        """
        Log an ERROR-level message or Exception (with optional stack trace) and
        trigger the copy-on-error archiving mechanism - WITHOUT raising.

        Args:
            error: Error message string or Exception object.
            caller_frame_offset: Number of frames to go back for caller info.

        Note:
            Shares message formatting and the archiving trigger with
            log_and_raise(); the only difference is that this does not raise.
            Does NOT beep - log_and_raise()'s beep signals flow interruption,
            which this does not cause (may be called repeatedly, e.g. in a loop).
        """
        complete_msg = self._build_error_message(error)
        self._log(logging.ERROR, complete_msg, caller_frame_offset + 1, archive=True)

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

        complete_msg = self._build_error_message(error)
        self._log(logging.ERROR, complete_msg, caller_frame_offset + 1, archive=True)
        beep_tone_error()
        if isinstance(error, Exception):
            raise error
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

    def _build_error_message(self, error: Union[str, Exception]) -> str:
        """Builds the tagged error message text, with optional stack trace for Exceptions."""
        if isinstance(error, Exception):
            exc_msg: str = str(error)
            exc_type_name: str = type(error).__name__
            complete_msg: str = f"[EXCEPTION_ERROR] [{exc_type_name}] {exc_msg}"
            if self._include_stacktrace and error.__traceback__ is not None:
                stack_trace: str = ''.join(traceback.format_exception(
                    type(error), error, error.__traceback__
                ))
                complete_msg = f"{complete_msg}\n\n{'='*60}\nStack Trace:\n{'='*60}\n{stack_trace}"
            return complete_msg
        return f"[EXCEPTION_ERROR] {error}"

    def _log(self, level: int, msg: str, caller_frame_offset: int, *, archive: bool = False) -> None:
        """Core logging primitive shared by log_msg/log_debug/log_info/log_warning/
        log_error/log_and_raise: level-gates, resolves the caller's class, emits.

        Args:
            level: Standard library log level.
            msg: Fully-formatted message text.
            caller_frame_offset: Frame offset for caller info, as seen from
                this method's own frame.
            archive: If True, flags the record so ErrorCopyHandler copies the
                log file (used only by log_error/log_and_raise).
        """
        if not self._logger.isEnabledFor(level):
            return
        classinfo = _caller_classname(caller_frame_offset + 1)
        extra: Dict[str, object] = {"classinfo": classinfo}
        if archive:
            extra["is_error_copy"] = True
        self._logger.log(level, msg, stacklevel=caller_frame_offset + 1, extra=extra)
