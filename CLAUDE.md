# CLAUDE.md

## Project Overview

**Basic Framework** — standalone Python package for data processing, file handling, configuration management, and structured logging. Extracted from the Krefeld Prototype project.

## Dependencies

- Python >= 3.10
- configparser >= 5.0.0
- pyodbc (optional, MS Access only)

## Development Commands

```bash
pip install -e ".[dev]"             # Dev install (editable + pytest, mypy)
python -m pytest tests/             # Run all tests
mypy src/basic_framework --ignore-missing-imports  # Type check
python -m build                     # Build package
```

Additional test files in root: `test_inheritance.py`, `test_refactored_config.py`, `test_simple_comparison.py`, `test_validation.py`

## Architecture

```
Application Code
    ↓
proc_frame (process lifecycle & logging)
    ↓
ini_config_file (hierarchical configuration)
    ↓
conditions + container_utils (data filtering & processing)
    ↓
ext_filesystem + utils (file & string operations)
```

**Key concepts:**
- Applications bracket execution with `proc_frame_start()` / `proc_frame_end()`
- INI sections support inheritance via `parent_section` parameter
- CSV-format logging with automatic caller detection via frame inspection
- Container/Iterator pattern for table-like data with condition-based filtering
- Module-level singletons for config and logging (thread-safe via GIL)

## Critical Design Constraints

**API Stability** — do not change function names or signatures.

**Frame Inspection** — `log_msg()` and `log_and_raise()` use `inspect.currentframe()` for automatic caller context. Migration to Python standard logging is planned (see `docs/LOGGING_MIGRATION_KONZEPT.md`).

**Platform-Specific:**
- Audio: `winsound` on Windows, terminal bell on Linux/Mac
- `os.startfile()` Windows only (skipped elsewhere)
- Tkinter dialogs may require X server on Linux

**Disabling Beeps in Tests:**
Set `BASIC_FRAMEWORK_DISABLE_BEEP=1` BEFORE importing `basic_framework.proc_frame`.
```python
# conftest.py
import os
os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"
```

**Required INI `[default]` parameters:** `working_dir`, `tmp_dir`, `single_instance`

**All public APIs are exported through `__init__.py`** — always import from package level:
```python
from basic_framework import log_msg, IniConfigFile, ConditionEquals
```

## Known Limitations

- No log levels, rotation, or configurable format (migration planned in 3 phases)
- See `docs/LOGGING_MIGRATION_KONZEPT.md` for details
