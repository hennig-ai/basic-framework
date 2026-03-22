"""
Abstract database base class.

This module provides the abstract base class for database connections
supporting MS Access, SQLite, and potentially other SQL databases.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Protocol, Iterator, Tuple, Optional


class DatabaseCursor(Protocol):
    """
    Protocol defining the interface for database cursors.

    This protocol allows different database libraries (pyodbc, sqlite3, etc.)
    to be used interchangeably.
    """

    @property
    def description(self) -> Optional[Tuple[Tuple[str, ...], ...]]:
        """Column descriptions from last query."""
        ...

    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> "DatabaseCursor":
        """Execute SQL statement."""
        ...

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        """Fetch next row."""
        ...

    def fetchall(self) -> List[Tuple[Any, ...]]:
        """Fetch all remaining rows."""
        ...

    def fetchmany(self, size: int) -> List[Tuple[Any, ...]]:
        """Fetch specified number of rows."""
        ...

    def close(self) -> None:
        """Close cursor."""
        ...

    def __iter__(self) -> Iterator[Tuple[Any, ...]]:
        """Iterate over rows."""
        ...


class AbstractDatabase(ABC):
    """
    Abstract base class for database connections.

    Provides a common interface for different database backends:
    - MS Access (via pyodbc)
    - SQLite (via sqlite3)
    - Potentially others (PostgreSQL, MySQL, etc.)

    Abstract base class for database connections with generalization for multiple backends.
    """

    @abstractmethod
    def __init__(self, connection_info: str) -> None:
        """
        Initialize database connection.

        Args:
            connection_info: Connection string or file path depending on backend.
                - SQLite: File path to .db file
                - MS Access: File path to .accdb/.mdb file
                - Others: Full connection string
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close database connection.

        Should be called when done with database operations.
        """
        pass

    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists in database.

        Args:
            table_name: Name of table to check.

        Returns:
            True if table exists, False otherwise.
        """
        pass

    @abstractmethod
    def execute(self, sql: str) -> None:
        """
        Execute SQL statement without returning results.

        Use for INSERT, UPDATE, DELETE, CREATE, DROP statements.

        Args:
            sql: SQL statement to execute.

        Raises:
            Exception: If SQL execution fails.
        """
        pass

    @abstractmethod
    def execute_with_params(self, sql: str, params: Tuple[Any, ...]) -> None:
        """
        Execute parameterized SQL statement without returning results.

        Use for INSERT, UPDATE, DELETE with parameters to prevent SQL injection.

        Args:
            sql: SQL statement with parameter placeholders.
            params: Tuple of parameter values.

        Raises:
            Exception: If SQL execution fails.
        """
        pass

    @abstractmethod
    def open_cursor(self, sql: str) -> DatabaseCursor:
        """
        Open cursor for SELECT query.

        Args:
            sql: SELECT statement to execute.

        Returns:
            Cursor object for iterating results.
        """
        pass

    @abstractmethod
    def open_cursor_with_params(self, sql: str, params: Tuple[Any, ...]) -> DatabaseCursor:
        """
        Open cursor for parameterized SELECT query.

        Args:
            sql: SELECT statement with parameter placeholders.
            params: Tuple of parameter values.

        Returns:
            Cursor object for iterating results.
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get database name or file path.

        Returns:
            Database identifier string.
        """
        pass

    @abstractmethod
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get list of column names for a table.

        Args:
            table_name: Name of table.

        Returns:
            List of column names in order.

        Raises:
            Exception: If table does not exist.
        """
        pass

    @abstractmethod
    def get_table_column_types(self, table_name: str) -> List[Tuple[str, str]]:
        """
        Get column names and types for a table.

        Args:
            table_name: Name of table.

        Returns:
            List of (column_name, column_type) tuples.

        Raises:
            Exception: If table does not exist.
        """
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """
        Start explicit transaction.

        All subsequent write operations will be part of this transaction
        until commit() or rollback() is called.

        Raises:
            RuntimeError: If transaction is already active.
        """
        pass

    @abstractmethod
    def is_in_transaction(self) -> bool:
        """
        Check if transaction is currently active.

        Returns:
            True if transaction is active, False otherwise.
        """
        pass

    @abstractmethod
    def commit(self) -> None:
        """
        Commit current transaction.

        Persists all changes since last commit.
        """
        pass

    @abstractmethod
    def rollback(self) -> None:
        """
        Rollback current transaction.

        Discards all changes since last commit.
        """
        pass

    @abstractmethod
    def get_tables(self) -> List[str]:
        """
        Get list of all table names in database.

        Returns:
            List of table names.
        """
        pass

    @abstractmethod
    def get_primary_key(self, table_name: str) -> List[str]:
        """
        Get primary key column(s) for a table.

        Args:
            table_name: Name of table.

        Returns:
            List of column names that form the primary key.
            Empty list if no primary key is defined.

        Raises:
            ValueError: If table does not exist.
        """
        pass

    @abstractmethod
    def get_last_insert_rowid(self) -> int:
        """
        Get the row ID of the last inserted row.

        Must be called immediately after an INSERT statement.
        The behavior is database-specific:
        - SQLite: Uses last_insert_rowid()
        - MS Access: Uses @@IDENTITY

        Returns:
            The row ID of the last inserted row.
            Returns 0 if no row was inserted or the table has no
            auto-increment primary key.

        Note:
            This only works for tables with an auto-increment (AUTOINCREMENT/COUNTER)
            primary key column.
        """
        pass

    def __enter__(self) -> "AbstractDatabase":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - closes connection."""
        self.close()


__all__ = ['AbstractDatabase', 'DatabaseCursor']
