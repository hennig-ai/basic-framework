"""
SQLite database implementation.

This module provides a concrete implementation of AbstractDatabase
for SQLite databases using Python's built-in sqlite3 module.
"""

import sqlite3
import time
from typing import Any, Callable, List, Tuple, TypeVar

from .abstract_database import AbstractDatabase, DatabaseCursor
from ..proc_frame import log_and_raise, log_msg

T = TypeVar('T')


class SQLiteDB(AbstractDatabase):
    """
    SQLite implementation of AbstractDatabase.

    Uses Python's built-in sqlite3 module for database access.
    No additional dependencies required.

    Example:
        db = SQLiteDB("my_database.db")

        if db.table_exists("users"):
            cursor = db.open_cursor("SELECT * FROM users")
            for row in cursor:
                print(row)

        db.close()

    Or with context manager:
        with SQLiteDB("my_database.db") as db:
            # ... operations ...
    """

    def __init__(
        self,
        connection_info: str,
        retry_count: int = 100,
        retry_delay: float = 2.0
    ) -> None:
        """
        Initialize SQLite database connection.

        Args:
            connection_info: Path to SQLite database file.
                If file doesn't exist, it will be created.
            retry_count: Number of retries on 'database is locked' error.
            retry_delay: Delay in seconds between retries.

        Raises:
            sqlite3.Error: If connection fails.
        """
        self._connection: sqlite3.Connection
        self._db_path: str = connection_info
        self._is_connected: bool = False
        self._retry_count: int = retry_count
        self._retry_delay: float = retry_delay

        try:
            self._connection = sqlite3.connect(connection_info)
            self._is_connected = True
            log_msg(f"SQLite Datenbank '{connection_info}' wurde geöffnet.")
        except sqlite3.Error as e:
            log_and_raise(sqlite3.Error(f"SQLite Verbindung fehlgeschlagen für '{connection_info}': {e}"))

    def close(self) -> None:
        """Close SQLite database connection."""
        if self._is_connected:
            log_msg(f"SQLite Datenbankverbindung zu '{self._db_path}' wird geschlossen...")
            self._connection.close()
            self._is_connected = False

    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists in SQLite database.

        Args:
            table_name: Name of table to check.

        Returns:
            True if table exists, False otherwise.
        """
        self._ensure_connected()

        cursor = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        result = cursor.fetchone()
        cursor.close()
        return result is not None

    def execute(self, sql: str) -> None:
        """
        Execute SQL statement without returning results.

        Args:
            sql: SQL statement to execute.

        Raises:
            sqlite3.Error: If SQL execution fails.
        """
        self._ensure_connected()
        self._execute_with_retry(
            lambda: self._connection.execute(sql),
            f"Execute: SQL '{sql}' fehlgeschlagen"
        )

    def execute_with_params(self, sql: str, params: Tuple[Any, ...]) -> None:
        """
        Execute parameterized SQL statement.

        Args:
            sql: SQL statement with ? placeholders.
            params: Tuple of parameter values.

        Raises:
            sqlite3.Error: If SQL execution fails.
        """
        self._ensure_connected()
        self._execute_with_retry(
            lambda: self._connection.execute(sql, params),
            f"Execute: SQL '{sql}' mit Parametern fehlgeschlagen"
        )

    def open_cursor(self, sql: str) -> DatabaseCursor:
        """
        Open cursor for SELECT query.

        Args:
            sql: SELECT statement to execute.

        Returns:
            Cursor object for iterating results.

        Raises:
            sqlite3.Error: If query fails.
        """
        self._ensure_connected()
        cursor = self._execute_with_retry(
            lambda: self._connection.execute(sql),
            f"OpenCursor: SQL '{sql}' fehlgeschlagen"
        )
        return cursor  # type: ignore[return-value]

    def open_cursor_with_params(self, sql: str, params: Tuple[Any, ...]) -> DatabaseCursor:
        """
        Open cursor for parameterized SELECT query.

        Args:
            sql: SELECT statement with ? placeholders.
            params: Tuple of parameter values.

        Returns:
            Cursor object for iterating results.

        Raises:
            sqlite3.Error: If query fails.
        """
        self._ensure_connected()
        cursor = self._execute_with_retry(
            lambda: self._connection.execute(sql, params),
            f"OpenCursor: SQL '{sql}' mit Parametern fehlgeschlagen"
        )
        return cursor  # type: ignore[return-value]

    def get_name(self) -> str:
        """
        Get database file path.

        Returns:
            Path to SQLite database file.
        """
        return self._db_path

    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get list of column names for a table.

        Args:
            table_name: Name of table.

        Returns:
            List of column names in order.

        Raises:
            ValueError: If table does not exist.
        """
        self._ensure_connected()

        if not self.table_exists(table_name):
            log_and_raise(ValueError(f"Tabelle '{table_name}' existiert nicht in Datenbank '{self._db_path}'."))

        cursor = self._connection.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        cursor.close()
        return columns

    def get_table_column_types(self, table_name: str) -> List[Tuple[str, str]]:
        """
        Get column names and types for a table.

        Args:
            table_name: Name of table.

        Returns:
            List of (column_name, column_type) tuples.

        Raises:
            ValueError: If table does not exist.
        """
        self._ensure_connected()

        if not self.table_exists(table_name):
            log_and_raise(ValueError(f"Tabelle '{table_name}' existiert nicht in Datenbank '{self._db_path}'."))

        cursor = self._connection.execute(f"PRAGMA table_info({table_name})")
        # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
        columns = [(row[1], row[2]) for row in cursor.fetchall()]
        cursor.close()
        return columns

    def begin_transaction(self) -> None:
        """
        Start explicit transaction.

        Raises:
            RuntimeError: If transaction is already active.
        """
        self._ensure_connected()

        if self._connection.in_transaction:
            log_and_raise(RuntimeError(
                "Transaction ist bereits aktiv. "
                "Verschachtelte Transaktionen werden nicht unterstützt."
            ))

        self._connection.execute("BEGIN IMMEDIATE")
        log_msg("Transaction gestartet.")

    def is_in_transaction(self) -> bool:
        """
        Check if transaction is currently active.

        Returns:
            True if transaction is active, False otherwise.
        """
        if not self._is_connected:
            return False
        return self._connection.in_transaction

    def commit(self) -> None:
        """Commit current transaction."""
        self._ensure_connected()
        self._execute_with_retry(
            lambda: self._connection.commit(),
            "Commit fehlgeschlagen"
        )
        log_msg("Transaction committed.")

    def rollback(self) -> None:
        """Rollback current transaction."""
        self._ensure_connected()
        self._connection.rollback()
        log_msg("Transaction rollback.")

    def get_tables(self) -> List[str]:
        """
        Get list of all table names in database.

        Returns:
            List of table names (excluding sqlite internal tables).
        """
        self._ensure_connected()

        cursor = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def get_primary_key(self, table_name: str) -> List[str]:
        """
        Get primary key column(s) for a table.

        Uses PRAGMA table_info which returns pk > 0 for PK columns.

        Args:
            table_name: Name of table.

        Returns:
            List of column names that form the primary key.
            Empty list if no primary key is defined.

        Raises:
            ValueError: If table does not exist.
        """
        self._ensure_connected()

        if not self.table_exists(table_name):
            log_and_raise(ValueError(
                f"Tabelle '{table_name}' existiert nicht in Datenbank '{self._db_path}'."
            ))

        cursor = self._connection.execute(f"PRAGMA table_info({table_name})")
        # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
        # pk is 0 if not part of PK, else 1-based index in composite PK
        pk_columns: List[Tuple[int, str]] = []
        for row in cursor.fetchall():
            if row[5] > 0:  # pk column
                pk_columns.append((int(row[5]), str(row[1])))  # (pk_index, column_name)
        cursor.close()

        # Sort by pk index and return column names
        pk_columns.sort(key=lambda x: x[0])
        return [col[1] for col in pk_columns]

    def get_last_insert_rowid(self) -> int:
        """
        Get the row ID of the last inserted row.

        Uses SQLite's last_insert_rowid() function.

        Returns:
            The row ID of the last inserted row.
            Returns 0 if no row was inserted.
        """
        self._ensure_connected()
        cursor = self._connection.execute("SELECT last_insert_rowid()")
        result = cursor.fetchone()
        cursor.close()
        if result is None:
            return 0
        return int(result[0])

    def _execute_with_retry(self, operation: Callable[[], T], error_context: str) -> T:
        """
        Execute operation with retry on 'database is locked' error.

        Args:
            operation: Callable that performs the database operation.
            error_context: Context string for error messages.

        Returns:
            Result of the operation.

        Raises:
            sqlite3.Error: If operation fails after all retries.
        """
        for attempt in range(self._retry_count):
            try:
                return operation()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < self._retry_count - 1:
                    log_msg(
                        f"Database locked, retry in {self._retry_delay}s "
                        f"({attempt + 1}/{self._retry_count})"
                    )
                    time.sleep(self._retry_delay)
                else:
                    log_and_raise(sqlite3.Error(f"{error_context}: {e}"))
                    raise  # Für Type Checker - wird nie erreicht
            except sqlite3.Error as e:
                log_and_raise(sqlite3.Error(f"{error_context}: {e}"))
                raise  # Für Type Checker - wird nie erreicht
        # Sollte nie erreicht werden, aber für Type Checker
        log_and_raise(sqlite3.Error(f"{error_context}: Max retries exceeded"))
        raise  # Für Type Checker - wird nie erreicht

    def _ensure_connected(self) -> None:
        """
        Ensure database connection is established.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._is_connected:
            log_and_raise(RuntimeError("SQLiteDB: Keine Datenbankverbindung."))


__all__ = ['SQLiteDB']
