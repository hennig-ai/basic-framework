"""
MarkdownFileAsTable - Read-only container for markdown files with table
Thin wrapper around ContainerInMemory extracted from MarkdownDocument
"""

from typing import Optional, Any, Collection
from .abstract_container import AbstractContainer
from .abstract_iterator import AbstractIterator
from .container_in_memory import ContainerInMemory
from ..conditions.condition import Condition
from ..proc_frame import log_and_raise
from ..utils.markdown_document import MarkdownDocument


class MarkdownFileAsTable(AbstractContainer):
    """
    Read-only container that extracts the first table from a MarkdownDocument
    and delegates all AbstractContainer operations to the underlying ContainerInMemory.

    The MarkdownDocument must contain at least one table.
    """

    def __init__(self, markdown_doc: MarkdownDocument):
        """
        Initialize from a MarkdownDocument.
        Extracts the first table and uses it as data source.

        Args:
            markdown_doc: Parsed MarkdownDocument containing at least one table
        """

        self._markdown_doc: Optional[MarkdownDocument] = None
        self._container: Optional[ContainerInMemory] = None

        try:
            self._markdown_doc = markdown_doc

            # Find first table in the document tree
            # Tables are stored as KnotObjects with ContainerInMemory as content
            table_list = self._markdown_doc.create_table_dictionary()

            # Validierung: Genau eine Tabelle erwartet
            if len(table_list) != 1:
                log_and_raise(ValueError(f"init_for_read_only: Hierarchie-Dokument muss genau eine Tabelle enthalten, gefunden: {len(table_list)}"))

            # Hierarchie-Tabelle extrahieren (erstes Element aus Dictionary)
            self._container = list(table_list.values())[0]

        except Exception as e:
            log_and_raise(ValueError(f"Failed to initialize MarkdownFileAsTable: {e}"))

    # ============================================================================
    # AbstractContainer Interface - All methods delegate to ContainerInMemory
    # ============================================================================

    def create_iterator(self,
                        cols_from_target_must_exist_in_source: bool = True,
                        condition: Optional[Condition] = None) -> AbstractIterator:
        """Create an iterator - delegates to ContainerInMemory."""
        if self._container is None:
            log_and_raise("MarkdownFileAsTable not initialized")
        return self._container.create_iterator(
            cols_from_target_must_exist_in_source, condition)

    def iterator_is_empty(self, row: int) -> bool:
        """Check if iterator is at end - delegates to ContainerInMemory."""
        if self._container is None:
            return True
        return self._container.iterator_is_empty(row)

    def pp_action(self) -> None:
        """Move to next position - delegates to ContainerInMemory."""
        if self._container is not None:
            self._container.pp_action()

    def get_value(self, position: int, column: str) -> Any:
        """Get value at position - delegates to ContainerInMemory."""
        if self._container is None:
            return None
        return self._container.get_value(position, column)

    def set_value(self, position: int, column: str, value: Any) -> None:
        """Set value - NOT ALLOWED for read-only container."""
        log_and_raise("MarkdownFileAsTable is read-only. Cannot set values.")

    def field_exists(self, column: str) -> bool:
        """Check if field exists - delegates to ContainerInMemory."""
        if self._container is None:
            return False
        return self._container.field_exists(column)

    def get_list_of_fields_as_ref(self) -> Collection[str]:
        """Get list of fields - delegates to ContainerInMemory."""
        if self._container is None:
            return list[str]()
        return self._container.get_list_of_fields_as_ref()

    def get_condition(self) -> Optional[Condition]:
        """Get condition - delegates to ContainerInMemory."""
        if self._container is None:
            return None
        return self._container.get_condition()

    def object_is_nothing(self, position: int) -> bool:
        """Check if object is nothing - checks if position is valid."""
        if self._container is None:
            return True
        # Check if position exists in m_Rows
        return position not in self._container.m_Rows

    def get_object(self, row: int) -> Any:
        """Get object at row - delegates to ContainerInMemory."""
        if self._container is None:
            return None
        return self._container.get_object(row)

    def get_technical_container_name(self) -> str:
        """Get technical container name."""
        if self._markdown_doc is not None:
            return f"MarkdownTable from {self._markdown_doc.m_SourceFile}"
        return "MarkdownFileAsTable"

    def get_logical_container_name(self) -> str:
        """Get logical container name."""
        return self.get_technical_container_name()

    def get_file_name(self) -> str:
        """Get file name."""
        if self._markdown_doc is not None:
            return self._markdown_doc.m_SourceFile
        return ""

    # ============================================================================
    # Additional helper methods
    # ============================================================================

    def is_initialized(self) -> bool:
        """Check if container is properly initialized."""
        return self._container is not None

    def get_row_count(self) -> int:
        """Get number of rows in the table."""
        if self._container is None:
            return 0
        # ContainerInMemory tracks row count internally in m_Rows dictionary
        return len(self._container.m_Rows)

    def get_column_count(self) -> int:
        """Get number of columns in the table."""
        if self._container is None:
            return 0
        return len(self._container.get_list_of_fields_as_ref())
