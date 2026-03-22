"""
KnotObject implementation - tree node structure.
"""

from typing import Any, Dict, Optional
from ..proc_frame import log_and_raise


class KnotObject:
    """Tree node implementation with parent-child relationships.

    Provides hierarchical data structure with automatic ID generation,
    parent-child navigation, and value lookup through the tree hierarchy.
    Supports leaf storage and recursive tree operations.
    """
    
    def __init__(self) -> None:
        """Initialize an empty knot object.

        Creates uninitialized node with default values. Call init() to properly
        set up the node with name, value, and parent relationships.
        """
        self.m_sName: str = ""
        self.m_vValue: Any = None
        self.m_nLevel: int = 0
        self.m_oParent: Optional['KnotObject'] = None
        self.m_children: Dict[Any, 'KnotObject'] = {}
        self.m_Leafs: Dict[Any, Any] = {}
        self._initialized: bool = False
        self._id_counter: int = 0
    
    def init(self, name: str, value: Any, parent: Optional['KnotObject']) -> None:
        """
        Initialize the knot object.
        
        Args:
            name: Name of the node
            value: Value of the node
            parent: Parent node (can be None for root)
        """
        if self._initialized:
            log_and_raise(f"Init: Der Knoten mit dem Namen '{name}' und dem Wert '{value}' sollte zweimal initialisiert werden.")
        
        self._initialized = True
        self.m_sName = name
        
        # Automatic ID generation for empty string values
        if isinstance(value, str):
            if value.strip() == "":
                self._id_counter += 1
                self.m_vValue = f"{self.m_sName}_AutoID_{self._id_counter}"
            else:
                self.m_vValue = value
        else:
            self.m_vValue = value
        
        self.m_children = {}
        self.m_Leafs = {}
        
        self.set_parent(parent)
    
    def get_name(self) -> str:
        """Get the name of the node.

        Returns:
            str: The node's name identifier.
        """
        return self.m_sName
    
    def set_parent(self, parent: Optional['KnotObject']) -> None:
        """
        Set the parent node.
        
        Args:
            parent: Parent node (None for root)
        """
        self.m_oParent = parent
        if self.m_oParent is None:
            self.m_nLevel = 0  # Root node level
        else:
            # Calculate level based on parent's level
            self.m_nLevel = self.m_oParent.m_nLevel + 1
            # Ensure no duplicate children in parent
            if self.m_oParent.child_exists(self.m_vValue):
                log_and_raise("Fehler bei Aufbau des Baumes! Kind existiert schon.")
            # Register this node as child of parent
            self.m_oParent.add_child(self.m_vValue, self)
    
    def get_parent(self) -> 'KnotObject':
        """
        Get the parent node.
        
        Returns:
            Parent node
            
        Raises:
            ValueError: If no parent exists
        """
        if self.m_oParent is None:
            log_and_raise(f"GetParent: das Objekt '{self.m_sName}' hat keinen Vater.")
            raise ValueError("No parent exists")  # This line will never be reached due to log_and_raise
        return self.m_oParent
    
    def add_child(self, key: Any, obj: 'KnotObject') -> None:
        """
        Add a child node.
        
        Args:
            key: Key for the child
            obj: Child node object
        """
        # Prevent duplicate keys in children collection
        if key in self.m_children:
            log_and_raise(f"Init: Der Knoten mit dem Namen '{self.m_sName}' und dem Wert '{self.m_vValue}' enthält bereits ein Kind mit dem Schlüsselwert '{key}'.")
        self.m_children[key] = obj
    
    def child_exists(self, key: Any) -> bool:
        """
        Check if a child exists.
        
        Args:
            key: Key to check
            
        Returns:
            True if child exists
        """
        return key in self.m_children
    
    def child_must_exist(self, key: Any) -> None:
        """
        Ensure a child exists, raise error if not.
        
        Args:
            key: Key to check
        """
        # Validate required child existence
        if not self.child_exists(key):
            log_and_raise(f"Init: Der Knoten mit dem Namen '{self.m_sName}' und dem Wert '{self.m_vValue}' muss ein Kind mit dem Schlüsselwert '{key}' enthalten, tut es aber nicht.")
    
    def get_child(self, key: Any) -> 'KnotObject':
        """
        Get a child node.
        
        Args:
            key: Key of the child
            
        Returns:
            Child node
        """
        self.child_must_exist(key)  # Validate child exists
        return self.m_children[key]
    
    def get_children(self) -> Dict[Any, 'KnotObject']:
        """
        Get all children.
        
        Returns:
            Dictionary of children
        """
        return self.m_children
    
    def deconstruct(self) -> None:
        """Recursively deconstruct the tree and free memory.

        Traverses all child nodes and calls deconstruct on them,
        then clears all collections. Use this for cleanup when
        the tree is no longer needed.
        """
        # Recursively deconstruct all children first
        for key in list(self.m_children.keys()):
            obj = self.m_children[key]
            obj.deconstruct()  # Depth-first cleanup
        # Clear collections after children are cleaned up
        self.m_children.clear()
        self.m_Leafs.clear()
    
    def get_value(self, name: str) -> Any:
        """
        Get value by field name, searching up the tree.
        
        Args:
            name: Field name to search for
            
        Returns:
            Value for the field
        """
        # Check if this node matches the requested field name
        if self.m_sName == name:
            return self.m_vValue
        else:
            # Recursively search up the tree hierarchy
            if self.m_oParent is None:
                log_and_raise(f"Im vorliegenden Baum gibt es keine Wert für das Feld '{name}'.")
            else:
                return self.m_oParent.get_value(name)  # Bubble up to parent