"""
Static container basics with factory functions.

This module provides factory functions for creating iterators and conditions,
serving as a convenience layer for container and condition operations.
"""

from typing import Any, Optional

from .abstract_container import AbstractContainer
from ..conditions.condition import Condition

from .abstract_iterator import AbstractIterator
from ..conditions.condition_and import ConditionAnd
from ..conditions.condition_equals import ConditionEquals
from ..conditions.condition_not import ConditionNot


def create_new_iterator(container: "AbstractContainer",
                       condition: Optional["Condition"] = None,
                       cols_must_exist: bool = True) -> AbstractIterator:
    """
    Create new iterator for container with optional condition.
    
    Args:
        container: Container to iterate over
        condition: Optional additional condition
        cols_must_exist: Whether columns must exist
        
    Returns:
        New iterator instance with combined conditions
    """
    # Get existing condition from container
    condition_before = container.get_condition()
    
    # Combine conditions
    if condition_before is None:
        total_condition = condition
    elif condition is None:
        total_condition = condition_before
    else:
        total_condition = and_(condition_before, condition)
    
    # Create and initialize iterator
    iterator = AbstractIterator()
    iterator.init(container, cols_must_exist, total_condition)
    
    return iterator


def and_(c1: Optional["Condition"], c2: Optional["Condition"]) -> Optional["Condition"]:
    """
    Create AND condition from two conditions.
    
    Args:
        c1: First condition (can be None)
        c2: Second condition (can be None)
        
    Returns:
        Combined AND condition, or single condition if one is None
    """
    if c1 is None:
        return c2
    
    if c2 is None:
        return c1
    
    and_condition = ConditionAnd(c1, c2)
    return and_condition


def equals_(column: str, value: Any) -> ConditionEquals:
    """
    Create equals condition for column and value.
    
    Args:
        column: Column name to check
        value: Value to compare against
        
    Returns:
        New ConditionEquals instance
    """
    return ConditionEquals(column, value)


def not_(condition: "Condition") -> ConditionNot:
    """
    Create NOT condition wrapping another condition.
    
    Args:
        condition: Condition to negate
        
    Returns:
        New ConditionNot instance
    """
    return ConditionNot(condition)


# Factory function aliases for more Pythonic naming
create_iterator = create_new_iterator
condition_and = and_
condition_equals = equals_
condition_not = not_


# Export all factory functions
__all__ = [
    'create_new_iterator',
    'and_',
    'equals_',
    'not_',
    'create_iterator',
    'condition_and', 
    'condition_equals',
    'condition_not'
]