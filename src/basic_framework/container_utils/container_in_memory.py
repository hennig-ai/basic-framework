"""
ContainerInMemory implementation - in-memory data container.
"""

from enum import Enum
from typing import Any, Collection, Dict, List, Optional
from datetime import datetime

from .abstract_container import AbstractContainer
from .abstract_iterator import AbstractIterator
from ..conditions.condition import Condition
from ..proc_frame import log_and_raise
from .static_container_basics import create_new_iterator

from ..utils.basic_utils import convert_to_mapping


class TableAccessType(Enum):
    """Table access type enumeration."""
    READ_WRITE = 0
    READ_ONLY = 1


class ContainerInMemory(AbstractContainer):
    """In-memory container implementation."""
    
    def __init__(self) -> None:
        # Liste der Spaltenbezeichner
        self.m_Fields: Dict[str, str] = {}
        self.m_FieldsAsRef: Optional[List[str]] = None
        
        # Container für die Zeilen. Jede Zeile ist ein Dictionary
        self.m_Rows: Dict[int, Dict[str, Any]] = {}
        
        self.m_sTechName: str = ""
        self.m_sFileName: str = ""
        self.m_sLogicalName: str = ""
        
        # Legt fest dass in diese Tabelle nicht geschrieben werden darf
        self.m_eAccType: TableAccessType = TableAccessType.READ_WRITE
    
    def init(self, container: AbstractContainer) -> None:
        """
        Initialize from another container.

        Args:
            container: Source container to copy from
        """
        # Spaltenbezeichner übernehmen
        self.m_Fields = convert_to_mapping(container.get_list_of_fields_as_ref())

        # Iterator erstellen
        iterator = container.create_iterator()
        row_index = 1

        while not iterator.is_empty():
            # Zeile anlegen
            row: Dict[str, Any] = {}
            # Werte hinzufügen
            for field in self.m_Fields.keys():
                row[field] = iterator.value(field)
            # Nun Zeile hinzufügen
            self.m_Rows[row_index] = row
            row_index += 1
            # Nächste Position
            iterator.pp()

        # Metadaten übernehmen
        self.m_sTechName = container.get_technical_container_name()
        self.m_sFileName = container.get_file_name()
        self.m_sLogicalName = container.get_logical_container_name()

        self.m_eAccType = TableAccessType.READ_ONLY
    
    def init_new(self, headers: Collection[str], tech_name: str = "", logical_name: str = "") -> None:
        """
        Initialize new empty container.
        
        Args:
            headers: Collection of column headers
            tech_name: Technical name (optional)
            logical_name: Logical name (optional)
        """
        # Header setzen
        self.m_Fields = convert_to_mapping(headers)
        
        self.m_sFileName = f"Memory:{datetime.now()}"
        
        if tech_name == "":
            self.m_sTechName = self.m_sFileName
            self.m_sLogicalName = self.m_sFileName
        else:
            self.m_sTechName = tech_name
            self.m_sLogicalName = logical_name
        
        self.m_eAccType = TableAccessType.READ_WRITE
    
    def _validate_write(self) -> None:
        """Validate that write operations are allowed."""
        if self.m_eAccType != TableAccessType.READ_WRITE:
            log_and_raise("Schreiboperation ist laut internen Typ nicht erlaubt.")
    
    def add_empty_row(self) -> int:
        """
        Add an empty row to the container.
        
        Returns:
            Row index of the new row
        """
        self._validate_write()
        
        row: Dict[str, Any] = {}
        # Werte hinzufügen
        for field in self.m_Fields.keys():
            row[field] = None
        # Nun Zeile hinzufügen
        row_index = len(self.m_Rows) + 1
        self.m_Rows[row_index] = row
        return row_index
    
    def purge_memory(self) -> None:
        """Clear all data from memory."""
        self._validate_write()
        
        for key in list(self.m_Rows.keys()):
            row = self.m_Rows[key]
            row.clear()
        self.m_Rows.clear()
    
    # AbstractContainer implementation methods
    
    def iterator_is_empty(self, row: int) -> bool:
        """Check if iterator position is empty."""
        return row not in self.m_Rows
    
    def get_object(self, row: int) -> Any:
        """Get object at row (not implemented in original)."""
        return None
    
    def field_exists(self, column: str) -> bool:
        """Check if field exists."""
        return column in self.m_Fields
    
    def _validate_col(self, col: str) -> None:
        """Validate that column exists."""
        if col not in self.m_Fields:
            log_and_raise(f"Spalte '{col}' existiert nicht im Memory-Container. Abbruch.")
    
    def get_value(self, position: int, column: str) -> Any:
        """
        Get value at position and column.

        Args:
            position: Row position (1-based)
            column: Column name

        Returns:
            Value at the specified position (None for NULL values)
        """
        if position > len(self.m_Rows):
            log_and_raise(f"Unzulässige Iteratorposition '{position}'.")

        row = self.m_Rows[position]
        self._validate_col(column)

        return row[column]
    
    def set_value(self, position: int, column: str, value: Any) -> None:
        """
        Set value at position and column.

        Args:
            position: Row position (1-based)
            column: Column name
            value: Value to set
        """
        self._validate_write()

        if position > len(self.m_Rows):
            # Add empty row if position doesn't exist
            self.add_empty_row()

        self._validate_col(column)
        row = self.m_Rows[position]
        row[column] = value
    
    def create_iterator(self, cols_from_target_must_exist_in_source: bool = True, 
                       condition: Optional[Condition] = None) -> AbstractIterator:
        """Create iterator for this container."""
        return create_new_iterator(self, condition, cols_from_target_must_exist_in_source)
    
    def get_list_of_fields_as_ref(self) -> List[str]:
        """Get list of field names."""
        if self.m_FieldsAsRef is None:
            self.m_FieldsAsRef = list(self.m_Fields.keys())
        return self.m_FieldsAsRef
    
    def get_technical_container_name(self) -> str:
        """Get technical container name."""
        return self.m_sTechName
    
    def get_file_name(self) -> str:
        """Get file name."""
        return self.m_sFileName
    
    def get_logical_container_name(self) -> str:
        """Get logical container name."""
        return self.m_sLogicalName
    
    def get_condition(self) -> Optional[Condition]:
        """Get condition (always None for in-memory container)."""
        return None
    
    def pp_action(self) -> None:
        """Perform post-position action (empty for in-memory container)."""
        pass