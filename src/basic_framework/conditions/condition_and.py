"""
AND condition implementation.
"""

from typing import Any
from .condition import Condition
from ..proc_frame import log_and_raise


class ConditionAnd(Condition):
    """Condition that combines two conditions with AND logic."""

    def __init__(self, condition1: Condition, condition2: Condition):
        """
        Initialize the AND condition.

        Args:
            condition1: First condition
            condition2: Second condition

        Raises:
            ValueError: If any condition is None
        """
        if condition1 is None:
            log_and_raise("condition1 cannot be None")
        if condition2 is None:
            log_and_raise("condition2 cannot be None")
        self._condition1 = condition1
        self._condition2 = condition2

    def is_true(self, data: Any) -> bool:
        """
        Check if the condition is true for the given data object.

        Args:
            data: Data object to check

        Returns:
            True if both conditions are true
        """
        return self._condition1.is_true(data) and self._condition2.is_true(data)
    
    def as_string(self) -> str:
        """
        Return a string representation of the condition.

        Returns:
            String representation with AND operator
        """
        return f"({self._condition1.as_string()} and {self._condition2.as_string()})"