# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Patch versions are bumped automatically by CI on every push to `main`, so not
every patch number corresponds to a published release. Only versions listed
below were tagged and released.

## [3.6.1] - 2026-07-26

### Fixed
- `ColorConsoleHandler` no longer subscripts `logging.StreamHandler` at runtime. The subscript is only valid in the typeshed stubs and in Python 3.11+, so importing `basic_framework` on Python 3.10 raised `TypeError: 'type' object is not subscriptable`. It is now evaluated under `TYPE_CHECKING` only; type information for static checkers is preserved

## [3.6.0] - 2026-07-25

Not published to PyPI — superseded by 3.6.1.

### Added
- Per-call log level family: `log_debug()`, `log_info()`, `log_warning()`, `log_error()` — all exported at package level. Note that `log_error` was removed in 2.0.0 and is reintroduced here with different semantics: it logs an error without raising, whereas the old one was replaced by `log_and_raise()`
- `level` parameter on `log_msg()` for explicit per-call levels
- Global level threshold via INI `[logging] level` (`DEBUG`/`INFO`/`WARNING`/`ERROR`, case-insensitive). **Required** in full mode — missing or empty raises `ValueError`, no silent default. Capped at `ERROR`, since errors must always be logged
- `level` parameter on `proc_frame_start()`, effective in console-only mode (`config_file_path=None`); default `logging.INFO`
- `Level` column in the CSV log format, between `Method` and `Message`: `Timestamp;Application;Version;PID;ThreadID;ThreadName;Class;Method;Level;Message`

### Changed
- Logging is now internally backed by the standard library's `logging` module (migration phase 1). CSV formatting, red error console output and thread-filtered error-log copies are implemented as stdlib handlers: `CsvLogFormatter`, `CsvFileHandler`, `ColorConsoleHandler`, `ErrorCopyHandler`
- Caller method and line are resolved via stdlib's `stacklevel` instead of manual frame inspection; only the caller's class name still uses a dedicated frame walk
- `log_and_raise()` continues to log, beep and raise; it shares message building and the copy-on-error trigger with `log_error()`
- Internal console-only logging module renamed `logging.py` → `logging_fallback.py`. It exists solely to break circular imports for low-level modules and must not be used by application code
- Corrected the API used for console output

### Removed
- `error_only` parameter of `proc_frame_start()` — fully subsumed by `level=logging.ERROR` (or INI `[logging] level = ERROR`). A leftover `error_only` entry in `[logging]` now raises a clear error instead of being silently ignored. This was a deliberate, one-time exception to the project's API-stability rule

## [3.5.1] - 2026-04-12

### Changed
- `py.typed` is declared as package-data, so the type marker is reliably delivered in the wheel

### Removed
- Optional `chardet` support in `markdown_document`. It was an `ImportError`-guarded soft dependency that silently fell back to BOM-only detection — a graceful-degradation pattern at odds with the project's fail-fast rule. Encoding detection is now purely BOM-based. `chardet` was never a declared runtime dependency, so nothing changes for installs

## [3.4.1] - 2026-03-25

First release published to PyPI.

### Added
- `error_only` logging mode (removed again in 3.6.0)
- PyPI publish workflow using a Trusted Publisher (OIDC), triggered by publishing a GitHub release

## [3.3.0] - 2026-03-24

Tagged but not published to PyPI.

### Changed
- Full pyright strict-mode compliance across the codebase (146 errors → 0), including suppression of platform-specific type checks on Linux CI
- Dev dependencies consolidated into `pyproject.toml`
- Default branch renamed from `master` to `main`

## [2.0.0] - 2025-01-09

### Changed
- Version number now read from `pyproject.toml` via `importlib.metadata`
- Replaced `log_error` with `log_and_raise` for fail-fast error handling
- Updated documentation to reflect current API

### Removed
- Excel operations (ExcelBook, openpyxl dependency)
- `log_error` function (use `log_and_raise` instead)

### Added
- Environment variable support: `env_par_exists`, `get_env_value`, `get_env_int_value`, `get_env_float_value`, `get_env_bool_value`
- Automatic version bumping via GitHub Actions

## [1.0.0] - 2024-09-02

### Added
- Initial release as standalone package
- Abstract containers and iterators
- Condition system (equals, and, not)
- INI configuration with section inheritance
- Process framework with structured logging
- File system extensions
- Text file as table processing
