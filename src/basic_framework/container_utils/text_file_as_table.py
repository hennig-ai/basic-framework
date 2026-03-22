"""
Text file as table implementation.

This module provides a concrete implementation of AbstractContainer
for CSV/text files with delimiter-separated values.
"""

import csv
from enum import Enum
from typing import Any, Collection, Dict, List, Optional, TextIO

from ..conditions.condition import Condition
from .abstract_iterator import AbstractIterator
from .abstract_container import AbstractContainer
from .static_container_basics import create_new_iterator
from ..utils.filename_utils import get_path_from_full_reference
from ..ext_filesystem import file_exists, file_must_exist, directory_must_exist
from ..proc_frame import log_and_raise, proc_frame_end


class TableAccessType(Enum):
    """Access type for text file operations."""
    PURGE_AND_WRITE = "purge_and_write"
    READ_ONLY = "read_only"


class TextFileAsTable(AbstractContainer):
    """
    Text file implementation of AbstractContainer.
    
    Supports reading from and writing to delimited text files,
    with column header management and iterator support.
    """

    def __init__(self):
        """Initialize the text file table."""
        self._file_with_path: str = ""
        self._file_handle: Optional[TextIO] = None
        self._csv_reader: Optional[csv.DictReader[str]] = None
        self._csv_writer: Optional[csv.DictWriter[str]] = None
        
        self._headers: Dict[str, int] = {}
        self._headers_as_ref: Optional[List[str]] = None
        self._access_type: Optional[TableAccessType] = None
        self._current_line: Dict[str, Any] = {}
        self._column_separator: str = ";"
        self._current_row_data: Dict[str, Any] = {}
        self._is_at_end: bool = False

    def _init(self, access_type: TableAccessType, file_with_path: str, column_separator: str = ";"):
        """
        Internal initialization method.
        
        Args:
            access_type: How to access the file
            file_with_path: Full path to text file
            column_separator: Column delimiter character
        """
        self._access_type = access_type
        self._file_with_path = file_with_path
        self._column_separator = column_separator
        self._headers = {}

        if access_type == TableAccessType.PURGE_AND_WRITE:
            # Create/overwrite file for writing
            if file_exists(file_with_path):
                # File will be overwritten
                pass
            
            # Ensure directory exists
            directory_must_exist(get_path_from_full_reference(file_with_path))
            
            # Open file for writing
            self._file_handle = open(file_with_path, 'w', newline='', encoding='utf-8')
            
        elif access_type == TableAccessType.READ_ONLY:
            # Open existing file for reading
            file_must_exist(file_with_path)
            self._file_handle = open(file_with_path, 'r', encoding='utf-8')
            
            # Create CSV reader
            self._csv_reader = csv.DictReader(self._file_handle, delimiter=column_separator)
            
            # Read headers
            if self._csv_reader.fieldnames:
                for i, col_name in enumerate(self._csv_reader.fieldnames):
                    self._headers[col_name] = i + 1
            
            # Read first row
            self.pp_action()

    def init_for_purge_and_write(self, file_with_path: str, headers: Collection[str], 
                                column_separator: str = ";"):
        """
        Initialize for writing mode with headers.
        
        Args:
            file_with_path: Full path to text file
            headers: Collection of column names
            column_separator: Column delimiter
        """
        self._init(TableAccessType.PURGE_AND_WRITE, file_with_path, column_separator)
        self.set_headers(headers)
        self._write_headers()

    def init_for_read_only(self, file_with_path: str, column_separator: str = ";"):
        """
        Initialize for reading mode.
        
        Args:
            file_with_path: Full path to text file
            column_separator: Column delimiter
        """
        if not file_exists(file_with_path):
            log_and_raise(f"Die Datei '{file_with_path}' existiert nicht.")
            return
            
        self._init(TableAccessType.READ_ONLY, file_with_path, column_separator)

    def set_headers(self, name_list: Collection[str]):
        """
        Set column headers with positions.
        
        Args:
            name_list: Collection of column names
        """
        i = 1
        for name in name_list:
            if name in self._headers:
                log_and_raise(f"In der Datei soll die Spalte '{name}' zweimal gesetzt werden. Bitte korrigieren.")
                proc_frame_end()
                return
            self._headers[name] = i
            i += 1

    def _write_headers(self):
        """Write header row to file."""
        if self._access_type != TableAccessType.PURGE_AND_WRITE:
            return
            
        if self._file_handle is None:
            log_and_raise("File handle is not initialized")
            return
            
        # Initialize CSV writer with headers
        header_names = sorted(self._headers.keys(), key=lambda k: self._headers[k])
        self._csv_writer = csv.DictWriter(
            self._file_handle,
            fieldnames=header_names,
            delimiter=self._column_separator
        )
        self._csv_writer.writeheader()

    def _validate_column(self, column: str):
        """
        Validate that column exists.
        
        Args:
            column: Column name to validate
        """
        if column not in self._headers:
            log_and_raise(f"Spalte '{column}' existiert nicht in der Datei. Abbruch.")
            raise ValueError(f"Column '{column}' does not exist")

    def close_object(self):
        """Close the file handle."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def truncate(self):
        """Truncate file and write headers again."""
        if self._access_type != TableAccessType.PURGE_AND_WRITE:
            log_and_raise("Truncate auf dafür nicht freigegebener Textdatei. Abbruch.")
            return
        
        # Close and reopen file
        if self._file_handle:
            self._file_handle.close()
        
        self._file_handle = open(self._file_with_path, 'w', newline='', encoding='utf-8')
        self._write_headers()

    # AbstractContainer implementation

    def pp_action(self) -> None:
        """Action performed when iterator moves forward."""
        if self._access_type == TableAccessType.PURGE_AND_WRITE:
            self._write_current_line()
        elif self._access_type == TableAccessType.READ_ONLY:
            self._current_line.clear()
            if self._csv_reader:
                try:
                    self._current_row_data = next(self._csv_reader)
                    self._is_at_end = False
                    # Convert to internal format
                    for col_name, value in self._current_row_data.items():
                        if col_name in self._headers:
                            self._current_line[col_name] = value
                except StopIteration:
                    self._is_at_end = True

    def _write_current_line(self):
        """Write current line data to file."""
        if self._csv_writer and self._current_line:
            # Ensure all columns have values
            row_data: Dict[str, Any] = {}
            for col_name in self._csv_writer.fieldnames:
                row_data[col_name] = self._current_line.get(col_name, "")
            self._csv_writer.writerow(row_data)

    def iterator_is_empty(self, row: int) -> bool:
        """Check if iterator is at end."""
        return self._is_at_end

    def get_object(self, row: int) -> Any:
        """Get object at row - not supported."""
        log_and_raise("Diese Methode ist in dieser Klasse nicht erlaubt.")
        return None

    def field_exists(self, column: str) -> bool:
        """Check if field exists."""
        return column in self._headers

    def get_value(self, position: int, column: str) -> Any:
        """Get value at position and column."""
        return self._col_value(position, column)

    def set_value(self, position: int, column: str, value: Any) -> None:
        """Set value at position and column."""
        self._set_col_value(position, column, value)

    def create_iterator(self, 
                       cols_from_target_must_exist_in_source: bool = True,
                       condition: Optional["Condition"] = None) -> "AbstractIterator":
        """Create iterator for this container."""
        return create_new_iterator(self, condition, cols_from_target_must_exist_in_source)

    def get_list_of_fields_as_ref(self) -> Collection[str]:
        """Get list of field names."""
        if self._headers_as_ref is None:
            self._headers_as_ref = list(self._headers.keys())
        return self._headers_as_ref

    def get_technical_container_name(self) -> str:
        """Get technical container name."""
        return self._file_with_path

    def get_file_name(self) -> str:
        """Get filename."""
        return self._file_with_path

    def get_logical_container_name(self) -> str:
        """Get logical container name."""
        return self.get_technical_container_name()

    def get_condition(self) -> Optional["Condition"]:
        """Get condition - always None for this implementation."""
        return None

    # Column value access methods

    def _col_value(self, position: int, column: str) -> Any:
        """
        Get column value at position.

        The legacy marker "##!empty!##" is converted to None for
        consistency with database NULL handling.
        """
        self._validate_column(column)
        value = self._current_line.get(column, "")
        if value == "##!empty!##":
            return None
        return value

    def _set_col_value(self, position: int, column: str, value: Any) -> None:
        """Set column value at position."""
        self._validate_column(column)
        self._current_line[column] = value

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close_object()


# Export the main class
__all__ = ['TextFileAsTable', 'TableAccessType']