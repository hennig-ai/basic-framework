# Basic Framework

[![CI](https://github.com/hennig-ai/basic-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/hennig-ai/basic-framework/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python framework providing essential utilities for data processing, file handling, configuration management, and structured logging.

## Overview

The Basic Framework was originally part of the Krefeld Prototype project and has been extracted into a standalone, installable Python package. It provides a comprehensive set of tools for:

- **Abstract Containers & Iterators**: Generic data container interfaces with filtering capabilities
- **Condition Handling**: Flexible condition system for data filtering (equals, not, and operations)
- **File System Extensions**: Enhanced file and directory operations
- **Configuration Management**: INI file handling with section inheritance
- **Process Framework**: Structured logging and process lifecycle management
- **Text File Processing**: Text files as table-like data structures
- **Environment Variables**: Type-safe access to environment variables

## Installation

### From Source (Development)

```bash
cd basic_framework
pip install -e .
```

### From GitHub

```bash
pip install git+https://github.com/hennig-ai/basic-framework.git
```

### Dependencies

- Python >= 3.10 (tested with 3.10, 3.11, 3.12, 3.13)
- configparser >= 5.0.0

## Quick Start

```python
from basic_framework import (
    IniConfigFile,
    proc_frame_start,
    proc_frame_end,
    log_msg,
    log_and_raise,
    file_exists
)

# Process framework with logging
proc_frame_start("MyProcess", "1.0.0", "config.ini")

try:
    log_msg("Processing started")

    if not file_exists("data.csv"):
        log_and_raise("Required file data.csv not found")

    log_msg("Processing completed successfully")
finally:
    proc_frame_end()
```

## Core Components

### Abstract Containers

```python
from basic_framework import AbstractContainer, create_new_iterator

# Create custom data containers with filtering capabilities
# Implement AbstractContainer interface for your data sources
```

### Conditions System

```python
from basic_framework import ConditionEquals, ConditionAnd, ConditionNot

# Create flexible filtering conditions
condition = ConditionAnd([
    ConditionEquals("status", "active"),
    ConditionNot(ConditionEquals("type", "archived"))
])
```

### File System Extensions

```python
from basic_framework import file_exists, file_must_exist, replace_path

# Enhanced file operations
if file_exists("myfile.txt"):
    processed_path = replace_path("~/data/file.csv")
    file_must_exist(processed_path)  # Raises error if missing
```

### Process Framework & Logging

```python
from basic_framework import proc_frame_start, proc_frame_end, log_msg, log_and_raise

# Structured process lifecycle
proc_frame_start("DataProcessing", "1.0.0", "config.ini")
try:
    log_msg("Processing started")
    # Your processing logic
    log_msg("Processing completed successfully")
except Exception as e:
    log_and_raise(f"Processing failed: {e}")
finally:
    proc_frame_end()
```

### Configuration with INI Files

```python
from basic_framework import IniConfigFile, get_global_par

# After proc_frame_start, access config via global functions
value = get_global_par("parameter_name", "section_name")

# Or use IniConfigFile directly
config = IniConfigFile()
config.init("settings.ini")
value = config.get_value("Section", "Key", "DefaultValue")
int_value = config.get_int_value("Section", "Count", 10)
bool_value = config.get_bool_value("Section", "Enabled", False)
```

INI files support section inheritance via `parent_section`:

```ini
[default]
timeout = 30
retry_count = 3

[production]
parent_section = default
timeout = 60
```

### Environment Variables

```python
from basic_framework import (
    env_par_exists,
    get_env_value,
    get_env_int_value,
    get_env_float_value,
    get_env_bool_value
)

# Type-safe environment variable access
if env_par_exists("DATABASE_URL"):
    db_url = get_env_value("DATABASE_URL")

port = get_env_int_value("DB_PORT")
timeout = get_env_float_value("TIMEOUT_SECONDS")
debug = get_env_bool_value("DEBUG_MODE")  # Supports: true/false, yes/no, 1/0
```

### Text File as Table

```python
from basic_framework import TextFileAsTable, create_new_iterator

# Process text files as structured data
table = TextFileAsTable()
table.init("data.csv", field_separator=",")

# Iterate over rows
iterator = table.create_iterator()
while not iterator.is_empty():
    name = iterator.value("Name")
    value = iterator.value("Value")
    iterator.pp()  # Move to next row
```

## Utilities

### Path and File Operations

```python
from basic_framework import (
    get_name_from_full_reference,
    get_path_from_full_reference,
    remove_file_postfix,
    is_hyperlink
)

# File path utilities
filename = get_name_from_full_reference("C:/data/file.csv")  # "file.csv"
name_only = remove_file_postfix(filename)  # "file"
path = get_path_from_full_reference("C:/data/file.csv")  # "C:/data/"

# URL detection
if is_hyperlink("https://example.com/file.csv"):
    # Handle URL
    pass
```

### String Operations

```python
from basic_framework import escape_access_sql_string, get_format_now_stamp

# SQL string escaping for Access queries
safe_string = escape_access_sql_string("user's [data]")

# Timestamp formatting
timestamp = get_format_now_stamp(with_seconds=True)  # "20231201_1430_25"
```

## Architecture

The framework follows these design principles:

- **Modular Design**: Each module has clear responsibilities and minimal dependencies
- **Logging Integration**: Comprehensive logging throughout all operations
- **Fail-Fast**: Errors are raised immediately with `log_and_raise()` rather than silently ignored
- **Type Safety**: Full type hints for better IDE support and code clarity

## License

MIT License - Copyright (c) 2024-2026 Lars Hennig

See [LICENSE](LICENSE) for details.

## Support

For issues and feature requests, please use the [issue tracker](https://github.com/hennig-ai/basic-framework/issues).
