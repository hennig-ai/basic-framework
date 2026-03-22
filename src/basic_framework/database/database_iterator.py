"""
Database iterator implementation.

This module provides an iterator for database containers with read and write support.
Works with any AbstractDatabase implementation (SQLite, MS Access, etc.).
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..container_utils.abstract_iterator import AbstractIterator
from ..container_utils.container_in_memory import ContainerInMemory
from ..conditions.condition import Condition
from ..proc_frame import log_and_raise, log_msg

if TYPE_CHECKING:
    from .database_container import DatabaseContainer
    from .abstract_database import AbstractDatabase, DatabaseCursor


class DatabaseIterator(AbstractIterator):
    """
    Database iterator with read and write support.

    Provides iteration over database query results with the ability to
    insert, update, and delete records.

    Example - Reading:
        container = DatabaseContainer(db, "Customers")
        iterator = container.create_iterator()

        while not iterator.is_empty():
            name = iterator.value("name")
            print(name)
            iterator.pp()

    Example - Inserting:
        iterator = container.create_iterator()
        iterator.start_insert()
        iterator.set_value("name", "New Customer")
        iterator.set_value("email", "new@example.com")
        iterator.pp()  # Commits the insert

    Example - Updating:
        while not iterator.is_empty():
            if iterator.value("status") == "old":
                iterator.start_update()
                iterator.set_value("status", "archived")
                iterator.pp()  # Commits the update
            else:
                iterator.pp()

    Example - Deleting:
        while not iterator.is_empty():
            if iterator.value("status") == "deleted":
                iterator.delete()
            iterator.pp()
    """

    def __init__(
        self,
        container: "DatabaseContainer",
        condition: Optional[Condition] = None,
        cols_must_exist: bool = True,
        step_factor: int = 1000,
        auto_commit: bool = False
    ) -> None:
        """
        Initialize DatabaseIterator for a database container.

        Args:
            container: DatabaseContainer to iterate over.
            condition: Optional condition for filtering (applied at SQL level).
            cols_must_exist: Whether columns must exist when accessing.
            step_factor: Step factor for logging distance.
            auto_commit: If True, each write operation commits immediately.
                If False, requires active transaction for write operations.

        Note:
            Transaction validation occurs at write time (start_insert, start_update, delete),
            not at iterator creation. This allows creating read-only iterators without
            starting a transaction.

            For SQL queries, the container pre-loads data into memory. The iterator
            then delegates to a memory-based iterator, avoiding database locks.
        """
        super().__init__()

        # Write operation state
        self._pending_operation: Optional[str] = None  # "INSERT" or "UPDATE"
        self._pending_values: Dict[str, Any] = {}
        self._current_pk_values: Dict[str, Any] = {}

        self._cursor: Optional["DatabaseCursor"] = None
        self._current_row: Dict[str, Any] = {}
        self._column_names: List[str] = []
        self._is_at_end: bool = True

        # Memory-based iteration for SQL queries
        self._memory_iterator: Optional[AbstractIterator] = None

        # Store database reference
        self._db: "AbstractDatabase" = container.get_database()
        self._table_name: str = container.get_table_name()
        self._is_writable: bool = container.is_writable
        self._auto_commit: bool = auto_commit
        self._primary_key: List[str] = []
        self._last_insert_rowid: int = 0

        # Get primary key for write operations
        if self._is_writable and self._table_name:
            self._primary_key = self._db.get_primary_key(self._table_name)
            if not self._primary_key:
                log_msg(
                    f"Warnung: Tabelle '{self._table_name}' hat keinen Primary Key. "
                    "UPDATE und DELETE sind nicht möglich."
                )
                self._is_writable = False

        # Initialize base iterator
        self._container = container
        self._condition = condition
        self._log_distance = step_factor
        self._cols_must_exist = cols_must_exist

        # Check if container has pre-loaded memory cache (SQL queries)
        memory_cache = container.get_memory_cache()
        if memory_cache is not None:
            # SQL query: delegate to memory-based iterator
            self._memory_iterator = memory_cache.create_iterator(
                cols_from_target_must_exist_in_source=cols_must_exist,
                condition=condition
            )
            self._is_at_end = self._memory_iterator.is_empty()
        elif condition is not None:
            # Table with condition: read-only, use fetchall to avoid locks
            self._load_all_to_memory(condition)
        else:
            # Table without condition: use cursor-based iteration (can write)
            self._open_cursor(condition)

    def _open_cursor(self, condition: Optional[Condition] = None) -> None:
        """
        Open database cursor for iteration.

        Args:
            condition: Optional condition for WHERE clause.
        """
        if not self._container:
            log_and_raise(ValueError("Container ist nicht initialisiert."))

        from .database_container import DatabaseContainer
        container = self._container
        if not isinstance(container, DatabaseContainer):
            log_and_raise(ValueError("Container muss ein DatabaseContainer sein."))

        sql = container.build_sql(condition)

        self._cursor = self._db.open_cursor(sql)

        # Get column names from cursor description
        if self._cursor.description:
            self._column_names = [col[0] for col in self._cursor.description]

        # Load first row
        self._load_next_row()

    def _load_all_to_memory(self, condition: Condition) -> None:
        """
        Load all data into memory for table access with condition.

        When a condition is provided for table access, the data is read-only
        (no UPDATE/DELETE possible). Using fetchall() avoids holding database
        locks during iteration.

        Args:
            condition: Condition for WHERE clause.
        """
        if not self._container:
            log_and_raise(ValueError("Container ist nicht initialisiert."))

        from .database_container import DatabaseContainer
        container = self._container
        if not isinstance(container, DatabaseContainer):
            log_and_raise(ValueError("Container muss ein DatabaseContainer sein."))

        sql = container.build_sql(condition)

        cursor = self._db.open_cursor(sql)

        # Get column names
        column_names: List[str] = []
        if cursor.description:
            column_names = [col[0] for col in cursor.description]

        # Fetch all data at once
        rows = cursor.fetchall()

        # Close cursor immediately to release locks
        cursor.close()

        # Store in ContainerInMemory
        memory_cache = ContainerInMemory()
        memory_cache.init_new(column_names, container.get_technical_container_name())

        for row in rows:
            row_index = memory_cache.add_empty_row()
            for i, col_name in enumerate(column_names):
                memory_cache.set_value(row_index, col_name, row[i])

        # Create memory iterator (no additional condition needed, already applied in SQL)
        self._memory_iterator = memory_cache.create_iterator(
            cols_from_target_must_exist_in_source=self._cols_must_exist
        )
        self._is_at_end = self._memory_iterator.is_empty()

    def _load_next_row(self) -> None:
        """Load next row from cursor into current_row dict."""
        self._current_row.clear()
        self._current_pk_values.clear()

        if self._cursor is None:
            self._is_at_end = True
            return

        row = self._cursor.fetchone()
        if row is None:
            self._is_at_end = True
        else:
            self._is_at_end = False
            # Map row values to column names
            for i, col_name in enumerate(self._column_names):
                self._current_row[col_name] = row[i]
                # Track PK values for UPDATE/DELETE
                if col_name in self._primary_key:
                    self._current_pk_values[col_name] = row[i]

    def _close_cursor(self) -> None:
        """Close database cursor if open."""
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None

    # === Read Operations ===

    def is_empty(self) -> bool:
        """
        Check if iterator is at end of results.

        Returns:
            True if no more rows available.
        """
        if self._memory_iterator is not None:
            return self._memory_iterator.is_empty()
        return self._is_at_end

    def value(self, column: str) -> Any:
        """
        Get value at current row and column.

        Args:
            column: Column name.

        Returns:
            Value from current row.
        """
        if self._memory_iterator is not None:
            return self._memory_iterator.value(column)

        if self._is_at_end:
            return ""

        if self._cols_must_exist and column not in self._current_row:
            log_and_raise(ValueError(
                f"Spalte '{column}' existiert nicht in Ergebnismenge."
            ))

        return self._current_row.get(column, "")

    def reset(self) -> int:
        """
        Reset iterator to first row.

        Reopens cursor and loads first row.

        Returns:
            New position (1).
        """
        self._pending_operation = None
        self._pending_values.clear()
        self._position = 1

        if self._memory_iterator is not None:
            self._memory_iterator.reset()
        else:
            self._close_cursor()
            self._open_cursor(self._condition)

        return self._position

    def pp(self) -> int:
        """
        Move to next row (plus-plus operation).

        If a write operation is pending (INSERT or UPDATE),
        it will be committed before moving.

        Returns:
            New position.
        """
        # Execute pending write operation
        if self._pending_operation == "INSERT":
            self._execute_insert()
        elif self._pending_operation == "UPDATE":
            self._execute_update()

        self._pending_operation = None
        self._pending_values.clear()

        # Move to next row
        if self._memory_iterator is not None:
            self._memory_iterator.pp()
        else:
            self._load_next_row()

        self._position += 1

        return self._position

    def finish(self) -> None:
        """
        Finish iteration and close cursor.

        Should be called when done iterating to release resources.
        """
        # Execute any pending operation
        if self._pending_operation == "INSERT":
            self._execute_insert()
        elif self._pending_operation == "UPDATE":
            self._execute_update()

        self._pending_operation = None
        self._pending_values.clear()

        if self._memory_iterator is not None:
            # Memory iterator has no cursor to close
            self._memory_iterator = None
        else:
            self._close_cursor()

    # === Write Operations ===

    def _validate_write_transaction(self) -> None:
        """
        Validate transaction state for write operations.

        Raises:
            RuntimeError: If auto_commit=False but no transaction is active.
            RuntimeError: If auto_commit=True but transaction is active.
        """
        in_transaction = self._db.is_in_transaction()

        if not self._auto_commit and not in_transaction:
            log_and_raise(RuntimeError(
                "auto_commit=False erfordert eine aktive Transaction. "
                "Bitte zuerst db.begin_transaction() aufrufen."
            ))

        if self._auto_commit and in_transaction:
            log_and_raise(RuntimeError(
                "auto_commit=True ist nicht erlaubt wenn eine Transaction aktiv ist. "
                "Verwende auto_commit=False innerhalb einer Transaction."
            ))

    def start_insert(self) -> None:
        """
        Start insert operation for new row.

        Call set_value() to set column values, then pp() to commit.

        Raises:
            ValueError: If container is not writable.
            RuntimeError: If transaction state is invalid for write.
        """
        if not self._is_writable:
            log_and_raise(ValueError(
                f"Container ist nicht schreibbar. "
                f"Schreiben nur für einzelne Tabellen mit Primary Key möglich."
            ))

        self._validate_write_transaction()

        self._pending_operation = "INSERT"
        self._pending_values.clear()

    def start_update(self) -> None:
        """
        Start update operation for current row.

        Call set_value() to set new values, then pp() to commit.

        Raises:
            ValueError: If container is not writable or no current row.
            RuntimeError: If transaction state is invalid for write.
        """
        if not self._is_writable:
            log_and_raise(ValueError(
                f"Container ist nicht schreibbar. "
                f"Schreiben nur für einzelne Tabellen mit Primary Key möglich."
            ))

        if self._is_at_end:
            log_and_raise(ValueError(
                "Kein aktueller Datensatz für UPDATE vorhanden."
            ))

        if not self._current_pk_values:
            log_and_raise(ValueError(
                "Primary Key Werte nicht verfügbar für UPDATE."
            ))

        self._validate_write_transaction()

        self._pending_operation = "UPDATE"
        self._pending_values.clear()

    def set_value(self, column: str, value: Any) -> None:
        """
        Set value for column in pending write operation.

        If no write operation is pending, automatically starts
        INSERT (if at end) or UPDATE (if on current row).

        Args:
            column: Column name.
            value: Value to set.
        """
        # Auto-start write operation if not started
        if self._pending_operation is None:
            if self._is_at_end:
                self.start_insert()
            else:
                self.start_update()

        self._pending_values[column] = value

    def delete(self) -> None:
        """
        Delete current row.

        Raises:
            ValueError: If container is not writable or no current row.
            RuntimeError: If transaction state is invalid for write.
        """
        if not self._is_writable:
            log_and_raise(ValueError(
                f"Container ist nicht schreibbar. "
                f"Löschen nur für einzelne Tabellen mit Primary Key möglich."
            ))

        if self._is_at_end:
            log_and_raise(ValueError(
                "Kein aktueller Datensatz für DELETE vorhanden."
            ))

        if not self._current_pk_values:
            log_and_raise(ValueError(
                "Primary Key Werte nicht verfügbar für DELETE."
            ))

        self._validate_write_transaction()

        self._execute_delete()

    def get_last_insert_rowid(self) -> int:
        """
        Get the row ID of the last inserted row.

        Must be called after an INSERT operation (start_insert + pp/finish).

        Returns:
            The row ID of the last inserted row.
            Returns 0 if no INSERT was performed yet.

        Example:
            iterator.start_insert()
            iterator.set_value("name", "Test")
            iterator.pp()  # Executes INSERT
            new_id = iterator.get_last_insert_rowid()
        """
        return self._last_insert_rowid

    # === SQL Execution ===

    def _execute_insert(self) -> None:
        """Execute pending INSERT operation."""
        if not self._pending_values:
            log_msg("INSERT übersprungen: Keine Werte gesetzt.")
            return

        columns = list(self._pending_values.keys())
        placeholders = ", ".join(["?" for _ in columns])
        column_list = ", ".join(columns)
        values = tuple(self._pending_values.values())

        sql = f"INSERT INTO {self._table_name} ({column_list}) VALUES ({placeholders})"

        self._db.execute_with_params(sql, values)

        # Store last insert rowid immediately after INSERT
        self._last_insert_rowid = self._db.get_last_insert_rowid()

        if self._auto_commit:
            self._db.commit()

        log_msg(f"INSERT in '{self._table_name}' ausgeführt (rowid={self._last_insert_rowid}).")

    def _execute_update(self) -> None:
        """Execute pending UPDATE operation."""
        if not self._pending_values:
            log_msg("UPDATE übersprungen: Keine Werte geändert.")
            return

        # Build SET clause
        set_parts = [f"{col} = ?" for col in self._pending_values.keys()]
        set_clause = ", ".join(set_parts)

        # Build WHERE clause from primary key
        where_parts = [f"{col} = ?" for col in self._primary_key]
        where_clause = " AND ".join(where_parts)

        # Combine values: SET values + WHERE values
        values = tuple(self._pending_values.values()) + tuple(
            self._current_pk_values[col] for col in self._primary_key
        )

        sql = f"UPDATE {self._table_name} SET {set_clause} WHERE {where_clause}"

        self._db.execute_with_params(sql, values)

        if self._auto_commit:
            self._db.commit()

        log_msg(f"UPDATE in '{self._table_name}' ausgeführt.")

    def _execute_delete(self) -> None:
        """Execute DELETE operation for current row."""
        # Build WHERE clause from primary key
        where_parts = [f"{col} = ?" for col in self._primary_key]
        where_clause = " AND ".join(where_parts)

        values = tuple(self._current_pk_values[col] for col in self._primary_key)

        sql = f"DELETE FROM {self._table_name} WHERE {where_clause}"

        self._db.execute_with_params(sql, values)

        if self._auto_commit:
            self._db.commit()

        log_msg(f"DELETE aus '{self._table_name}' ausgeführt.")

    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        # Check for uncommitted pending operations
        if self._pending_operation is not None:
            pending_cols = list(self._pending_values.keys())
            # Note: Exceptions in __del__ are suppressed by Python,
            # but log_and_raise will still log and beep
            log_and_raise(RuntimeError(
                f"Iterator hat uncommitted {self._pending_operation} Operation! "
                f"Pending columns: {pending_cols}. "
                f"Bitte pp() aufrufen um die Operation auszuführen."
            ))

        try:
            self._close_cursor()
        except Exception:
            # Ignore errors during cleanup (database may already be closed)
            pass


__all__ = ['DatabaseIterator']
