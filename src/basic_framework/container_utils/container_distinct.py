"""
ContainerDistinct implementation - distinct values container with grouping.
"""

from enum import Enum
from typing import Any, Collection, Dict, List, Optional

from .abstract_container import AbstractContainer
from .abstract_iterator import AbstractIterator
from ..conditions.condition import Condition
from ..proc_frame import log_and_raise
from .static_container_basics import create_new_iterator

from .knot_object import KnotObject
from ..utils.basic_utils import convert_to_mapping


class GroupResultType(Enum):
    """Group result type enumeration."""
    GROUP_RESULT_IS_SUM = 1
    GROUP_RESULT_IS_COUNT = 2


class ContainerDistinct(AbstractContainer):
    """Container for distinct values with grouping and aggregation."""
    
    # Constants
    C_ROW_ID = "RowID"
    C_GROUP_RESULTS = "GroupResults"
    
    def __init__(self) -> None:
        self.m_oContainer: Optional[AbstractContainer] = None
        self.m_oRoot: KnotObject = KnotObject()
        self.m_Index: List[KnotObject] = []
        self.m_bDeconstructed: bool = False
        self.m_FieldList: Dict[str, str] = {}
        self.m_FieldsAsRef: Optional[List[str]] = None
        self.m_GroupFields: List[str] = []
        self.m_ResultDef: Optional[Dict[str, int]] = None
        self.m_oCondition: Optional[Condition] = None
    
    def init(self, container: AbstractContainer, group_fields: Collection[str], 
             result_def: Optional[Dict[str, int]] = None, 
             condition: Optional[Condition] = None) -> None:
        """
        Initialize the distinct container.
        
        Args:
            container: Source container
            group_fields: Fields to group by
            result_def: Result definition for aggregations
            condition: Optional filter condition
        """
        self.m_oContainer = container
        self.m_oCondition = condition
        
        # FeldListe aufbauen
        for field in group_fields:
            self.m_GroupFields.append(field)
            self.m_FieldList[field] = field
        
        group_fields_m = convert_to_mapping(self.m_GroupFields)
        
        if result_def is not None:
            self.m_ResultDef = {}
            for key, value in result_def.items():
                if key in group_fields_m:
                    log_and_raise(f"DistinctContainer.Init: Feld '{key}' kann nicht Gruppierungsfeld und Ergebnisfeld gleichzeitig sein.")
                self.m_FieldList[key] = key
                self._validate_result_type(value)
                self.m_ResultDef[key] = value
        
        self._init_index()
    
    def pp_action(self) -> None:
        """Perform post-position action."""
        if self.m_oContainer:
            self.m_oContainer.pp_action()
    
    def release_memory(self) -> None:
        """Release memory by deconstructing the tree."""
        self.m_oRoot.deconstruct()
        for obj in self.m_Index:
            obj.deconstruct()
        self.m_Index.clear()
        self.m_bDeconstructed = True
    
    def _validate_result_type(self, value: Any) -> None:
        """Validate that the result type is valid."""
        if not isinstance(value, int):
            log_and_raise(f"{type(self).__name__}.ValidateResultType: Als GroupResultType wurde der unzulässige Wert '{value}' übergeben.")
        
        if value not in [GroupResultType.GROUP_RESULT_IS_SUM.value, GroupResultType.GROUP_RESULT_IS_COUNT.value]:
            log_and_raise(f"{type(self).__name__}.ValidateResultType: Als GroupResultType wurde der unzulässige Wert '{value}' übergeben.")
    
    def _init_index(self) -> None:
        """Initialize the index structure."""
        self.m_oRoot.init("", "", None)
        
        if self.m_oContainer is None:
            log_and_raise("Container is not initialized")
            return
            
        iterator = create_new_iterator(self.m_oContainer, self.m_oCondition)
        while not iterator.is_empty():
            self._create_distinct_entry(iterator)
            iterator.pp()
            iterator.write_pp_message(f"{type(self).__name__}: Indexaufbau")
        
        self.m_bDeconstructed = False
    
    def _must_not_be_deconstructed(self) -> None:
        """Check that the index has not been deconstructed."""
        if self.m_bDeconstructed:
            log_and_raise(f"{type(self).__name__}:GetValidRoot: Interne Indexstruktur wurde bereits abgebaut.")
    
    def find_distinct_results(self, key_list: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find distinct results for given keys.
        
        Args:
            key_list: Dictionary of field names to values
            
        Returns:
            Dictionary of results or None if not found
        """
        self._must_not_be_deconstructed()
        
        where_to_look = self.m_oRoot
        field_count = len(self.m_GroupFields)
        
        for level in range(field_count):
            col = self.m_GroupFields[level]
            value = str(key_list[col])
            if where_to_look.child_exists(value):
                where_to_look = where_to_look.get_child(value)
            else:
                return None
        
        return where_to_look.m_Leafs.get(self.C_GROUP_RESULTS)
    
    def _find(self, parent_where_to_look: KnotObject, name: str, value: Any) -> Optional[KnotObject]:
        """Find a child node."""
        if parent_where_to_look.child_exists(value):
            return parent_where_to_look.get_child(value)
        else:
            return None
    
    def _create_distinct_entry(self, iterator: AbstractIterator) -> None:
        """Create a distinct entry from iterator position."""
        self._must_not_be_deconstructed()
        
        where_to_look = self.m_oRoot
        field_count = len(self.m_GroupFields)
        
        for level in range(field_count):
            col = self.m_GroupFields[level]
            value = str(iterator.value(col))
            
            if level < field_count - 1:
                where_to_look = self._find_or_create(where_to_look, col, value)
            else:
                # Mit dem letzten Element wird der Schlüssel vollständig
                where_to_look = self._find_or_create(where_to_look, col, value)
                if len(where_to_look.m_Leafs) == 0:
                    # Legen wir diesen Eintrag das erste Mal an?
                    where_to_look.m_Leafs[self.C_ROW_ID] = iterator.position
                    self.m_Index.append(where_to_look)
                
                # Falls ich Gruppierungsergebnisse bilden soll
                self._build_results(iterator, where_to_look.m_Leafs)
    
    def _build_results(self, iterator: AbstractIterator, leafs: Dict[str, Any]) -> None:
        """Build aggregation results."""
        # Sollen keine Ergebnisse gebildet werden?
        if self.m_ResultDef is None:
            return
        
        # Falls es keine Ergebnisliste gibt, initial aufbauen
        if self.C_GROUP_RESULTS not in leafs:
            results: Dict[str, Any] = {}
            leafs[self.C_GROUP_RESULTS] = results
            for def_key in self.m_ResultDef.keys():
                results[def_key] = ""
        else:
            results = leafs[self.C_GROUP_RESULTS]
        
        # Nun schleife ich durch alle Resultfelder
        for def_key, result_type in self.m_ResultDef.items():
            col_val = iterator.value(def_key)
            
            if result_type == GroupResultType.GROUP_RESULT_IS_SUM.value:
                if str(col_val) != "":
                    # Der Wert muss numerisch sein
                    try:
                        num_val = float(col_val)
                    except (ValueError, TypeError):
                        log_and_raise(f"DistinctContainer.BuildResults: Das Feld '{def_key}' an der Position {iterator.position} "
                                f"enthält den nichtnumerischen Wert '{col_val}'.")
                        num_val = 0.0  # Set default value if conversion fails
                    
                    current_result = results[def_key]
                    if str(current_result) == "":
                        d_result = 0.0
                    else:
                        d_result = float(current_result)
                    
                    d_result += num_val
                    results[def_key] = d_result
            
            elif result_type == GroupResultType.GROUP_RESULT_IS_COUNT.value:
                current_result = results[def_key]
                if str(current_result) == "":
                    d_result = 0.0
                else:
                    d_result = float(current_result)
                
                d_result += 1
                results[def_key] = d_result
            
            else:
                log_and_raise(f"{type(self).__name__}.BuildResults: Unbekannter Gruppierungstyp '{result_type}'.")
    
    def _find_or_create(self, parent_where_to_look: KnotObject, name: str, value: Any) -> KnotObject:
        """Find or create a child node."""
        if not parent_where_to_look.child_exists(value):
            # Es gibt noch keinen Eintrag, also legen wir einen an
            knot = KnotObject()
            knot.init(name, value, parent_where_to_look)
        
        return parent_where_to_look.get_child(value)
    
    # AbstractContainer implementation methods
    
    def iterator_is_empty(self, row: int) -> bool:
        """Check if iterator position is empty."""
        self._must_not_be_deconstructed()
        return row > len(self.m_Index)
    
    def get_object(self, row: int) -> Any:
        """Get object at row."""
        self._must_not_be_deconstructed()
        return self.m_Index[row - 1]  # Convert to 0-based index
    
    def field_exists(self, column: str) -> bool:
        """Check if field exists."""
        self._must_not_be_deconstructed()
        return column in self.m_FieldList
    
    def get_value(self, position: int, column: str) -> Any:
        """Get value at position and column."""
        self._must_not_be_deconstructed()
        
        knot = self.m_Index[position - 1]  # Convert to 0-based index
        
        if self.m_ResultDef is not None:
            if column in self.m_ResultDef:
                return knot.m_Leafs[self.C_GROUP_RESULTS][column]
        
        return knot.get_value(column)
    
    def set_value(self, position: int, column: str, value: Any) -> None:
        """Set value (not implemented for distinct container)."""
        pass
    
    def create_iterator(self, cols_from_target_must_exist_in_source: bool = True,
                       condition: Optional[Condition] = None) -> AbstractIterator:
        """Create iterator for this container."""
        self._must_not_be_deconstructed()
        return create_new_iterator(self, condition, cols_from_target_must_exist_in_source)
    
    def get_list_of_fields_as_ref(self) -> List[str]:
        """Get list of field names."""
        self._must_not_be_deconstructed()
        
        if self.m_FieldsAsRef is None:
            self.m_FieldsAsRef = list(self.m_FieldList.keys())
        return self.m_FieldsAsRef
    
    def get_technical_container_name(self) -> str:
        """Get technical container name."""
        self._must_not_be_deconstructed()
        if self.m_oContainer:
            return self.m_oContainer.get_technical_container_name()
        return ""
    
    def get_file_name(self) -> str:
        """Get file name."""
        self._must_not_be_deconstructed()
        if self.m_oContainer:
            return self.m_oContainer.get_file_name()
        return ""
    
    def get_logical_container_name(self) -> str:
        """Get logical container name."""
        self._must_not_be_deconstructed()
        if self.m_oContainer:
            return self.m_oContainer.get_logical_container_name()
        return ""
    
    def get_condition(self) -> Optional[Condition]:
        """Get condition (always None for distinct container)."""
        return None