"""
Unit tests for environment variable support functions.

Tests for:
- env_par_exists()
- get_env_value()
- get_env_int_value()
- get_env_float_value()
- get_env_bool_value()
"""

import os
import unittest
from typing import Generator

import pytest


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Fixture to ensure test environment variables are cleaned up."""
    test_vars = [
        "TEST_ENV_STRING",
        "TEST_ENV_INT",
        "TEST_ENV_FLOAT",
        "TEST_ENV_BOOL",
        "TEST_ENV_EMPTY",
        "TEST_ENV_NEGATIVE",
        "TEST_ENV_SCIENTIFIC",
    ]
    # Cleanup before test
    for var in test_vars:
        os.environ.pop(var, None)
    yield
    # Cleanup after test
    for var in test_vars:
        os.environ.pop(var, None)


# =============================================================================
# Test Classes
# =============================================================================

class TestEnvParExists:
    """Tests for env_par_exists()."""

    def test_existing_variable_returns_true(self, clean_env: None) -> None:
        """Test that existing environment variable returns True."""
        from basic_framework import env_par_exists

        os.environ["TEST_ENV_STRING"] = "value"
        assert env_par_exists("TEST_ENV_STRING") is True

    def test_non_existing_variable_returns_false(self, clean_env: None) -> None:
        """Test that non-existing environment variable returns False."""
        from basic_framework import env_par_exists

        assert env_par_exists("TEST_ENV_NONEXISTENT_12345") is False

    def test_empty_value_variable_returns_true(self, clean_env: None) -> None:
        """Test that environment variable with empty string value returns True."""
        from basic_framework import env_par_exists

        os.environ["TEST_ENV_EMPTY"] = ""
        assert env_par_exists("TEST_ENV_EMPTY") is True


class TestGetEnvValue:
    """Tests for get_env_value()."""

    def test_existing_variable_returns_value(self, clean_env: None) -> None:
        """Test that existing environment variable returns its value."""
        from basic_framework import get_env_value

        os.environ["TEST_ENV_STRING"] = "test_value"
        result: str = get_env_value("TEST_ENV_STRING")
        assert result == "test_value"

    def test_non_existing_variable_raises_valueerror(self, clean_env: None) -> None:
        """Test that non-existing environment variable raises ValueError."""
        from basic_framework import get_env_value

        with pytest.raises(ValueError) as exc_info:
            get_env_value("TEST_ENV_NONEXISTENT_12345")

        assert "TEST_ENV_NONEXISTENT_12345" in str(exc_info.value)
        assert "not set" in str(exc_info.value)

    def test_empty_string_is_valid_value(self, clean_env: None) -> None:
        """Test that empty string is returned correctly (not treated as missing)."""
        from basic_framework import get_env_value

        os.environ["TEST_ENV_EMPTY"] = ""
        result: str = get_env_value("TEST_ENV_EMPTY")
        assert result == ""


class TestGetEnvIntValue:
    """Tests for get_env_int_value()."""

    def test_valid_integer_returns_int(self, clean_env: None) -> None:
        """Test that valid integer string is converted correctly."""
        from basic_framework import get_env_int_value

        os.environ["TEST_ENV_INT"] = "42"
        result: int = get_env_int_value("TEST_ENV_INT")
        assert result == 42
        assert isinstance(result, int)

    def test_negative_integer_returns_int(self, clean_env: None) -> None:
        """Test that negative integer string is converted correctly."""
        from basic_framework import get_env_int_value

        os.environ["TEST_ENV_NEGATIVE"] = "-123"
        result: int = get_env_int_value("TEST_ENV_NEGATIVE")
        assert result == -123

    def test_zero_returns_int(self, clean_env: None) -> None:
        """Test that zero is converted correctly."""
        from basic_framework import get_env_int_value

        os.environ["TEST_ENV_INT"] = "0"
        result: int = get_env_int_value("TEST_ENV_INT")
        assert result == 0

    def test_non_integer_raises_valueerror(self, clean_env: None) -> None:
        """Test that non-integer value raises ValueError."""
        from basic_framework import get_env_int_value

        os.environ["TEST_ENV_INT"] = "not_a_number"
        with pytest.raises(ValueError) as exc_info:
            get_env_int_value("TEST_ENV_INT")

        assert "TEST_ENV_INT" in str(exc_info.value)
        assert "cannot be converted to integer" in str(exc_info.value)

    def test_float_string_raises_valueerror(self, clean_env: None) -> None:
        """Test that float string raises ValueError when getting int."""
        from basic_framework import get_env_int_value

        os.environ["TEST_ENV_INT"] = "3.14"
        with pytest.raises(ValueError):
            get_env_int_value("TEST_ENV_INT")

    def test_non_existing_variable_raises_valueerror(self, clean_env: None) -> None:
        """Test that non-existing variable raises ValueError."""
        from basic_framework import get_env_int_value

        with pytest.raises(ValueError) as exc_info:
            get_env_int_value("TEST_ENV_NONEXISTENT_12345")

        assert "not set" in str(exc_info.value)


class TestGetEnvFloatValue:
    """Tests for get_env_float_value()."""

    def test_valid_float_returns_float(self, clean_env: None) -> None:
        """Test that valid float string is converted correctly."""
        from basic_framework import get_env_float_value

        os.environ["TEST_ENV_FLOAT"] = "3.14"
        result: float = get_env_float_value("TEST_ENV_FLOAT")
        assert result == 3.14
        assert isinstance(result, float)

    def test_integer_string_returns_float(self, clean_env: None) -> None:
        """Test that integer string can be converted to float."""
        from basic_framework import get_env_float_value

        os.environ["TEST_ENV_FLOAT"] = "42"
        result: float = get_env_float_value("TEST_ENV_FLOAT")
        assert result == 42.0
        assert isinstance(result, float)

    def test_negative_float_returns_float(self, clean_env: None) -> None:
        """Test that negative float string is converted correctly."""
        from basic_framework import get_env_float_value

        os.environ["TEST_ENV_NEGATIVE"] = "-2.5"
        result: float = get_env_float_value("TEST_ENV_NEGATIVE")
        assert result == -2.5

    def test_scientific_notation_returns_float(self, clean_env: None) -> None:
        """Test that scientific notation is converted correctly."""
        from basic_framework import get_env_float_value

        os.environ["TEST_ENV_SCIENTIFIC"] = "1.5e-3"
        result: float = get_env_float_value("TEST_ENV_SCIENTIFIC")
        assert result == 0.0015

    def test_zero_returns_float(self, clean_env: None) -> None:
        """Test that zero is converted correctly."""
        from basic_framework import get_env_float_value

        os.environ["TEST_ENV_FLOAT"] = "0.0"
        result: float = get_env_float_value("TEST_ENV_FLOAT")
        assert result == 0.0

    def test_non_numeric_raises_valueerror(self, clean_env: None) -> None:
        """Test that non-numeric value raises ValueError."""
        from basic_framework import get_env_float_value

        os.environ["TEST_ENV_FLOAT"] = "not_a_number"
        with pytest.raises(ValueError) as exc_info:
            get_env_float_value("TEST_ENV_FLOAT")

        assert "TEST_ENV_FLOAT" in str(exc_info.value)
        assert "cannot be converted to float" in str(exc_info.value)

    def test_non_existing_variable_raises_valueerror(self, clean_env: None) -> None:
        """Test that non-existing variable raises ValueError."""
        from basic_framework import get_env_float_value

        with pytest.raises(ValueError) as exc_info:
            get_env_float_value("TEST_ENV_NONEXISTENT_12345")

        assert "not set" in str(exc_info.value)


class TestGetEnvBoolValue:
    """Tests for get_env_bool_value()."""

    # Parametrized tests for true values
    @pytest.mark.parametrize(
        "true_value",
        ["true", "True", "TRUE", "wahr", "Wahr", "WAHR", "yes", "Yes", "YES", "ja", "Ja", "JA", "1"],
    )
    def test_true_values_return_true(self, clean_env: None, true_value: str) -> None:
        """Test all recognized true values return True (case-insensitive)."""
        from basic_framework import get_env_bool_value

        os.environ["TEST_ENV_BOOL"] = true_value
        result: bool = get_env_bool_value("TEST_ENV_BOOL")
        assert result is True

    # Parametrized tests for false values
    @pytest.mark.parametrize(
        "false_value",
        ["false", "False", "FALSE", "falsch", "Falsch", "FALSCH", "no", "No", "NO", "nein", "Nein", "NEIN", "0"],
    )
    def test_false_values_return_false(self, clean_env: None, false_value: str) -> None:
        """Test all recognized false values return False (case-insensitive)."""
        from basic_framework import get_env_bool_value

        os.environ["TEST_ENV_BOOL"] = false_value
        result: bool = get_env_bool_value("TEST_ENV_BOOL")
        assert result is False

    def test_unrecognized_value_raises_valueerror(self, clean_env: None) -> None:
        """Test that unrecognized boolean value raises ValueError."""
        from basic_framework import get_env_bool_value

        os.environ["TEST_ENV_BOOL"] = "maybe"
        with pytest.raises(ValueError) as exc_info:
            get_env_bool_value("TEST_ENV_BOOL")

        assert "TEST_ENV_BOOL" in str(exc_info.value)
        assert "unrecognized boolean value" in str(exc_info.value)

    def test_empty_string_raises_valueerror(self, clean_env: None) -> None:
        """Test that empty string raises ValueError (not a valid boolean)."""
        from basic_framework import get_env_bool_value

        os.environ["TEST_ENV_EMPTY"] = ""
        with pytest.raises(ValueError) as exc_info:
            get_env_bool_value("TEST_ENV_EMPTY")

        assert "unrecognized boolean value" in str(exc_info.value)

    def test_non_existing_variable_raises_valueerror(self, clean_env: None) -> None:
        """Test that non-existing variable raises ValueError."""
        from basic_framework import get_env_bool_value

        with pytest.raises(ValueError) as exc_info:
            get_env_bool_value("TEST_ENV_NONEXISTENT_12345")

        assert "not set" in str(exc_info.value)


class TestPackageLevelImports:
    """Tests for package-level imports of environment variable functions."""

    def test_all_env_functions_importable(self) -> None:
        """Test that all environment variable functions can be imported."""
        from basic_framework import (
            env_par_exists,
            get_env_value,
            get_env_int_value,
            get_env_float_value,
            get_env_bool_value,
        )

        assert callable(env_par_exists)
        assert callable(get_env_value)
        assert callable(get_env_int_value)
        assert callable(get_env_float_value)
        assert callable(get_env_bool_value)

    def test_env_functions_in_all(self) -> None:
        """Test that all environment variable functions are in __all__."""
        import basic_framework

        expected_exports = [
            "env_par_exists",
            "get_env_value",
            "get_env_int_value",
            "get_env_float_value",
            "get_env_bool_value",
        ]

        for export in expected_exports:
            assert export in basic_framework.__all__, f"{export} not in __all__"


# =============================================================================
# unittest compatibility (for running with python -m unittest)
# =============================================================================

class TestEnvParExistsUnittest(unittest.TestCase):
    """unittest-compatible tests for env_par_exists()."""

    def setUp(self) -> None:
        """Clean up test environment variables before each test."""
        test_vars = ["TEST_ENV_STRING", "TEST_ENV_EMPTY"]
        for var in test_vars:
            os.environ.pop(var, None)

    def tearDown(self) -> None:
        """Clean up test environment variables after each test."""
        test_vars = ["TEST_ENV_STRING", "TEST_ENV_EMPTY"]
        for var in test_vars:
            os.environ.pop(var, None)

    def test_existing_variable(self) -> None:
        """Test that existing variable returns True."""
        from basic_framework import env_par_exists

        os.environ["TEST_ENV_STRING"] = "value"
        self.assertTrue(env_par_exists("TEST_ENV_STRING"))

    def test_non_existing_variable(self) -> None:
        """Test that non-existing variable returns False."""
        from basic_framework import env_par_exists

        self.assertFalse(env_par_exists("TEST_ENV_NONEXISTENT_12345"))


if __name__ == "__main__":
    unittest.main()
