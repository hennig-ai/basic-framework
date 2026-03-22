# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
