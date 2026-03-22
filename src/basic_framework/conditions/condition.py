"""
Abstract base class for conditions.
"""

from abc import ABC, abstractmethod
from typing import Any


class Condition(ABC):
    """Abstract base class for condition implementations."""
    
    @abstractmethod
    def is_true(self, data: Any) -> bool:
        """Check if the condition is true for the given data object."""
        pass
    
    @abstractmethod
    def as_string(self) -> str:
        """Return a string representation of the condition."""
        pass