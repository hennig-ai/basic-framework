"""
Shared pytest fixtures for basic_framework tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Disable beeps before importing basic_framework modules
os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_ini_file(temp_dir: Path) -> Path:
    """Create a sample INI file for testing."""
    ini_path = temp_dir / "test_config.ini"
    ini_path.write_text(
        """[default]
single_instance = false
timeout = 30
debug = true

[logging]
console_output = false
include_stacktrace = true

[production]
parent_section = default
timeout = 60
database_host = prod.example.com

[development]
parent_section = production
database_host = localhost
""",
        encoding="utf-8",
    )
    return ini_path


@pytest.fixture
def circular_ini_file(temp_dir: Path) -> Path:
    """Create an INI file with circular parent_section references."""
    ini_path = temp_dir / "circular_config.ini"
    ini_path.write_text(
        """[default]
value = default_value

[section_a]
parent_section = section_b
value_a = a

[section_b]
parent_section = section_a
value_b = b
""",
        encoding="utf-8",
    )
    return ini_path


@pytest.fixture
def invalid_parent_ini_file(temp_dir: Path) -> Path:
    """Create an INI file with non-existent parent_section."""
    ini_path = temp_dir / "invalid_parent.ini"
    ini_path.write_text(
        """[default]
value = default_value

[child]
parent_section = nonexistent_section
child_value = test
""",
        encoding="utf-8",
    )
    return ini_path


@pytest.fixture
def sample_csv_file(temp_dir: Path) -> Path:
    """Create a sample CSV file for TextFileAsTable testing."""
    csv_path = temp_dir / "test_data.csv"
    csv_path.write_text(
        """name;value;status
item1;100;active
item2;200;inactive
item3;300;active
""",
        encoding="utf-8",
    )
    return csv_path


@pytest.fixture
def empty_csv_file(temp_dir: Path) -> Path:
    """Create an empty CSV file with only headers."""
    csv_path = temp_dir / "empty_data.csv"
    csv_path.write_text("name;value;status\n", encoding="utf-8")
    return csv_path


class MockDataObject:
    """Mock data object for condition testing."""

    def __init__(self, data: dict):
        self._data = data

    def get_value(self, column: str):
        return self._data.get(column)


@pytest.fixture
def mock_data_object() -> MockDataObject:
    """Create a mock data object for condition tests."""
    return MockDataObject({"name": "test", "value": 100, "status": "active"})
