"""Console handler that prints ERROR-and-above records in red."""

import ctypes
import logging
import sys
from typing import TextIO

_RED = "\033[91m"
_RESET = "\033[0m"


class ColorConsoleHandler(logging.StreamHandler[TextIO]):
    """Writes CSV log lines to stdout, coloring ERROR-and-above lines red.

    Coloring lives here (not in the Formatter) because the same Formatter
    instance is shared with the file handler, which must never receive
    ANSI escape codes.
    """

    def __init__(self, header: str) -> None:
        super().__init__(sys.stdout)
        self._header = header
        self._header_written = False
        if sys.platform == "win32":
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)

    def ensure_header(self) -> None:
        if self._header_written:
            return
        assert self.lock is not None
        with self.lock:
            if self._header_written:
                return
            self.stream.write(f"{self._header}\n")
            self.stream.flush()
            self._header_written = True

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.ensure_header()
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                msg = f"{_RED}{msg}{_RESET}"
            self.stream.write(msg + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)
