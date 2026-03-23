"""
Unit tests for condition classes.

Tests for:
- ConditionEquals
- ConditionAnd
- ConditionNot
"""

import os

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"

from basic_framework.conditions.condition_equals import ConditionEquals
from basic_framework.conditions.condition_and import ConditionAnd
from basic_framework.conditions.condition_not import ConditionNot


class MockDataObject:
    """Mock data object for testing conditions."""

    def __init__(self, data: dict):
        self._data = data

    def get_value(self, column: str):
        return self._data.get(column)


# =============================================================================
# ConditionEquals Tests
# =============================================================================


class TestConditionEquals:
    """Tests for ConditionEquals class."""

    def test_equals_string_true(self) -> None:
        """Test equality with matching string value."""
        data = MockDataObject({"status": "active"})
        condition = ConditionEquals("status", "active")
        assert condition.is_true(data) is True

    def test_equals_string_false(self) -> None:
        """Test equality with non-matching string value."""
        data = MockDataObject({"status": "inactive"})
        condition = ConditionEquals("status", "active")
        assert condition.is_true(data) is False

    def test_equals_integer_true(self) -> None:
        """Test equality with matching integer value."""
        data = MockDataObject({"count": 100})
        condition = ConditionEquals("count", 100)
        assert condition.is_true(data) is True

    def test_equals_integer_false(self) -> None:
        """Test equality with non-matching integer value."""
        data = MockDataObject({"count": 200})
        condition = ConditionEquals("count", 100)
        assert condition.is_true(data) is False

    def test_equals_none_value(self) -> None:
        """Test equality with None value."""
        data = MockDataObject({"field": None})
        condition = ConditionEquals("field", None)
        assert condition.is_true(data) is True

    def test_equals_missing_field(self) -> None:
        """Test equality when field is missing (returns None)."""
        data = MockDataObject({"other": "value"})
        condition = ConditionEquals("missing", None)
        # get_value returns None for missing keys
        assert condition.is_true(data) is True

    def test_as_string_numeric(self) -> None:
        """Test as_string for numeric value."""
        condition = ConditionEquals("count", 100)
        result = condition.as_string()
        assert result == "[count]=100"

    def test_as_string_float(self) -> None:
        """Test as_string for float value."""
        condition = ConditionEquals("rate", 3.14)
        result = condition.as_string()
        assert result == "[rate]=3.14"

    def test_as_string_string(self) -> None:
        """Test as_string for string value."""
        condition = ConditionEquals("name", "test")
        result = condition.as_string()
        assert result == "[name]='test'"

    def test_as_string_escapes_quotes(self) -> None:
        """Test as_string escapes single quotes."""
        condition = ConditionEquals("name", "test's value")
        result = condition.as_string()
        assert "''" in result  # Escaped quote


# =============================================================================
# ConditionAnd Tests
# =============================================================================


class TestConditionAnd:
    """Tests for ConditionAnd class."""

    def test_both_conditions_true(self) -> None:
        """Test AND with both conditions true."""
        data = MockDataObject({"status": "active", "count": 100})
        cond1 = ConditionEquals("status", "active")
        cond2 = ConditionEquals("count", 100)
        and_cond = ConditionAnd(cond1, cond2)
        assert and_cond.is_true(data) is True

    def test_first_condition_false(self) -> None:
        """Test AND with first condition false."""
        data = MockDataObject({"status": "inactive", "count": 100})
        cond1 = ConditionEquals("status", "active")
        cond2 = ConditionEquals("count", 100)
        and_cond = ConditionAnd(cond1, cond2)
        assert and_cond.is_true(data) is False

    def test_second_condition_false(self) -> None:
        """Test AND with second condition false."""
        data = MockDataObject({"status": "active", "count": 200})
        cond1 = ConditionEquals("status", "active")
        cond2 = ConditionEquals("count", 100)
        and_cond = ConditionAnd(cond1, cond2)
        assert and_cond.is_true(data) is False

    def test_both_conditions_false(self) -> None:
        """Test AND with both conditions false."""
        data = MockDataObject({"status": "inactive", "count": 200})
        cond1 = ConditionEquals("status", "active")
        cond2 = ConditionEquals("count", 100)
        and_cond = ConditionAnd(cond1, cond2)
        assert and_cond.is_true(data) is False

    def test_as_string_both_conditions(self) -> None:
        """Test as_string with both conditions."""
        cond1 = ConditionEquals("status", "active")
        cond2 = ConditionEquals("count", 100)
        and_cond = ConditionAnd(cond1, cond2)
        result = and_cond.as_string()
        assert "and" in result
        assert "[status]" in result
        assert "[count]" in result



# =============================================================================
# ConditionNot Tests
# =============================================================================


class TestConditionNot:
    """Tests for ConditionNot class."""

    def test_negates_true_to_false(self) -> None:
        """Test NOT negates true condition to false."""
        data = MockDataObject({"status": "active"})
        inner_cond = ConditionEquals("status", "active")
        not_cond = ConditionNot(inner_cond)
        assert not_cond.is_true(data) is False

    def test_negates_false_to_true(self) -> None:
        """Test NOT negates false condition to true."""
        data = MockDataObject({"status": "inactive"})
        inner_cond = ConditionEquals("status", "active")
        not_cond = ConditionNot(inner_cond)
        assert not_cond.is_true(data) is True

    def test_as_string(self) -> None:
        """Test as_string representation."""
        inner_cond = ConditionEquals("status", "active")
        not_cond = ConditionNot(inner_cond)
        result = not_cond.as_string()
        assert result == "not ([status]='active')"

    def test_double_negation(self) -> None:
        """Test double NOT returns original result."""
        data = MockDataObject({"status": "active"})
        inner_cond = ConditionEquals("status", "active")
        not_cond = ConditionNot(inner_cond)
        double_not = ConditionNot(not_cond)
        assert double_not.is_true(data) is True


# =============================================================================
# Combined Condition Tests
# =============================================================================


class TestCombinedConditions:
    """Tests for combining multiple conditions."""

    def test_not_and_combination(self) -> None:
        """Test NOT(AND) combination."""
        data = MockDataObject({"status": "active", "count": 100})
        cond1 = ConditionEquals("status", "active")
        cond2 = ConditionEquals("count", 100)
        and_cond = ConditionAnd(cond1, cond2)
        not_and = ConditionNot(and_cond)
        # Both are true, AND is true, NOT(AND) is false
        assert not_and.is_true(data) is False

    def test_and_with_not_inside(self) -> None:
        """Test AND with NOT as one condition."""
        data = MockDataObject({"status": "inactive", "count": 100})
        cond1 = ConditionNot(ConditionEquals("status", "active"))  # status != active
        cond2 = ConditionEquals("count", 100)
        and_cond = ConditionAnd(cond1, cond2)
        # status is inactive (NOT active = true), count is 100 (true)
        assert and_cond.is_true(data) is True

    def test_nested_and(self) -> None:
        """Test nested AND conditions."""
        data = MockDataObject({"a": 1, "b": 2, "c": 3})
        cond_a = ConditionEquals("a", 1)
        cond_b = ConditionEquals("b", 2)
        cond_c = ConditionEquals("c", 3)
        # (a=1 AND b=2) AND c=3
        inner_and = ConditionAnd(cond_a, cond_b)
        outer_and = ConditionAnd(inner_and, cond_c)
        assert outer_and.is_true(data) is True
