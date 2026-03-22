"""
NOT condition implementation.
"""

from typing import Any
from .condition import Condition


class ConditionNot(Condition):
    """Condition that negates another condition."""
    
    def __init__(self, condition: Condition):
        """
        Initialize the NOT condition.
        
        Args:
            condition: The condition to negate
        """
        self._condition = condition
    
    def is_true(self, data: Any) -> bool:
        """
        Check if the condition is true for the given data object.
        
        Args:
            data: Data object to check
            
        Returns:
            True if the wrapped condition is False
        """
        return not self._condition.is_true(data)
    
    def as_string(self) -> str:
        """
        Return a string representation of the condition.
        
        Returns:
            String representation with NOT operator
        """
        return f"not ({self._condition.as_string()})"