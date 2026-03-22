"""
Abstract container base class.

This module provides the abstract base class for container implementations
that support iteration, field access, and condition filtering.
"""

from abc import ABC, abstractmethod
from typing import Any, Collection, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .abstract_iterator import AbstractIterator
from ..conditions.condition import Condition


class AbstractContainer(ABC):
    """
    Abstract base class for container implementations.
    
    Provides interface for data containers that support:
    - Iterator creation with optional conditions
    - Field-based data access by position and column
    - Metadata about container structure and naming
    """

    @abstractmethod
    def iterator_is_empty(self, row: int) -> bool:
        """
        Check if iterator position is beyond container bounds.
        
        Args:
            row: Row position to check (1-based)
            
        Returns:
            True if position is empty/beyond bounds
        """
        pass

    @abstractmethod
    def get_object(self, row: int) -> Any:
        """
        Get object at specific row position.
        
        Args:
            row: Row position (1-based)
            
        Returns:
            Object at the specified position
        """
        pass

    @abstractmethod
    def field_exists(self, column: str) -> bool:
        """
        Check if field/column exists in container.
        
        Args:
            column: Column name to check
            
        Returns:
            True if field exists
        """
        pass

    @abstractmethod
    def get_value(self, position: int, column: str) -> Any:
        """
        Get value at specific position and column.
        
        Args:
            position: Row position (1-based)
            column: Column name
            
        Returns:
            Value at the specified position and column
        """
        pass

    @abstractmethod
    def set_value(self, position: int, column: str, value: Any) -> None:
        """
        Set value at specific position and column.
        
        Args:
            position: Row position (1-based)  
            column: Column name
            value: Value to set
        """
        pass

    @abstractmethod
    def create_iterator(self, 
                       cols_from_target_must_exist_in_source: bool = True,
                       condition: Optional["Condition"] = None) -> "AbstractIterator":
        """
        Create iterator for this container.
        
        Args:
            cols_from_target_must_exist_in_source: Whether columns must exist
            condition: Optional condition for filtering
            
        Returns:
            New iterator instance
        """
        pass

    @abstractmethod
    def get_list_of_fields_as_ref(self) -> Collection[str]:
        """
        Get list of field names in container.
        
        Returns:
            Collection of field names
        """
        pass

    @abstractmethod
    def get_technical_container_name(self) -> str:
        """
        Get technical name of container.
        
        Returns:
            Technical container name
        """
        pass

    @abstractmethod
    def get_file_name(self) -> str:
        """
        Get filename associated with container.
        
        Returns:
            Filename string
        """
        pass

    @abstractmethod
    def get_logical_container_name(self) -> str:
        """
        Get logical name of container.
        
        Returns:
            Logical container name
        """
        pass

    @abstractmethod
    def get_condition(self) -> Optional["Condition"]:
        """
        Get condition associated with container.
        
        Returns:
            Condition object or None
        """
        pass

    @abstractmethod
    def pp_action(self) -> None:
        """
        Action to be performed when iterator moves forward.
        Important for writing data operations.
        """
        pass


# Export the abstract base class
__all__ = ['AbstractContainer']