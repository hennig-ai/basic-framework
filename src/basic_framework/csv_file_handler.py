"""File handler for CSV-format log output, with eager/lazy header support."""

import logging


class CsvFileHandler(logging.FileHandler):
    """Writes CSV log lines to a file, with a header written on demand.

    `ensure_header()` is idempotent and safe to call either eagerly (right
    after construction) or lazily (from `emit()`, e.g. at level=ERROR, where
    the first record might be the first error).
    """

    def __init__(self, filename: str, header: str) -> None:
        super().__init__(filename, mode="w", encoding="utf-8")
        self._header = header
        self._header_written = False

    def ensure_header(self) -> None:
        if self._header_written:
            return
        assert self.lock is not None
        with self.lock:
            if self._header_written:
                return
            assert self.stream is not None
            self.stream.write(f"{self._header}\n")
            self.stream.flush()
            self._header_written = True

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.ensure_header()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)
            return
        super().emit(record)
