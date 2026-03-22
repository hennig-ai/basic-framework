"""
Abstract iterator implementation.

This module provides iterator functionality for container classes,
supporting position tracking, condition filtering, and data access.
"""

from typing import Any, Collection, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .abstract_container import AbstractContainer
from ..conditions.condition import Condition

from ..proc_frame import log_and_raise, log_msg


class AbstractIterator:
    """
    Iterator class for traversing container data with optional filtering.
    
    Provides position-based iteration with condition filtering and logging support.
    """

    def __init__(self):
        """Initialize the iterator with default values."""
        self._container: Optional["AbstractContainer"] = None
        self._cols_must_exist: bool = True
        self._condition: Optional["Condition"] = None
        self._log_distance: int = 1000
        self._position: int = 1

    def init(self, 
             container: Any,
             cols_must_exist: bool = True,
             condition: Optional["Condition"] = None,
             step_factor: int = 1000) -> "AbstractIterator":
        """
        Initialize iterator with container and options.
        
        Args:
            container: Container object to iterate over
            cols_must_exist: Whether columns must exist when accessing
            condition: Optional condition for filtering
            step_factor: Step factor for logging distance
            
        Returns:
            Self for method chaining
        """
        self._container = container
        self._condition = condition
        self._log_distance = step_factor
        self._cols_must_exist = cols_must_exist
        self.reset()
        return self

    def finish(self) -> None:
        """Finish iteration - for compatibility with database iterators."""
        pass

    def set_log_distance(self, distance: int) -> None:
        """
        Set distance for log messages during iteration.
        
        Args:
            distance: Distance between log messages
        """
        self._log_distance = distance

    def cols_from_target_must_exist_in_source(self) -> bool:
        """
        Check if columns from target must exist in source.
        
        Returns:
            True if columns must exist
        """
        return self._cols_must_exist

    def _find_next(self, step: int = 1) -> int:
        """
        Find next record matching conditions.
        
        Args:
            step: Step size for searching
            
        Returns:
            Position of next matching record
        """
        result_position = self._position
        
        while not self.is_empty():
            if self._condition is None or self._condition.is_true(self):
                break
            self._position += step
            result_position = self._position
        
        return result_position

    def reset(self) -> int:
        """
        Reset iterator to first position.
        
        Returns:
            New position (usually 1)
        """
        self._position = 1
        
        if self._condition is not None:
            self._position = self._find_next()
        
        return self._position

    def delete(self) -> None:
        """Delete current record - not allowed for this class."""
        log_and_raise("Delete: ist für diese Klasse nicht erlaubt")

    def write_pp_message(self, message: str) -> None:
        """
        Write progress message during iteration if at logging interval.
        
        Args:
            message: Message to log
        """
        current_pos = self.position()
        remainder = self._log_distance * (current_pos // self._log_distance)
        
        if remainder == current_pos:
            container_name = self.get_technical_container_name()
            log_msg(f"{container_name},Position {current_pos}: {message}")

    def pp(self) -> int:
        """
        Move iterator forward (plus-plus operation).
        
        Returns:
            New position
        """
        if self._container:
            self._container.pp_action()
        
        self._position += 1
        
        if self._condition is not None:
            self._position = self._find_next()
        
        return self._position

    def mm(self) -> int:
        """Move iterator backward - not allowed for this class."""
        log_and_raise("mm: ist für diese Klasse nicht erlaubt")
        return self._position

    def step_behind_last_row(self) -> None:
        """Move iterator to position after last row."""
        self.reset()
        while not self.is_empty():
            self.pp()

    def position(self) -> int:
        """
        Get current iterator position.
        
        Returns:
            Current position (1-based)
        """
        return self._position

    def set_position(self, position: int) -> None:
        """
        Set iterator position.
        
        Args:
            position: New position (1-based)
        """
        self._position = position

    def get_value(self, field: str) -> Any:
        """
        Get value of field at current position.
        
        Args:
            field: Field name
            
        Returns:
            Field value
        """
        return self.value(field)

    def value(self, column: str) -> Any:
        """
        Get value at current position and column.
        
        Args:
            column: Column name
            
        Returns:
            Value at current position
        """
        if not self._container:
            return ""
        
        if self._cols_must_exist:
            return self._container.get_value(self._position, column)
        elif self._container.field_exists(column):
            return self._container.get_value(self._position, column)
        else:
            return ""

    def set_value(self, column: str, value: Any) -> None:
        """
        Set value at current position and column.
        
        Args:
            column: Column name
            value: Value to set
        """
        if self._container:
            self._container.set_value(self._position, column, value)

    def is_empty(self) -> bool:
        """
        Check if iterator is at empty position.
        
        Returns:
            True if at empty position
        """
        if not self._container:
            return True
        return self._container.iterator_is_empty(self._position)

    def field_exists(self, column: str) -> bool:
        """
        Check if field exists in container.
        
        Args:
            column: Column name
            
        Returns:
            True if field exists
        """
        if not self._container:
            return False
        return self._container.field_exists(column)

    def get_object(self) -> Any:
        """
        Get object at current position.
        
        Returns:
            Object at current position
        """
        if not self._container:
            return None
        return self._container.get_object(self._position)

    def get_list_of_fields_as_ref(self) -> Collection[str]:
        """
        Get list of field names.
        
        Returns:
            Collection of field names
        """
        if not self._container:
            return []
        return self._container.get_list_of_fields_as_ref()

    def get_technical_container_name(self) -> str:
        """
        Get technical name of container.
        
        Returns:
            Technical container name
        """
        if not self._container:
            return ""
        return self._container.get_technical_container_name()

    def get_container_file_name(self) -> str:
        """
        Get filename of container.
        
        Returns:
            Container filename
        """
        if not self._container:
            return ""
        return self._container.get_file_name()

    def get_logical_container_name(self) -> str:
        """
        Get logical name of container.
        
        Returns:
            Logical container name
        """
        if not self._container:
            return ""
        return self._container.get_logical_container_name()

    def get_container(self) -> Optional["AbstractContainer"]:
        """
        Get the container object.
        
        Returns:
            Container object
        """
        return self._container

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"AbstractIterator(pos={self._position}, container={type(self._container).__name__ if self._container else None})"


# Export the iterator class
__all__ = ['AbstractIterator']