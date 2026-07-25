"""
CSV log line formatting for the stdlib-logging-backed LoggingObject.

CSV format (Level column added after Method, before Message):
Timestamp;Application;Version;PID;ThreadID;ThreadName;Class;Method;Level;Message
"""

import logging
from datetime import datetime
from typing import Optional

CSV_LOG_HEADER: str = "Timestamp;Application;Version;PID;ThreadID;ThreadName;Class;Method;Level;Message"

_CSV_FORMAT: str = (
    "%(asctime)s;%(app_name)s;%(app_version)s;%(process)d;"
    "%(thread)d;%(threadName)s;%(classinfo)s;%(funcName)s;%(levelname)s;%(message)s"
)
_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"


class CsvLogFormatter(logging.Formatter):
    """Formats a LogRecord as one semicolon-separated CSV line.

    PID/ThreadID/ThreadName/Method/Level come from stdlib's own LogRecord
    fields (Method populated via the caller-supplied `stacklevel`).
    `app_name`/`app_version` are stamped by AppContextFilter; `classinfo` is
    supplied per-call via `extra=` by LoggingObject, since "class of the
    caller" is not a stdlib LogRecord concept.
    """

    def __init__(self) -> None:
        super().__init__(fmt=_CSV_FORMAT, datefmt=_DATE_FORMAT)

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        # base Formatter.formatTime() goes through time.struct_time, which has
        # no fractional-second field - datetime.fromtimestamp() preserves the
        # microseconds the historical "%f" format relies on.
        return datetime.fromtimestamp(record.created).strftime(datefmt or self.datefmt or _DATE_FORMAT)


class AppContextFilter(logging.Filter):
    """Stamps the constant-per-instance app_name/app_version onto every record."""

    def __init__(self, app_name: str, app_version: str) -> None:
        super().__init__()
        self._app_name = app_name
        self._app_version = app_version

    def filter(self, record: logging.LogRecord) -> bool:
        record.app_name = self._app_name  # type: ignore[attr-defined]
        record.app_version = self._app_version  # type: ignore[attr-defined]
        return True
