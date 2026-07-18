"""Handler that copies the log file into a per-thread error subdirectory
whenever an error record originating from log_and_raise() is emitted.

Ports the historical copy-on-error mechanism (full copy + thread-filtered
copy + optional external mirror directory) onto the stdlib logging.Handler
interface. Only reacts to records explicitly flagged via `is_error_copy`
(set by LoggingObject only for log_and_raise() calls) - a plain
log_msg(..., is_error=True) call is colored red on the console but does not
trigger a copy, matching historical behavior.
"""

import logging
import os
import shutil
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple


class ErrorCopyHandler(logging.Handler):
    def __init__(
        self,
        app_name: str,
        file_handler: logging.FileHandler,
        error_log_dir: str,
        error_log_auto_copy_dir: Optional[str],
    ) -> None:
        super().__init__()
        self._app_name = app_name
        self._file_handler = file_handler
        self._error_log_dir = error_log_dir
        self._error_log_auto_copy_dir = error_log_auto_copy_dir
        # thread_id -> (error_subdir, full_copy_path, filtered_copy_path, last_line_count)
        self._state: Dict[int, Tuple[str, str, str, int]] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "is_error_copy", False):
            return False
        return super().filter(record)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            current_tid = record.thread
            if current_tid is None:
                return

            # Hold the FILE handler's own lock (not just this handler's) while
            # flushing+reading it, so a concurrent CsvFileHandler.emit() on
            # another thread can't be caught mid-write.
            assert self._file_handler.lock is not None
            with self._file_handler.lock:
                self._file_handler.flush()
                src_path = self._file_handler.baseFilename
                with open(src_path, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()

            current_line_count = len(all_lines)

            if current_tid in self._state:
                error_subdir, full_path, filtered_path, last_line_count = self._state[current_tid]
                if current_line_count > last_line_count:
                    new_lines = all_lines[last_line_count:]
                    with open(full_path, "a", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    self._state[current_tid] = (error_subdir, full_path, filtered_path, current_line_count)
                    self._auto_copy_error_logs(error_subdir)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pid = os.getpid()
                error_subdir = os.path.join(self._error_log_dir, timestamp)
                os.makedirs(error_subdir, exist_ok=True)

                filename_base = f"{self._app_name}_{pid}_{current_tid}"

                dst_path_full = os.path.join(error_subdir, f"{filename_base}.txt")
                shutil.copy2(src_path, dst_path_full)

                main_tid = threading.main_thread().ident
                relevant_tids = {str(main_tid), str(current_tid)}
                dst_path_filtered = os.path.join(error_subdir, f"{filename_base}_filtered.txt")
                self._write_filtered_log(all_lines, dst_path_filtered, relevant_tids)

                self._state[current_tid] = (error_subdir, dst_path_full, dst_path_filtered, current_line_count)
                self._auto_copy_error_logs(error_subdir)
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)

    def _auto_copy_error_logs(self, error_subdir: str) -> None:
        if self._error_log_auto_copy_dir is None:
            return
        subdir_name = os.path.basename(error_subdir)
        dst_subdir = os.path.join(self._error_log_auto_copy_dir, subdir_name)
        if os.path.exists(dst_subdir):
            shutil.rmtree(dst_subdir)
        shutil.copytree(error_subdir, dst_subdir)

    def _write_filtered_log(self, lines: List[str], dst_path: str, relevant_tids: Set[str]) -> None:
        if not lines:
            return
        filtered_lines: List[str] = []
        include_current_entry = False
        filtered_lines.append(lines[0])
        for line in lines[1:]:
            parts = line.split(";")
            if len(parts) >= 9:
                tid = parts[4]
                include_current_entry = tid in relevant_tids
            if include_current_entry:
                filtered_lines.append(line)
        with open(dst_path, "w", encoding="utf-8") as f:
            f.writelines(filtered_lines)
