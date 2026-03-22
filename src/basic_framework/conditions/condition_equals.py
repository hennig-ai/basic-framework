"""
Equality condition implementation.
"""

from typing import Any, cast
from .condition import Condition
from ..utils.basic_utils import escape_access_sql_string
from ..proc_frame import log_and_raise


class ConditionEquals(Condition):
    """Condition that checks if a field equals a specific value."""
    
    def __init__(self, column: str, value: Any):
        """2
        Initialize the equality condition.
        
        Args:
            column: Column name to check
            value: Value to compare against
        """
        self._column = column
        self._value = value
    
    def is_true(self, data: Any) -> bool:
        """
        Check if the condition is true for the given data object.
        
        Args:
            data: Data object with GetValue method
            
        Returns:
            True if the field equals the expected value
        """
        try:
            field_value = data.get_value(self._column)
            return cast(bool, field_value == self._value)
        except (AttributeError, KeyError, Exception):
            log_and_raise("Schwerer Programmierfehler im is_true")
    
    def as_string(self) -> str:
        """
        Return a string representation of the condition.
        
        Returns:
            SQL-like string representation of the condition
        """
        # Check if value is numeric
        if isinstance(self._value, (int, float)):
            return f"[{self._column}]={self._value}"
        else:
            # Escape string value for SQL
            escaped_value = escape_access_sql_string(str(self._value))
            return f"[{self._column}]='{escaped_value}'"