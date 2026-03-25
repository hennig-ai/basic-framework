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
ext_filesystem + utils (file ops & string utilities)
    ↓
database (AbstractDatabase → SQLiteDB, MSAccessDB + DatabaseContainer)
```

**Key patterns:**
- Applications bracket execution with `proc_frame_start()` / `proc_frame_end()` — this initializes logging, config, and single-instance locking
- `proc_frame` uses module-level singletons (`_default_logger`, `_ini_config_file`, `_ini_pars`) for global state, thread-safe via GIL
- `log_msg()` and `log_and_raise()` use `inspect.currentframe()` to auto-detect caller class/method for CSV log entries
- INI sections support inheritance via `parent_section` parameter (child overrides parent values)
- Container/Iterator pattern: `AbstractContainer` → `create_new_iterator()` → `AbstractIterator` with condition-based filtering
- `LoggingObject` encapsulates CSV-format file logging with thread filtering and error log copies

**All public APIs are exported through `__init__.py`** — always import from package level:
```python
from basic_framework import log_msg, IniConfigFile, ConditionEquals
```

## Critical Design Constraints

**API Stability** — do not change existing function names or signatures.

**Frame Inspection** — `log_msg()` and `log_and_raise()` rely on `inspect.currentframe()`. Do not add wrapper functions that change the call depth without adjusting frame traversal. Migration to Python standard logging is planned (see `docs/internal/LOGGING_MIGRATION_KONZEPT.md`).

**Platform-Specific:**
- Audio: `winsound` on Windows, terminal bell on Linux/Mac
- Single-instance locking: `msvcrt` on Windows, `fcntl` on Unix
- `os.startfile()` Windows only (skipped elsewhere)

**Disabling Beeps in Tests:**
Set `BASIC_FRAMEWORK_DISABLE_BEEP=1` BEFORE importing `basic_framework.proc_frame` (see `tests/conftest.py`).

**Required INI `[default]` parameters:** `working_dir`, `tmp_dir`, `single_instance`

## Known Limitations

- No log levels, rotation, or configurable format (migration planned — see `docs/internal/LOGGING_MIGRATION_KONZEPT.md`)
