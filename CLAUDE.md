# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Basic Framework** is a Python package that provides data processing utilities, file handling, configuration management, and structured logging. It was extracted from the Krefeld Prototype project and is maintained as a standalone, installable package.

## Dependencies

- Python >= 3.10 (tested with 3.10, 3.11, 3.12, 3.13)
- configparser >= 5.0.0
- pyodbc (optional, required only for MS Access database support)

**Note:** The package has minimal dependencies by design. SQLite support uses Python's built-in `sqlite3` module.

## Development Commands

### Installation
```bash
# Development installation (editable mode)
pip install -e .

# Install dev dependencies (pytest, mypy)
pip install -r requirements-dev.txt
```

### Running Tests
```bash
# Run all tests in tests/ directory
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_basic_imports.py

# Run individual test files in root directory
python test_inheritance.py
python test_refactored_config.py
python test_simple_comparison.py
python test_validation.py

# Run specific test class or method
python -m pytest tests/test_basic_imports.py::TestBasicImports::test_package_level_imports
```

### Type Checking
```bash
# Type check with mypy
mypy src/basic_framework --ignore-missing-imports
```

### Package Management
```bash
# Build distribution packages
python -m build

# Install from source
pip install .

# Uninstall
pip uninstall basic-framework
```

## Architecture Overview

### Module Organization

The framework follows a layered architecture:

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

### Key Architectural Concepts

**1. Process Framework Pattern**
- All applications should bracket their execution with `proc_frame_start()` and `proc_frame_end()`
- This initializes logging, configuration, and ensures graceful shutdown with audio feedback
- Global configuration singleton is created during `proc_frame_start()`

**2. Hierarchical Configuration (INI Files)**
- INI sections support parent section inheritance via `parent_section` parameter
- Configuration values cascade from parent sections if not found in current section
- Circular reference validation prevents infinite loops
- Type-safe getters: `get_value()`, `get_int_value()`, `get_float_value()`, `get_bool_value()`

**3. Logging Architecture**
- CSV-format logging with semicolon separators
- Log format: `Zeit;Applikation;Version;PID;ThreadID;ThreadName;Klasse;Methode;Nachricht`
- Automatic metadata capture: timestamp, app name, app version, PID, thread ID/name, class, method
- Frame inspection extracts caller information automatically
- Logs written to: `{working_dir}/Logdateien/{app_name}_{timestamp}.txt`
- Console + file output simultaneously (configurable via `[logging] console_output`)
- Stack traces included on errors (configurable via `[logging] include_stacktrace`)
- Error log copy on `log_and_raise()`: full copy + filtered copy (MainThread + error thread only)
- Audio feedback via `winsound` beeps (Windows-specific)

**4. Container & Iterator Pattern**
- Abstract base classes define interfaces: `AbstractContainer`, `AbstractIterator`
- Concrete implementations: `ContainerInMemory`, `TextFileAsTable`, etc.
- Condition-based filtering: `ConditionEquals`, `ConditionAnd`, `ConditionNot`
- Containers represent table-like data with named fields
- Iterators provide navigation with `.pp()` (move next), `.value(field)` (get value)

**5. Module-Level Singletons**
- `proc_frame.py` maintains global `_ini_config_file` and `_logfile` instances
- Accessed via `get_ini_config_file()`, `get_log_filename()`, `get_global_par()`
- Thread-safe via Python's GIL

### Critical Design Constraints

**API Stability**
- Do not arbitrarily change function names or signatures

**Frame Inspection for Logging**
- `log_msg()` and `log_and_raise()` use `inspect.currentframe()` to extract caller info
- This adds overhead but provides automatic context in logs
- Migration to Python standard logging is planned (see LOGGING_MIGRATION_KONZEPT.md)

**Platform-Specific Features**
- Audio feedback uses `winsound` module on Windows, falls back to terminal bell (`\a`) on Linux/Mac
- File path handling uses both Windows and Unix separators
- Tkinter dialogs for folder selection
- `os.startfile()` for opening log files (Windows only, skipped on other platforms)

**Disabling Beeps (for Unit Tests)**
- Set environment variable `BASIC_FRAMEWORK_DISABLE_BEEP=1` to disable all audio beeps
- Useful for unit tests where `log_and_raise()` is expected to raise exceptions
- Must be set BEFORE importing `basic_framework.proc_frame`
- Example in `conftest.py`:
  ```python
  import os
  os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"
  # Now import other modules
  ```

## Module Reference

### Core Entry Points

**proc_frame.py** - Process Framework
- `proc_frame_start(app_name, app_version, config_file_path)` - Initialize process, logging, config
- `proc_frame_end(beep=None, close_log_flag=True)` - Graceful shutdown (beep controlled via INI config `beep_on_end`, default: false)
- `log_msg(msg)` - Log informational message (auto-captures caller)
- `log_and_raise(error: Union[str, Exception])` - Log error and raise exception (str → ValueError, Exception → re-raises original)
- `get_global_par(name, section)` - Retrieve INI parameter as string
- `get_global_par_int(name, section)` - Retrieve INI parameter as integer
- `get_global_par_float(name, section)` - Retrieve INI parameter as float
- `get_global_par_bool(name, section)` - Retrieve INI parameter as boolean
- `get_ini_config_file()` - Access global configuration singleton
- `get_log_filename()` - Get current log file path
- `get_app_name()` - Get the application name
- `get_app_version()` - Get the application version
- `global_ini_par_exists(name, section)` - Check if parameter exists in global config
- `get_config_dir()` - Get directory where config file is located
- `resolve_config_path(relative_path)` - Resolve path relative to config directory
- `get_default_logger()` - Get the default LoggingObject instance

**logging_object.py** - Logging Class
- `LoggingObject` - Class for structured logging with automatic caller detection

**proc_frame.py** - Environment Variable Support
- `env_par_exists(name)` - Check if environment variable exists
- `get_env_value(name)` - Get environment variable as string (raises if not set)
- `get_env_int_value(name)` - Get environment variable as integer
- `get_env_float_value(name)` - Get environment variable as float
- `get_env_bool_value(name)` - Get environment variable as boolean (true/false, yes/no, 1/0, wahr/falsch, ja/nein)

**logging.py** - Simple Logging (Fallback)
- Lightweight logging module to avoid circular imports with proc_frame
- Use when proc_frame not initialized

**ini_config_file.py** - Configuration Management
- `IniConfigFile.init(filename)` - Load INI file with inheritance support
- `get_value(section, name, default)` - Get string value
- `get_int_value(section, name, default)` - Get integer value
- `get_float_value(section, name, default)` - Get float value (recently added)
- `get_bool_value(section, name, default)` - Get boolean value
- `get_full_config()` - Retrieve all config as nested dictionaries

### Utilities

**utils/basic_utils.py**
- `get_format_now_stamp(with_seconds=False)` - Timestamp: "YYYYMMDD_HHMM[_SS]"
- `is_hyperlink(text)` - Detect if string is URL (http/https)
- `escape_access_sql_string(text)` - Escape for MS Access SQL
- `unescape_access_sql_string(text)` - Reverse escape for MS Access SQL strings
- `is_effectively_null(value)` - Check if value is None, empty string, or whitespace
- `convert_to_mapping(data)` - Convert data to dictionary mapping

**utils/filename_utils.py**
- `get_name_from_full_reference(path)` - Extract filename without extension
- `get_path_from_full_reference(path)` - Extract directory path
- `remove_file_postfix(filename)` - Remove file extension
- `C_DIR_SEPARATOR` - Constant for directory separator

**ext_filesystem.py**
- `file_exists(path)` - Check file existence (exported via `__init__.py`)
- `file_must_exist(path)` - Assert file exists or raise error (exported)
- `directory_must_exist(path)` - Assert directory exists or raise error (exported)
- `replace_path(path)` - Apply URL-to-local path mappings (exported)
- `directory_exists(path)` - Check directory existence (import directly from `basic_framework.ext_filesystem`)
- `remember_replacement(hint)` - Register path substitution rule (import directly from `basic_framework.ext_filesystem`)

### Container System

**container_utils/abstract_container.py**
- Base interface for all container implementations
- Methods: `field_exists()`, `create_iterator()`, `value_of_field()`, `set_value_for_field()`

**container_utils/abstract_iterator.py**
- Base interface for navigating container data
- Methods: `is_empty()`, `value(field)`, `pp()` (move next), `set_value(field, value)`

**container_utils/text_file_as_table.py**
- `TextFileAsTable` - CSV/delimited file as table-like container
- Supports read and write operations
- Custom field separators

**container_utils/markdown_file_as_table.py**
- `MarkdownFileAsTable` - Markdown table (pipe-delimited) as container
- Parses first Markdown table found in the file

**container_utils/static_container_basics.py**
- `create_new_iterator(container, condition=None)` - Factory for creating iterators with filtering

**Additional Container Implementations (Advanced)**
- `ContainerInMemory` - In-memory container for fast data access
- `ContainerDistinct` - Container that filters duplicate records
- `ContainerSimpleIndexed` - Indexed container for key-based lookup
- `ContainerUniqueIndexed` - Indexed container enforcing unique keys
- `KnotObject` - Specialized object for container data representation

These are specialized implementations of `AbstractContainer`. Most users will work with `TextFileAsTable` or create custom implementations by inheriting from `AbstractContainer`.

### Condition System

**conditions/condition.py**
- `Condition` - Abstract base class for all conditions
- Method: `is_true(data)` - Evaluate condition against data object

**conditions/condition_equals.py**
- `ConditionEquals(field, value)` - Equality comparison with SQL-safe escaping

**conditions/condition_and.py**
- `ConditionAnd(conditions)` - Logical AND composition of multiple conditions

**conditions/condition_not.py**
- `ConditionNot(condition)` - Logical NOT negation of condition

**conditions/condition_or.py**
- `ConditionOr(conditions)` - Logical OR composition of multiple conditions

### Markdown Utilities

**utils/markdown_document.py**
- `MarkdownDocument` - Tree-structured parser for Markdown documents
- `MarkdownLineType` - Enum for line types (heading, table row, paragraph, etc.)
- `MarkdownParserState` - Enum for parser state machine
- Optional dependency: `chardet` for improved encoding detection; falls back to UTF-8

### Database System

**database/abstract_database.py**
- `AbstractDatabase` - Abstract base class for all database connections
- `DatabaseCursor` - Protocol defining cursor interface (execute, fetchone, fetchall)

**database/sqlite_db.py**
- `SQLiteDB` - SQLite implementation using built-in `sqlite3` module
- No additional dependencies required

**database/ms_access_db.py**
- `MSAccessDB` - MS Access implementation using `pyodbc`
- Additional methods: `query_exists()`, `get_queries()` for MS Access-specific features

**database/database_container.py**
- `DatabaseContainer(db, table_or_sql)` - Container for database tables or SQL queries
- Implements `AbstractContainer` interface for seamless integration with condition system

**database/database_iterator.py**
- `DatabaseIterator` - Iterator with full read/write support
- Read operations: `value(field)`, `pp()` (move next), `reset()`, `is_empty()`
- Write operations: `start_insert()`, `start_update()`, `set_value(field, value)`, `delete()`, `finish()`

## Common Development Patterns

### Standard Application Structure

```python
from basic_framework import (
    proc_frame_start, proc_frame_end, log_msg, log_and_raise,
    get_global_par, file_exists, file_must_exist
)

def main():
    proc_frame_start("MyApplication", "1.0.0", "config.ini")

    try:
        # Get configuration parameters
        input_file = get_global_par("input_file", "Settings")

        # IMPORTANT: log_and_raise() raises ValueError - no need to catch it
        file_must_exist(input_file)  # Will call log_and_raise() if file missing

        log_msg(f"Processing {input_file}")
        # Application logic here
        log_msg("Processing completed successfully")

    finally:
        # Always execute cleanup, even if log_and_raise() was called
        proc_frame_end()

if __name__ == "__main__":
    main()
```

**Important Note about log_and_raise():**
- `log_and_raise("message")` logs the error, plays a beep, and raises `ValueError`
- `log_and_raise(exception)` logs the exception with stack trace, plays a beep, and re-raises the original exception
- Do **not** wrap these in try-except blocks - they're designed to terminate execution
- Use them for fatal errors where the process cannot continue
- The finally block ensures `proc_frame_end()` is called even after they raise

**Pattern for Recoverable Errors:**

For situations where you want to handle missing resources gracefully instead of terminating:

```python
def main():
    proc_frame_start("MyApplication", "1.0.0", "config.ini")

    try:
        input_file = get_global_par("input_file", "Settings")

        if not file_exists(input_file):
            # For recoverable errors, use log_msg and handle gracefully
            log_msg(f"Warning: Input file not found: {input_file}")
            log_msg("Using default data instead")
            input_file = "default.csv"

        log_msg(f"Processing {input_file}")
        # Application logic here

    finally:
        proc_frame_end()
```

Note: Use `file_exists()` + `log_msg()` for recoverable situations. Use `file_must_exist()` or `log_and_raise()` only for fatal errors that should terminate execution.

### INI Configuration with Inheritance

**Required Parameters in `[default]` section:**

| Parameter | Description |
|-----------|-------------|
| `working_dir` | Working directory for the application |
| `tmp_dir` | Temporary directory for lock files (supports `%TEMP%` expansion) |
| `single_instance` | `true`/`false` - Prevent multiple instances of the application |

**Optional Parameters in `[logging]` section:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `console_output` | `true` | Enable/disable console output |
| `include_stacktrace` | `true` | Include stack traces in error logs |
| `copy_on_error` | `true` | Copy log file to error directory on `log_and_raise()` |
| `error_log_dir` | `errors` | Subdirectory name for error log copies (relative to logs/) |
| `error_log_auto_copy_dir` | (none) | Optional: absolute path to auto-copy error logs (must exist) |
| `beep_on_end` | `false` | Play audio beep when process ends via `proc_frame_end()` |

**Example Configuration:**

```ini
[default]
working_dir = C:\MyData\projects\myapp
tmp_dir = %TEMP%
single_instance = true
timeout = 30
retry_count = 3

[logging]
console_output = true
include_stacktrace = true
copy_on_error = true
error_log_dir = errors
beep_on_end = false
error_log_auto_copy_dir = \\server\share\error_logs

[production]
parent_section = default
database_host = prod.example.com
timeout = 60

[development]
parent_section = default
database_host = localhost
```

Access in code:
```python
config = get_ini_config_file()
host = config.get_value("production", "database_host")  # "prod.example.com"
timeout = config.get_int_value("production", "timeout")  # 60 (overridden)
retry = config.get_int_value("production", "retry_count")  # 3 (inherited)
```

### Environment Variables

```python
from basic_framework import (
    env_par_exists, get_env_value, get_env_int_value,
    get_env_float_value, get_env_bool_value
)

# Check existence before access (optional - get_env_value raises if not set)
if env_par_exists("DATABASE_URL"):
    db_url = get_env_value("DATABASE_URL")

# Type-safe getters (raise ValueError if invalid format)
port = get_env_int_value("DB_PORT")  # Must be valid integer
timeout = get_env_float_value("TIMEOUT_SECONDS")  # Must be valid float
debug = get_env_bool_value("DEBUG_MODE")  # true/false, yes/no, 1/0, wahr/falsch, ja/nein
```

**Security Note:** Environment variable values are NOT logged to prevent leaking secrets.

### Container Processing with Filtering

**Basic Pattern - Iterating over any AbstractContainer:**

```python
from basic_framework import AbstractContainer, create_new_iterator, ConditionEquals

def process_container(container: AbstractContainer):
    """Process all records in a container."""
    # Create iterator without filtering
    iterator = container.create_iterator()

    while not iterator.is_empty():
        # Access field values by name
        name = iterator.value("name")
        value = iterator.value("value")

        # Process the data
        log_msg(f"Processing: {name} = {value}")

        # Move to next record
        iterator.pp()

def process_filtered_container(container: AbstractContainer):
    """Process filtered records in a container."""
    # Create iterator with condition
    condition = ConditionEquals("status", "active")
    iterator = create_new_iterator(container, condition)

    while not iterator.is_empty():
        # Only processes records where status == "active"
        name = iterator.value("name")
        iterator.pp()
```

**Concrete Example - TextFileAsTable:**

```python
from basic_framework import TextFileAsTable, ConditionEquals, create_new_iterator

# Load CSV file as table
table = TextFileAsTable()
table.init("data.csv", field_separator=",")

# Create filtered iterator for active records
condition = ConditionEquals("status", "active")
iterator = create_new_iterator(table, condition)

while not iterator.is_empty():
    name = iterator.value("name")
    value = iterator.value("value")
    log_msg(f"Processing: {name} = {value}")
    iterator.pp()  # Move to next record
```

**Copying Container Data:**

```python
from basic_framework.container_utils.container_in_memory import ContainerInMemory

def copy_container_to_memory(source_container: AbstractContainer) -> ContainerInMemory:
    """Copy any container to in-memory container."""
    memory_container = ContainerInMemory()
    memory_container.init(source_container)  # Internally iterates and copies all data
    return memory_container
```

## Package Exports

All public APIs are exported through [\_\_init\_\_.py](src/basic_framework/__init__.py):

- Abstract classes: `AbstractContainer`, `AbstractIterator`, `Condition`
- Condition classes: `ConditionEquals`, `ConditionAnd`, `ConditionNot`, `ConditionOr`
- Utilities: `get_format_now_stamp`, `is_hyperlink`, `escape_access_sql_string`, etc.
- File operations: `file_exists`, `file_must_exist`, `directory_must_exist`, `replace_path`
- Configuration: `IniConfigFile`
- Logging: `LoggingObject`, `get_default_logger`
- Process framework: `proc_frame_start`, `proc_frame_end`, `log_msg`, `log_and_raise`, `get_global_par`, `get_ini_config_file`, `get_log_filename`, `get_app_name`, `get_app_version`, `global_ini_par_exists`
- Environment variables: `env_par_exists`, `get_env_value`, `get_env_int_value`, `get_env_float_value`, `get_env_bool_value`
- Containers: `create_new_iterator`, `TextFileAsTable`, `MarkdownFileAsTable`
- Markdown: `MarkdownDocument`, `MarkdownLineType`, `MarkdownParserState`
- Database: `AbstractDatabase`, `DatabaseCursor`, `SQLiteDB`, `MSAccessDB`, `DatabaseContainer`

Users should import from the package level:
```python
from basic_framework import log_msg, IniConfigFile, ConditionEquals
```

## Known Limitations and Future Plans

### Logging System Migration
See [docs/LOGGING_MIGRATION_KONZEPT.md](docs/LOGGING_MIGRATION_KONZEPT.md) for detailed migration plan.

**Current Limitations:**
- No log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- No log rotation (files grow indefinitely)
- No configurable output format beyond CSV
- Frame inspection adds performance overhead

**Planned Migration:**
- Phase 1: Compatibility layer (wrapper functions preserve existing API)
- Phase 2: Custom handlers (CSV format, beep audio, rotation)
- Phase 3: Full migration to Python standard logging
- All existing code remains compatible throughout

### Platform Compatibility
- Audio feedback uses `winsound` on Windows, terminal bell (`\a`) on Linux/Mac
- Tkinter folder dialogs may require X server on Linux
- `os.startfile()` for opening log files only available on Windows

## Testing

### Test Structure
- Unit tests in `tests/` directory (pytest/unittest framework)
- Additional functional tests in root directory: `test_inheritance.py`, `test_refactored_config.py`, etc.
- Test INI files: `test_config.ini`, `test_circular.ini`, `test_invalid.ini`

### Test Data
- Logging output: `Logdateien/` directory (auto-created)
- Test config files demonstrate inheritance and circular reference validation

## Related Projects

This framework was extracted from the **Krefeld Prototype** project and serves as a foundational library for that ecosystem.
