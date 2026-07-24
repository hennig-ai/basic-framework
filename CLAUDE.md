# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Basic Framework** — standalone Python package for data processing, file handling, configuration management, and structured logging. Extracted from the Krefeld Prototype project. No external runtime dependencies (pure Python Standard Library). Optional: `pyodbc` for MS Access (`pip install basic-framework[msaccess]`).

## Development Commands

```bash
pip install -e ".[dev]"             # Dev install (editable + pytest, pyright)
python -m pytest tests/             # Run all tests
python -m pytest tests/test_proc_frame.py           # Run single test file
python -m pytest tests/test_proc_frame.py::test_name -v  # Run single test
pyright src/basic_framework         # Type check (strict mode)
python -m build                     # Build package
```

Pyright runs in `strict` mode (`pyproject.toml`). CI tests against Python 3.10-3.13.

**Release workflow** — two git remotes: `origin` = `basic-framework-private` (development), `public` = `basic-framework` (published mirror). On push to `main` of the private repo, CI auto-bumps the patch version in `pyproject.toml` and commits it as `Bump patch version [skip ci]`. Do not hand-edit `version` for a patch release; bump `major`/`minor` manually only when intended.

## Architecture

```
Application Code
    ↓
proc_frame (process lifecycle & logging)  ← module-level singletons
    ↓
ini_config_file (hierarchical INI config with parent_section inheritance)
    ↓
conditions + container_utils (data filtering & container/iterator pattern)
    ↓
ext_filesystem + utils (file ops, string & markdown utilities)
    ↓
database (AbstractDatabase → SQLiteDB, MSAccessDB + DatabaseContainer)
```

Also exported at package level: Markdown handling (`MarkdownDocument`, `MarkdownFileAsTable`) and extra global-config accessors (`get_global_par_int/float/bool`, `global_ini_par_exists`, `resolve_config_path`, `get_config_dir`).

**Key patterns:**
- Applications bracket execution with `proc_frame_start()` / `proc_frame_end()` — this initializes logging, config, and single-instance locking
- `proc_frame` uses module-level singletons (`_default_logger`, `_ini_config_file`, `_ini_pars`) for global state, thread-safe via GIL
- `log_msg()`/`log_debug()`/`log_info()`/`log_warning()`/`log_error()`/`log_and_raise()` auto-detect caller class/method for CSV log entries: method/line come from stdlib's `stacklevel` parameter, class name from a small dedicated frame-walk (`_caller_classname()` in `logging_object.py`) — both are driven by the same `caller_frame_offset` value threaded through each wrapper layer
- `log_debug`/`log_info`/`log_warning` are thin facades over `log_msg(level=...)`; `log_error`/`log_and_raise` share message-building (`_build_error_message()`) and the copy-on-error trigger (`archive=True` on the shared `_log()` core) — `log_error` does not raise or beep, `log_and_raise` does both. All six funnel through `LoggingObject._log()`
- `LoggingObject(level=...)` / INI `[logging] level` set the global threshold (`DEBUG`/`INFO`/`WARNING`/`ERROR`, case-insensitive in the INI). Deliberately capped at `ERROR` — both `LoggingObject.__init__` and `proc_frame._parse_log_level()` reject anything higher (e.g. `CRITICAL`) — errors must always be logged, so exceeding `ERROR` is a configuration error, not a silently-honored setting. There is no `error_only` parameter anymore — it was removed once `level=logging.ERROR` (or INI `[logging] level = ERROR`) fully subsumed it; this was a deliberate, one-time exception to the API-stability rule below
- **Two logging modules exist:** the public `log_msg`/`log_and_raise` (in `proc_frame.py`, re-exported at package level) do full frame-inspecting CSV file logging. A second, console-only pair in `logging_fallback.py` exists *solely* to break circular imports for low-level modules — do not export or import it from application code; always use the package-level functions
- INI sections support inheritance via `parent_section` parameter (child overrides parent values)
- Container/Iterator pattern: `AbstractContainer` → `create_new_iterator()` → `AbstractIterator` with condition-based filtering
- `LoggingObject` composes a private (non-registry) `logging.Logger` with `CsvLogFormatter`/`AppContextFilter` (`csv_log_formatter.py`), `CsvFileHandler` (`csv_file_handler.py`), `ColorConsoleHandler` (`color_console_handler.py`), and `ErrorCopyHandler` (`error_copy_handler.py`) — CSV formatting, red error console output, and thread-filtered error-log copies are stdlib `logging` handlers, not hand-rolled I/O. Uses `logging.Logger(name, level)` directly rather than `logging.getLogger(name)`, since the latter would share handlers between independent `LoggingObject` instances via the global logger registry

**All public APIs are exported through `__init__.py`** — always import from package level:
```python
from basic_framework import log_msg, IniConfigFile, ConditionEquals
```

## Critical Design Constraints

**API Stability** — do not change existing function names or signatures.

**Frame Inspection** — `log_msg()`/`log_debug()`/`log_info()`/`log_warning()`/`log_error()`/`log_and_raise()` resolve the caller's class via a dedicated frame-walk (`_caller_classname()`) and the caller's method/line via stdlib's `stacklevel` parameter — both keyed off the same `caller_frame_offset`. Do not add a wrapper function without incrementing `caller_frame_offset` by exactly 1 at that layer, or both mechanisms will misattribute the caller by one frame. Phase 1 of the stdlib-logging migration (see `docs/internal/LOGGING_MIGRATION_KONZEPT.md`) is implemented, plus a per-call log-level family (`log_debug`/`log_info`/`log_warning`/`log_error`, and `log_msg(level=...)`) and an INI-configurable global level threshold (`[logging] level`, capped at `ERROR`) on top of it; further phases (log rotation, per-module logger hierarchy) remain planned.

**Platform-Specific:**
- Audio: `winsound` on Windows, terminal bell on Linux/Mac
- Single-instance locking: `msvcrt` on Windows, `fcntl` on Unix
- `os.startfile()` Windows only (skipped elsewhere)

**Disabling Beeps in Tests:**
Set `BASIC_FRAMEWORK_DISABLE_BEEP=1` BEFORE importing `basic_framework.proc_frame` (see `tests/conftest.py`).

**Required INI `[default]` parameters:** `working_dir`, `tmp_dir`, `single_instance`

## Known Limitations

- Internally backed by stdlib `logging` (Phase 1 of the migration, see `docs/internal/LOGGING_MIGRATION_KONZEPT.md`), with a per-call log-level family (`log_debug`/`log_info`/`log_warning`/`log_error`/`log_and_raise`, `log_msg(level=...)`) and an INI-configurable global level threshold (`[logging] level = DEBUG|INFO|WARNING|ERROR`) on top of it. Still missing: log rotation, configurable output format, and per-module logger hierarchy — these remain planned for later migration phases
