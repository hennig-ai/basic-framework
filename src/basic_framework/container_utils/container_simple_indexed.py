"""
ContainerSimpleIndexed implementation - indexed container with non-unique keys.
"""

from typing import Any, Collection, Dict, List, Optional, Union, cast

from .abstract_container import AbstractContainer
from .abstract_iterator import AbstractIterator
from ..conditions.condition import Condition
from ..proc_frame import log_and_raise
from .static_container_basics import create_new_iterator

from .knot_object import KnotObject


class ContainerSimpleIndexed(AbstractContainer):
    """Container with simple (non-unique) indexing."""
    
    def __init__(self) -> None:
        self.m_oContainer: Optional[AbstractContainer] = None
        self.m_KeyFields: List[str] = []
        self.m_oRoot: KnotObject = KnotObject()
    
    def init(self, container: AbstractContainer, fields: Union[Collection[str], str, List[str]], 
             ignore_empty_rows: bool = False) -> None:
        """
        Initialize the indexed container.
        
        Args:
            container: Source container to index
            fields: Field(s) to use as index keys
            ignore_empty_rows: Whether to ignore rows with empty key fields
        """
        # Convert fields to list
        field_list: List[str] = []
        if isinstance(fields, str):
            field_list = [fields]
        elif isinstance(fields, (list, tuple)):
            field_list = list(fields)
        elif hasattr(fields, '__iter__'):
            field_list = list(fields)
        else:
            log_and_raise(f"{type(self).__name__}:Init : Feldlistenobjekt vom Typ {type(fields).__name__} kann nicht verarbeitet werden.")
        
        self.m_oContainer = container
        
        # Als erstes prüfen ob diese Liste an Feldern zulässig ist
        for key in field_list:
            if not self.m_oContainer.field_exists(str(key)):
                log_and_raise(f"Index kann nicht aufgebaut werden: das Feld '{key}' existiert nicht im Container '{self.m_oContainer.get_technical_container_name()}'")
        
        for key in field_list:
            self.m_KeyFields.append(str(key))
        
        self._init_index(ignore_empty_rows)
    
    def pp_action(self) -> None:
        """Perform post-position action."""
        if self.m_oContainer:
            self.m_oContainer.pp_action()
    
    def get_condition(self) -> Optional[Condition]:
        """Get condition from underlying container."""
        if self.m_oContainer:
            return self.m_oContainer.get_condition()
        return None
    
    def get_key_fields(self) -> List[str]:
        """Get a copy of key fields."""
        return self.m_KeyFields.copy()
    
    def get_key_fields_by_ref(self) -> List[str]:
        """Get key fields by reference."""
        return self.m_KeyFields
    
    def _init_index(self, ignore_empty_rows: bool) -> None:
        """Initialize the index structure."""
        self.m_oRoot.init("", "", None)
        
        if self.m_oContainer is None:
            log_and_raise("Container is not initialized")
            return
            
        iterator = self.m_oContainer.create_iterator()
        
        while not iterator.is_empty():
            self._create_index_entry(iterator, ignore_empty_rows)
            iterator.pp()
    
    def _key_fields_in_row_are_empty(self, iterator: AbstractIterator) -> bool:
        """Check if all key fields in current row are empty."""
        for field in self.m_KeyFields:
            if iterator.value(field) != "":
                return False
        return True
    
    def _create_index_entry(self, iterator: AbstractIterator, ignore_empty_rows: bool) -> None:
        """Create an index entry for current iterator position."""
        if ignore_empty_rows:
            if self._key_fields_in_row_are_empty(iterator):
                return
        
        where_to_look = self.m_oRoot
        field_count = len(self.m_KeyFields)
        
        for level in range(field_count):
            col = self.m_KeyFields[level]
            value = str(iterator.value(col))
            
            if level < field_count - 1:
                where_to_look = self._find_or_create(where_to_look, col, value)
            else:
                # Mit dem letzten Element wird der Schlüssel vollständig
                where_to_look = self._find_or_create(where_to_look, col, value, False)
                where_to_look.m_Leafs[iterator.position] = iterator.position
    
    def _find_or_create(self, parent_where_to_look: KnotObject, name: str, value: Any, 
                       mustnt_exist: bool = False) -> KnotObject:
        """Find or create a child node."""
        if parent_where_to_look.child_exists(value):
            if mustnt_exist:
                self._unique_key_error(parent_where_to_look.get_child(value))
        else:
            # Es gibt noch keinen Eintrag, also legen wir einen an
            knot = KnotObject()
            knot.init(name, value, parent_where_to_look)
        
        return parent_where_to_look.get_child(value)
    
    def _unique_key_error(self, parent_where_to_look: KnotObject) -> None:
        """Raise error for non-unique key."""
        msg = self._create_key_string(parent_where_to_look)
        container_name = self.m_oContainer.get_technical_container_name() if self.m_oContainer else "Unknown"
        log_and_raise(f"Fehler: Schlüssel für Container '{container_name}' ist nicht eindeutig, "
                 f"folgende Sequenz wurde ein zweites Mal gefunden:{msg}")
    
    def _create_key_string(self, knot: KnotObject) -> str:
        """Create a string representation of the key path."""
        if knot.m_oParent is not None:
            return self._create_key_string(knot.m_oParent) + f";'{knot.m_sName}'='{knot.m_vValue}'"
        else:
            return ""
    
    def unique_key_exists(self, key: Dict[str, Any]) -> bool:
        """Check if a unique key exists."""
        return self.get_row_for_unique_key(key) != -1
    
    def _get_knot_name_of_first_child(self, knot: KnotObject) -> str:
        """Get the name of the first child node."""
        children = knot.get_children()
        if children:
            first_child = list(children.values())[0]
            return first_child.m_sName
        return ""
    
    def get_row_for_unique_key(self, key: Dict[str, Any]) -> int:
        """
        Get row for unique key.
        
        Args:
            key: Dictionary of field names to values
            
        Returns:
            Row position or -1 if not found or not unique
        """
        return self._get_row_for_unique_key_intern(key, self.m_oRoot)
    
    def get_rows_for_key(self, key: Dict[str, Any]) -> Optional[List[int]]:
        """
        Get all rows matching the key.
        
        Args:
            key: Dictionary of field names to values
            
        Returns:
            List of row positions or None if not found
        """
        ret = self._get_rows_for_key_intern(key, self.m_oRoot)
        
        if ret is None or len(ret) == 0:
            return None
        
        return list(ret.keys())
    
    def _get_rows_for_key_intern(self, key: Dict[str, Any], look_here: KnotObject) -> Optional[Dict[int, int]]:
        """Internal method to get rows for key."""
        # Hat der Knoten keine Kinder mehr?
        if len(look_here.get_children()) == 0:
            return look_here.m_Leafs
        
        # Hole mir den Spaltenbezeichner
        key_field = self._get_knot_name_of_first_child(look_here)
        if key_field not in key:
            log_and_raise(f"Spalte '{key_field}' fehlt im übergebenen Key.")
        
        # Ich suche nun mit dem Wert in der Indexstruktur
        key_field_value = str(key[key_field])
        
        if look_here.child_exists(key_field_value):
            child = look_here.get_child(key_field_value)
            if key_field != child.m_sName:
                log_and_raise("Schwere Inkonsistenz in einer Indexstruktur. Überprüfen!")
            return self._get_rows_for_key_intern(key, child)
        else:
            return None
    
    def _get_row_for_unique_key_intern(self, key: Dict[str, Any], look_here: KnotObject) -> int:
        """Internal method to get row for unique key."""
        # Hat der Knoten keine Kinder mehr?
        if len(look_here.get_children()) == 0:
            if len(look_here.m_Leafs) == 1:
                return cast(int, list(look_here.m_Leafs.values())[0])
            else:
                return -1
        
        # Hole mir den Spaltenbezeichner
        key_field = self._get_knot_name_of_first_child(look_here)
        if key_field not in key:
            log_and_raise(f"Spalte '{key_field}' fehlt im übergebenen Key.")
        
        # Ich suche nun mit dem Wert in der Indexstruktur
        key_field_value = str(key[key_field])
        
        if look_here.child_exists(key_field_value):
            child = look_here.get_child(key_field_value)
            if key_field != child.m_sName:
                log_and_raise("Schwere Inkonsistenz in einer Indexstruktur. Überprüfen!")
            return self._get_row_for_unique_key_intern(key, child)
        else:
            return -1
    
    def release_memory(self) -> None:
        """Release memory by deconstructing the tree."""
        self.m_oRoot.deconstruct()
    
    # AbstractContainer implementation methods
    
    def iterator_is_empty(self, row: int) -> bool:
        """Check if iterator position is empty."""
        if self.m_oContainer:
            return self.m_oContainer.iterator_is_empty(row)
        return True
    
    def get_object(self, row: int) -> Any:
        """Get object at row."""
        if self.m_oContainer:
            return self.m_oContainer.get_object(row)
        return None
    
    def field_exists(self, column: str) -> bool:
        """Check if field exists."""
        if self.m_oContainer:
            return self.m_oContainer.field_exists(column)
        return False
    
    def get_value(self, position: int, column: str) -> Any:
        """Get value at position and column."""
        if self.m_oContainer:
            return self.m_oContainer.get_value(position, column)
        return None
    
    def set_value(self, position: int, column: str, value: Any) -> None:
        """Set value at position and column."""
        if self.m_oContainer:
            self.m_oContainer.set_value(position, column, value)
    
    def create_iterator(self, cols_from_target_must_exist_in_source: bool = True,
                       condition: Optional[Condition] = None) -> AbstractIterator:
        """Create iterator for this container."""
        return create_new_iterator(self, condition, cols_from_target_must_exist_in_source)
    
    def get_list_of_fields_as_ref(self) -> List[str]:
        """Get list of field names."""
        if self.m_oContainer:
            return list(self.m_oContainer.get_list_of_fields_as_ref())
        return []
    
    def get_technical_container_name(self) -> str:
        """Get technical container name."""
        if self.m_oContainer:
            return self.m_oContainer.get_technical_container_name()
        return ""
    
    def get_file_name(self) -> str:
        """Get file name."""
        if self.m_oContainer:
            return self.m_oContainer.get_file_name()
        return ""
    
    def get_logical_container_name(self) -> str:
        """Get logical container name."""
        if self.m_oContainer:
            return self.m_oContainer.get_logical_container_name()
        return ""