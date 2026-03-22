"""
Unit tests for ContainerInMemory class.

Tests for:
- Initialization (init_new, init from container)
- Row operations (add_empty_row, get_value, set_value)
- Field operations (field_exists, get_list_of_fields_as_ref)
- Memory operations (purge_memory)
- Iterator creation
- Read-only mode validation
"""

import os
from pathlib import Path

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"

from basic_framework.container_utils.container_in_memory import (
    ContainerInMemory,
    TableAccessType,
)
from basic_framework.conditions.condition_equals import ConditionEquals


# =============================================================================
# Initialization Tests
# =============================================================================


class TestContainerInMemoryInitialization:
    """Tests for container initialization."""

    def test_init_new_creates_empty_container(self) -> None:
        """Test init_new creates container with headers but no rows."""
        container = ContainerInMemory()
        container.init_new(["col1", "col2", "col3"])

        assert container.field_exists("col1") is True
        assert container.field_exists("col2") is True
        assert container.field_exists("col3") is True
        assert container.iterator_is_empty(1) is True  # No rows yet

    def test_init_new_with_tech_name(self) -> None:
        """Test init_new with technical name."""
        container = ContainerInMemory()
        container.init_new(["col1"], tech_name="tech_test", logical_name="logical_test")

        assert container.get_technical_container_name() == "tech_test"
        assert container.get_logical_container_name() == "logical_test"

    def test_init_new_without_tech_name_uses_memory_prefix(self) -> None:
        """Test init_new without tech_name uses Memory: prefix."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        tech_name = container.get_technical_container_name()
        file_name = container.get_file_name()

        assert tech_name.startswith("Memory:")
        assert file_name.startswith("Memory:")

    def test_init_new_sets_read_write_mode(self) -> None:
        """Test init_new sets READ_WRITE access type."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        assert container.m_eAccType == TableAccessType.READ_WRITE

    def test_init_from_container_copies_data(self, sample_csv_file: Path) -> None:
        """Test init from another container copies all data."""
        # Create source container
        from basic_framework.container_utils.text_file_as_table import TextFileAsTable

        source = TextFileAsTable()
        source.init_for_read_only(str(sample_csv_file))

        # Create memory container from source
        memory_container = ContainerInMemory()
        memory_container.init(source)

        # Check fields were copied
        assert memory_container.field_exists("name") is True
        assert memory_container.field_exists("value") is True
        assert memory_container.field_exists("status") is True

        # Check data was copied
        assert memory_container.get_value(1, "name") == "item1"
        assert memory_container.get_value(2, "name") == "item2"
        assert memory_container.get_value(3, "name") == "item3"

        source.close_object()

    def test_init_from_container_sets_read_only_mode(self, sample_csv_file: Path) -> None:
        """Test init from container sets READ_ONLY access type."""
        from basic_framework.container_utils.text_file_as_table import TextFileAsTable

        source = TextFileAsTable()
        source.init_for_read_only(str(sample_csv_file))

        memory_container = ContainerInMemory()
        memory_container.init(source)

        assert memory_container.m_eAccType == TableAccessType.READ_ONLY

        source.close_object()


# =============================================================================
# Row Operation Tests
# =============================================================================


class TestContainerInMemoryRowOperations:
    """Tests for row operations."""

    def test_add_empty_row_returns_row_index(self) -> None:
        """Test add_empty_row returns correct row index."""
        container = ContainerInMemory()
        container.init_new(["col1", "col2"])

        row1 = container.add_empty_row()
        row2 = container.add_empty_row()
        row3 = container.add_empty_row()

        assert row1 == 1
        assert row2 == 2
        assert row3 == 3

    def test_add_empty_row_creates_row_with_none_values(self) -> None:
        """Test add_empty_row creates row with None values."""
        container = ContainerInMemory()
        container.init_new(["col1", "col2"])

        row_idx = container.add_empty_row()

        # Empty rows contain None values (consistent with DatabaseIterator behavior)
        assert container.get_value(row_idx, "col1") is None
        assert container.get_value(row_idx, "col2") is None

    def test_set_value_stores_value(self) -> None:
        """Test set_value correctly stores value."""
        container = ContainerInMemory()
        container.init_new(["name", "value"])
        container.add_empty_row()

        container.set_value(1, "name", "test_name")
        container.set_value(1, "value", 42)

        assert container.get_value(1, "name") == "test_name"
        assert container.get_value(1, "value") == 42

    def test_get_value_with_invalid_position_raises(self) -> None:
        """Test get_value with invalid position raises error."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        with pytest.raises(ValueError) as exc_info:
            container.get_value(999, "col1")
        assert "Unzulässige Iteratorposition" in str(exc_info.value)

    def test_get_value_with_invalid_column_raises(self) -> None:
        """Test get_value with invalid column raises error."""
        container = ContainerInMemory()
        container.init_new(["col1"])
        container.add_empty_row()

        with pytest.raises(ValueError) as exc_info:
            container.get_value(1, "nonexistent")
        assert "existiert nicht" in str(exc_info.value)

    def test_set_value_with_invalid_column_raises(self) -> None:
        """Test set_value with invalid column raises error."""
        container = ContainerInMemory()
        container.init_new(["col1"])
        container.add_empty_row()

        with pytest.raises(ValueError) as exc_info:
            container.set_value(1, "nonexistent", "value")
        assert "existiert nicht" in str(exc_info.value)

    def test_set_value_auto_extends_rows(self) -> None:
        """Test set_value auto-extends rows if position doesn't exist."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        # Setting value at position 1 should auto-create row
        container.set_value(1, "col1", "value1")

        assert container.get_value(1, "col1") == "value1"


# =============================================================================
# Field Operation Tests
# =============================================================================


class TestContainerInMemoryFieldOperations:
    """Tests for field operations."""

    def test_field_exists_returns_true_for_existing(self) -> None:
        """Test field_exists returns True for existing field."""
        container = ContainerInMemory()
        container.init_new(["col1", "col2"])

        assert container.field_exists("col1") is True
        assert container.field_exists("col2") is True

    def test_field_exists_returns_false_for_nonexistent(self) -> None:
        """Test field_exists returns False for nonexistent field."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        assert container.field_exists("nonexistent") is False

    def test_get_list_of_fields_as_ref(self) -> None:
        """Test get_list_of_fields_as_ref returns all fields."""
        container = ContainerInMemory()
        container.init_new(["col1", "col2", "col3"])

        fields = container.get_list_of_fields_as_ref()

        assert "col1" in fields
        assert "col2" in fields
        assert "col3" in fields
        assert len(fields) == 3


# =============================================================================
# Memory Operation Tests
# =============================================================================


class TestContainerInMemoryMemoryOperations:
    """Tests for memory operations."""

    def test_purge_memory_clears_all_rows(self) -> None:
        """Test purge_memory clears all rows."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        container.add_empty_row()
        container.set_value(1, "col1", "value1")
        container.add_empty_row()
        container.set_value(2, "col1", "value2")

        # Verify rows exist
        assert container.iterator_is_empty(1) is False
        assert container.iterator_is_empty(2) is False

        # Purge
        container.purge_memory()

        # Verify rows are gone
        assert container.iterator_is_empty(1) is True
        assert container.iterator_is_empty(2) is True

    def test_iterator_is_empty_returns_true_for_nonexistent_row(self) -> None:
        """Test iterator_is_empty returns True for nonexistent row."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        assert container.iterator_is_empty(1) is True
        assert container.iterator_is_empty(999) is True

    def test_iterator_is_empty_returns_false_for_existing_row(self) -> None:
        """Test iterator_is_empty returns False for existing row."""
        container = ContainerInMemory()
        container.init_new(["col1"])
        container.add_empty_row()

        assert container.iterator_is_empty(1) is False


# =============================================================================
# Iterator Tests
# =============================================================================


class TestContainerInMemoryIterator:
    """Tests for iterator creation."""

    def test_create_iterator_returns_iterator(self) -> None:
        """Test create_iterator returns valid iterator."""
        container = ContainerInMemory()
        container.init_new(["col1", "col2"])
        container.add_empty_row()
        container.set_value(1, "col1", "value1")

        iterator = container.create_iterator()

        assert iterator is not None
        assert iterator.is_empty() is False

    def test_create_iterator_on_empty_container(self) -> None:
        """Test create_iterator on empty container."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        iterator = container.create_iterator()

        assert iterator.is_empty() is True

    def test_iterator_access_values(self) -> None:
        """Test iterator can access values."""
        container = ContainerInMemory()
        container.init_new(["name", "value"])
        container.add_empty_row()
        container.set_value(1, "name", "test")
        container.set_value(1, "value", "123")

        iterator = container.create_iterator()

        assert iterator.value("name") == "test"
        assert iterator.value("value") == "123"

    def test_create_iterator_with_condition(self) -> None:
        """Test create_iterator with condition."""
        container = ContainerInMemory()
        container.init_new(["name", "status"])

        container.add_empty_row()
        container.set_value(1, "name", "item1")
        container.set_value(1, "status", "active")

        container.add_empty_row()
        container.set_value(2, "name", "item2")
        container.set_value(2, "status", "inactive")

        container.add_empty_row()
        container.set_value(3, "name", "item3")
        container.set_value(3, "status", "active")

        # Create iterator with condition for active status
        condition = ConditionEquals("status", "active")
        iterator = container.create_iterator(condition=condition)

        # Should find first active item
        assert iterator.is_empty() is False
        assert iterator.value("name") == "item1"


# =============================================================================
# Read-Only Mode Tests
# =============================================================================


class TestContainerInMemoryReadOnlyMode:
    """Tests for read-only mode validation."""

    def test_add_empty_row_raises_in_read_only_mode(self, sample_csv_file: Path) -> None:
        """Test add_empty_row raises in read-only mode."""
        from basic_framework.container_utils.text_file_as_table import TextFileAsTable

        source = TextFileAsTable()
        source.init_for_read_only(str(sample_csv_file))

        container = ContainerInMemory()
        container.init(source)  # Sets READ_ONLY

        with pytest.raises(ValueError) as exc_info:
            container.add_empty_row()
        assert "Schreiboperation" in str(exc_info.value)

        source.close_object()

    def test_set_value_raises_in_read_only_mode(self, sample_csv_file: Path) -> None:
        """Test set_value raises in read-only mode."""
        from basic_framework.container_utils.text_file_as_table import TextFileAsTable

        source = TextFileAsTable()
        source.init_for_read_only(str(sample_csv_file))

        container = ContainerInMemory()
        container.init(source)

        with pytest.raises(ValueError) as exc_info:
            container.set_value(1, "name", "new_value")
        assert "Schreiboperation" in str(exc_info.value)

        source.close_object()

    def test_purge_memory_raises_in_read_only_mode(self, sample_csv_file: Path) -> None:
        """Test purge_memory raises in read-only mode."""
        from basic_framework.container_utils.text_file_as_table import TextFileAsTable

        source = TextFileAsTable()
        source.init_for_read_only(str(sample_csv_file))

        container = ContainerInMemory()
        container.init(source)

        with pytest.raises(ValueError) as exc_info:
            container.purge_memory()
        assert "Schreiboperation" in str(exc_info.value)

        source.close_object()

    def test_get_value_works_in_read_only_mode(self, sample_csv_file: Path) -> None:
        """Test get_value works in read-only mode."""
        from basic_framework.container_utils.text_file_as_table import TextFileAsTable

        source = TextFileAsTable()
        source.init_for_read_only(str(sample_csv_file))

        container = ContainerInMemory()
        container.init(source)

        # Read operations should work
        value = container.get_value(1, "name")
        assert value == "item1"

        source.close_object()


# =============================================================================
# Metadata Tests
# =============================================================================


class TestContainerInMemoryMetadata:
    """Tests for container metadata."""

    def test_get_condition_returns_none(self) -> None:
        """Test get_condition always returns None."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        assert container.get_condition() is None

    def test_get_object_returns_none(self) -> None:
        """Test get_object returns None."""
        container = ContainerInMemory()
        container.init_new(["col1"])
        container.add_empty_row()

        assert container.get_object(1) is None

    def test_pp_action_does_nothing(self) -> None:
        """Test pp_action does nothing (no error)."""
        container = ContainerInMemory()
        container.init_new(["col1"])

        # Should not raise
        container.pp_action()
