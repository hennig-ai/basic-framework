"""
Unit tests for TextFileAsTable class.

Tests for:
- Reading CSV files
- Writing CSV files
- Iterator functionality
- Field access
"""

import os
from pathlib import Path

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"

from basic_framework.container_utils.text_file_as_table import (
    TextFileAsTable,
    TableAccessType,
)
from basic_framework.conditions.condition_equals import ConditionEquals


# =============================================================================
# Reading Tests
# =============================================================================


class TestTextFileAsTableReading:
    """Tests for reading CSV files."""

    def test_init_for_read_only(self, sample_csv_file: Path) -> None:
        """Test initializing for read-only mode."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))
        assert table is not None

    def test_read_headers(self, sample_csv_file: Path) -> None:
        """Test that headers are read correctly."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        fields = table.get_list_of_fields_as_ref()
        assert "name" in fields
        assert "value" in fields
        assert "status" in fields

    def test_field_exists(self, sample_csv_file: Path) -> None:
        """Test field_exists method."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        assert table.field_exists("name") is True
        assert table.field_exists("value") is True
        assert table.field_exists("nonexistent") is False

    def test_read_first_row(self, sample_csv_file: Path) -> None:
        """Test reading first data row."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        # First row should be loaded after init
        assert table.iterator_is_empty(0) is False
        value = table.get_value(0, "name")
        assert value == "item1"

    def test_iterate_all_rows(self, sample_csv_file: Path) -> None:
        """Test iterating through all rows."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        rows_read = 0
        names = []

        while not table.iterator_is_empty(0):
            names.append(table.get_value(0, "name"))
            rows_read += 1
            table.pp_action()

        assert rows_read == 3
        assert names == ["item1", "item2", "item3"]

    def test_read_nonexistent_file_raises(self, temp_dir: Path) -> None:
        """Test that reading non-existent file raises error."""
        table = TextFileAsTable()
        nonexistent = temp_dir / "nonexistent.csv"

        with pytest.raises(ValueError) as exc_info:
            table.init_for_read_only(str(nonexistent))
        assert "existiert nicht" in str(exc_info.value)

    def test_read_empty_file(self, empty_csv_file: Path) -> None:
        """Test reading file with only headers."""
        table = TextFileAsTable()
        table.init_for_read_only(str(empty_csv_file))

        # Should have headers but no data rows
        assert table.field_exists("name") is True
        assert table.iterator_is_empty(0) is True

    def test_get_technical_container_name(self, sample_csv_file: Path) -> None:
        """Test get_technical_container_name returns file path."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        name = table.get_technical_container_name()
        assert str(sample_csv_file) == name

    def test_get_file_name(self, sample_csv_file: Path) -> None:
        """Test get_file_name returns file path."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        assert table.get_file_name() == str(sample_csv_file)


# =============================================================================
# Writing Tests
# =============================================================================


class TestTextFileAsTableWriting:
    """Tests for writing CSV files."""

    def test_init_for_purge_and_write(self, temp_dir: Path) -> None:
        """Test initializing for write mode."""
        output_file = temp_dir / "output.csv"

        table = TextFileAsTable()
        table.init_for_purge_and_write(
            str(output_file),
            headers=["col1", "col2", "col3"]
        )

        assert output_file.exists()
        table.close_object()

    def test_write_headers(self, temp_dir: Path) -> None:
        """Test that headers are written correctly."""
        output_file = temp_dir / "headers.csv"

        table = TextFileAsTable()
        table.init_for_purge_and_write(
            str(output_file),
            headers=["name", "value"]
        )
        table.close_object()

        content = output_file.read_text()
        assert "name" in content
        assert "value" in content

    def test_write_data_row(self, temp_dir: Path) -> None:
        """Test writing a data row."""
        output_file = temp_dir / "data.csv"

        table = TextFileAsTable()
        table.init_for_purge_and_write(
            str(output_file),
            headers=["name", "value"]
        )

        # Set values and advance to write
        table.set_value(0, "name", "test_name")
        table.set_value(0, "value", "test_value")
        table.pp_action()  # Writes the row

        table.close_object()

        content = output_file.read_text()
        assert "test_name" in content
        assert "test_value" in content

    def test_write_multiple_rows(self, temp_dir: Path) -> None:
        """Test writing multiple rows."""
        output_file = temp_dir / "multi.csv"

        table = TextFileAsTable()
        table.init_for_purge_and_write(
            str(output_file),
            headers=["id", "name"]
        )

        for i in range(3):
            table.set_value(0, "id", str(i + 1))
            table.set_value(0, "name", f"item{i + 1}")
            table.pp_action()

        table.close_object()

        content = output_file.read_text()
        assert "item1" in content
        assert "item2" in content
        assert "item3" in content

    def test_duplicate_header_raises(self, temp_dir: Path) -> None:
        """Test that duplicate headers raise error."""
        output_file = temp_dir / "dup.csv"

        table = TextFileAsTable()

        try:
            with pytest.raises(ValueError) as exc_info:
                table.init_for_purge_and_write(
                    str(output_file),
                    headers=["name", "value", "name"]  # Duplicate!
                )
            assert "zweimal" in str(exc_info.value)
        finally:
            # Ensure file handle is closed even if exception occurred
            try:
                table.close_object()
            except Exception:
                pass

    def test_truncate(self, temp_dir: Path) -> None:
        """Test truncate functionality."""
        output_file = temp_dir / "truncate.csv"

        table = TextFileAsTable()
        table.init_for_purge_and_write(
            str(output_file),
            headers=["name"]
        )

        # Write some data
        table.set_value(0, "name", "data1")
        table.pp_action()
        table.set_value(0, "name", "data2")
        table.pp_action()

        # Truncate
        table.truncate()
        table.close_object()

        # File should only have headers
        content = output_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Only header


# =============================================================================
# Iterator Tests
# =============================================================================


class TestTextFileAsTableIterator:
    """Tests for iterator functionality."""

    def test_create_iterator(self, sample_csv_file: Path) -> None:
        """Test creating an iterator."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        iterator = table.create_iterator()
        assert iterator is not None

    def test_iterator_not_empty_on_data(self, sample_csv_file: Path) -> None:
        """Test that iterator is not empty when file has data."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        iterator = table.create_iterator()
        assert iterator.is_empty() is False

    def test_iterator_value_access(self, sample_csv_file: Path) -> None:
        """Test accessing values through iterator."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        iterator = table.create_iterator()

        # First item
        assert iterator.value("name") == "item1"
        assert iterator.value("value") == "100"
        assert iterator.value("status") == "active"


# =============================================================================
# Column Validation Tests
# =============================================================================


class TestTextFileAsTableValidation:
    """Tests for column validation."""

    def test_get_value_invalid_column_raises(self, sample_csv_file: Path) -> None:
        """Test that invalid column raises error."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        try:
            with pytest.raises(ValueError) as exc_info:
                table.get_value(0, "nonexistent_column")
            assert "existiert nicht" in str(exc_info.value)
        finally:
            table.close_object()

    def test_set_value_invalid_column_raises(self, temp_dir: Path) -> None:
        """Test that setting invalid column raises error."""
        output_file = temp_dir / "test.csv"

        table = TextFileAsTable()
        table.init_for_purge_and_write(
            str(output_file),
            headers=["name", "value"]
        )

        try:
            with pytest.raises(ValueError) as exc_info:
                table.set_value(0, "nonexistent", "test")
            assert "existiert nicht" in str(exc_info.value)
        finally:
            table.close_object()


# =============================================================================
# Custom Separator Tests
# =============================================================================


class TestTextFileAsTableSeparator:
    """Tests for custom column separator."""

    def test_comma_separator(self, temp_dir: Path) -> None:
        """Test using comma as separator."""
        csv_file = temp_dir / "comma.csv"
        csv_file.write_text("name,value\ntest,123\n")

        table = TextFileAsTable()
        table.init_for_read_only(str(csv_file), column_separator=",")

        assert table.get_value(0, "name") == "test"
        assert table.get_value(0, "value") == "123"

    def test_tab_separator(self, temp_dir: Path) -> None:
        """Test using tab as separator."""
        tsv_file = temp_dir / "data.tsv"
        tsv_file.write_text("name\tvalue\ntest\t456\n")

        table = TextFileAsTable()
        table.init_for_read_only(str(tsv_file), column_separator="\t")

        assert table.get_value(0, "name") == "test"
        assert table.get_value(0, "value") == "456"

    def test_write_with_custom_separator(self, temp_dir: Path) -> None:
        """Test writing with custom separator."""
        output_file = temp_dir / "custom.csv"

        table = TextFileAsTable()
        table.init_for_purge_and_write(
            str(output_file),
            headers=["a", "b"],
            column_separator="|"
        )

        table.set_value(0, "a", "x")
        table.set_value(0, "b", "y")
        table.pp_action()
        table.close_object()

        content = output_file.read_text()
        assert "|" in content


# =============================================================================
# Cleanup Tests
# =============================================================================


class TestTextFileAsTableCleanup:
    """Tests for resource cleanup."""

    def test_close_object(self, sample_csv_file: Path) -> None:
        """Test close_object method."""
        table = TextFileAsTable()
        table.init_for_read_only(str(sample_csv_file))

        # Should not raise
        table.close_object()

        # Double close should not raise
        table.close_object()

    def test_destructor_closes_file(self, temp_dir: Path) -> None:
        """Test that destructor closes file handle."""
        output_file = temp_dir / "destructor.csv"

        def create_and_destroy():
            table = TextFileAsTable()
            table.init_for_purge_and_write(
                str(output_file),
                headers=["test"]
            )
            # table goes out of scope here

        create_and_destroy()

        # File should be readable (not locked)
        content = output_file.read_text()
        assert "test" in content
