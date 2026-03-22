"""
Database container implementation.

This module provides a concrete implementation of AbstractContainer
for database tables and queries, working with any AbstractDatabase implementation.
"""

from typing import Any, Collection, Dict, List, Optional, TYPE_CHECKING

from ..conditions.condition import Condition
from ..container_utils.abstract_container import AbstractContainer
from ..container_utils.container_in_memory import ContainerInMemory
from ..proc_frame import log_and_raise
from .abstract_database import AbstractDatabase, DatabaseCursor

if TYPE_CHECKING:
    from .database_iterator import DatabaseIterator


class DatabaseContainer(AbstractContainer):
    """
    Database implementation of AbstractContainer.

    Supports reading from database tables and queries using any
    AbstractDatabase implementation (SQLite, MS Access, etc.).

    Example with SQLite:
        from basic_framework import SQLiteDB, DatabaseContainer

        db = SQLiteDB("data.db")

        container = DatabaseContainer(db, "Customers")
        iterator = container.create_iterator()

        while not iterator.is_empty():
            name = iterator.value("name")
            print(name)
            iterator.pp()

        db.close()

    Example with SQL query:
        container = DatabaseContainer(db, "SELECT * FROM Customers WHERE active = 1")
    """

    def __init__(self, db: AbstractDatabase, table_or_sql: str) -> None:
        """
        Initialize DatabaseContainer.

        Args:
            db: Database connection (any AbstractDatabase implementation).
            table_or_sql: Table name or SQL SELECT statement.

        Note:
            For SQL queries, all data is loaded immediately into memory
            using fetchall() to avoid holding database locks during iteration.
            For tables, data is loaded on-demand using fetchone().
        """
        self._db: AbstractDatabase = db
        self._table_or_sql: str = table_or_sql
        self._is_sql_query: bool = self._detect_sql_query(table_or_sql)

        self._headers: Dict[str, int] = {}
        self._headers_as_ref: Optional[List[str]] = None
        self._cursor: Optional[DatabaseCursor] = None
        self._current_row: Dict[str, Any] = {}
        self._is_at_end: bool = False
        self._condition_sql: Optional[str] = None

        # Memory cache for SQL queries (to avoid holding locks)
        self._memory_cache: Optional[ContainerInMemory] = None

        self._init_headers()

        # For SQL queries: load all data immediately into memory
        if self._is_sql_query:
            self._load_all_data()
        # log_msg(f"DatabaseContainer für '{self._get_display_name()}' initialisiert.")

    def _detect_sql_query(self, table_or_sql: str) -> bool:
        """
        Detect if input is SQL query or table name.

        Args:
            table_or_sql: Input string to check.

        Returns:
            True if SQL query, False if table name.
        """
        # Normalize: strip whitespace and convert to uppercase
        normalized = table_or_sql.strip().upper()

        # Check for SQL keywords at the start
        # SELECT can be followed by space, *, newline, or tab
        if normalized.startswith("SELECT"):
            # Make sure it's not just a table named "SELECT..."
            if len(normalized) == 6:  # Just "SELECT"
                return False
            next_char = normalized[6]
            # Valid chars after SELECT: whitespace or *
            return next_char in (" ", "\t", "\n", "\r", "*")

        # Also check for WITH (CTEs) and parentheses (subqueries)
        if normalized.startswith("WITH ") or normalized.startswith("(SELECT"):
            return True

        return False

    def _get_display_name(self) -> str:
        """Get display name for logging."""
        if self._is_sql_query:
            # Truncate long SQL for display
            if len(self._table_or_sql) > 50:
                return self._table_or_sql[:50] + "..."
            return self._table_or_sql
        return f"{self._db.get_name()}.{self._table_or_sql}"

    def _init_headers(self) -> None:
        """Initialize column headers from database."""
        if self._is_sql_query:
            # For SQL queries, execute and get column names from cursor
            cursor = self._db.open_cursor(self._table_or_sql)
            if cursor.description:
                for i, col_info in enumerate(cursor.description):
                    col_name = col_info[0]
                    self._headers[col_name] = i + 1
            cursor.close()
        else:
            # For table names, get columns from table metadata
            if not self._db.table_exists(self._table_or_sql):
                log_and_raise(ValueError(
                    f"Tabelle '{self._table_or_sql}' existiert nicht in "
                    f"Datenbank '{self._db.get_name()}'."
                ))
            columns = self._db.get_table_columns(self._table_or_sql)
            for i, col_name in enumerate(columns):
                self._headers[col_name] = i + 1

    def _load_all_data(self) -> None:
        """
        Load all data into memory for SQL queries.

        Uses fetchall() to get all rows at once, then immediately closes
        the cursor to release database locks. Data is stored in a
        ContainerInMemory instance for iteration.

        This method is only called for SQL queries, not for table access.
        """
        cursor = self._db.open_cursor(self._table_or_sql)

        # Get column names
        column_names: List[str] = []
        if cursor.description:
            column_names = [col[0] for col in cursor.description]

        # Fetch all data at once
        rows = cursor.fetchall()

        # Close cursor immediately to release locks
        cursor.close()

        # Store in ContainerInMemory
        self._memory_cache = ContainerInMemory()
        self._memory_cache.init_new(column_names, self._get_display_name())

        for row in rows:
            row_index = self._memory_cache.add_empty_row()
            for i, col_name in enumerate(column_names):
                self._memory_cache.set_value(row_index, col_name, row[i])

    def build_sql(self, condition: Optional[Condition] = None) -> str:
        """
        Build SQL statement for query.

        Args:
            condition: Optional condition for WHERE clause.

        Returns:
            Complete SQL SELECT statement.
        """
        if self._is_sql_query:
            base_sql = self._table_or_sql
            # For existing SQL queries with conditions, wrap in subquery
            if condition is not None:
                condition_str = condition.as_string()
                return f"SELECT * FROM ({base_sql}) AS subquery WHERE {condition_str}"
            return base_sql
        else:
            # For table names, build simple SELECT
            if condition is not None:
                condition_str = condition.as_string()
                return f"SELECT * FROM {self._table_or_sql} WHERE {condition_str}"
            return f"SELECT * FROM {self._table_or_sql}"

    def _open_cursor(self, condition: Optional[Condition] = None) -> None:
        """
        Open database cursor for iteration.

        Args:
            condition: Optional condition for filtering.
        """
        sql = self.build_sql(condition)
        self._cursor = self._db.open_cursor(sql)
        self._is_at_end = False
        # Read first row
        self.pp_action()

    def _close_cursor(self) -> None:
        """Close database cursor if open."""
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None

    # AbstractContainer implementation

    def pp_action(self) -> None:
        """
        Action performed when iterator moves forward.

        Reads next row from database cursor.
        """
        if self._cursor is None:
            self._is_at_end = True
            return

        self._current_row.clear()

        try:
            row = self._cursor.fetchone()
            if row is None:
                self._is_at_end = True
            else:
                self._is_at_end = False
                # Map row values to column names
                if self._cursor.description:
                    for i, col_info in enumerate(self._cursor.description):
                        col_name = col_info[0]
                        self._current_row[col_name] = row[i]
        except StopIteration:
            self._is_at_end = True

    def iterator_is_empty(self, row: int) -> bool:
        """
        Check if iterator is at end.

        Args:
            row: Row position (unused for cursor-based iteration).

        Returns:
            True if at end of results.
        """
        return self._is_at_end

    def get_object(self, row: int) -> Any:
        """
        Get object at row - not supported for databases.

        Args:
            row: Row position.

        Raises:
            NotImplementedError: Always.
        """
        log_and_raise(NotImplementedError(
            "get_object() ist für DatabaseContainer nicht implementiert."
        ))
        return None

    def field_exists(self, column: str) -> bool:
        """
        Check if column exists in result set.

        Args:
            column: Column name to check.

        Returns:
            True if column exists.
        """
        return column in self._headers

    def get_value(self, position: int, column: str) -> Any:
        """
        Get value at current position and column.

        Args:
            position: Row position (unused for cursor-based iteration).
            column: Column name.

        Returns:
            Value from current row.
        """
        if column not in self._headers:
            log_and_raise(ValueError(
                f"Spalte '{column}' existiert nicht in '{self._get_display_name()}'."
            ))
        return self._current_row.get(column, "")

    def set_value(self, position: int, column: str, value: Any) -> None:
        """
        Set value - not supported for read-only database containers.

        Args:
            position: Row position.
            column: Column name.
            value: Value to set.

        Raises:
            NotImplementedError: Always (read-only container).
        """
        log_and_raise(NotImplementedError(
            "set_value() ist für DatabaseContainer (read-only) nicht implementiert. "
            "Verwende db.execute() für Datenänderungen."
        ))

    def create_iterator(
        self,
        cols_from_target_must_exist_in_source: bool = True,
        condition: Optional[Condition] = None,
        auto_commit: bool = False
    ) -> "DatabaseIterator":
        """
        Create iterator for this container.

        If a condition is provided, it will be converted to SQL WHERE clause
        for efficient database-level filtering.

        The returned DatabaseIterator supports read and write operations
        (INSERT, UPDATE, DELETE) if the container is writable.

        Args:
            cols_from_target_must_exist_in_source: Whether columns must exist.
            condition: Optional condition for filtering (converted to SQL WHERE).
            auto_commit: If True, each write operation commits immediately.
                If False, requires active transaction for write operations.

        Returns:
            New DatabaseIterator instance.

        Note:
            Transaction validation occurs at write time (start_insert, start_update, delete),
            not at iterator creation. This allows creating read-only iterators without
            starting a transaction.
        """
        # Import here to avoid circular import
        from .database_iterator import DatabaseIterator

        # Close any existing cursor (cleanup from previous iterations)
        self._close_cursor()

        return DatabaseIterator(
            container=self,
            condition=condition,
            cols_must_exist=cols_from_target_must_exist_in_source,
            auto_commit=auto_commit
        )

    def get_list_of_fields_as_ref(self) -> Collection[str]:
        """
        Get list of column names.

        Returns:
            List of column names.
        """
        if self._headers_as_ref is None:
            self._headers_as_ref = list(self._headers.keys())
        return self._headers_as_ref

    def get_technical_container_name(self) -> str:
        """
        Get technical container name.

        Returns:
            Database and table/query name.
        """
        return self._get_display_name()

    def get_file_name(self) -> str:
        """
        Get database file name.

        Returns:
            Database name/path.
        """
        return self._db.get_name()

    def get_logical_container_name(self) -> str:
        """
        Get logical container name.

        Returns:
            Same as technical name.
        """
        return self.get_technical_container_name()

    def get_condition(self) -> Optional[Condition]:
        """
        Get condition - always None (condition applied at SQL level).

        Returns:
            None.
        """
        return None

    def get_database(self) -> AbstractDatabase:
        """
        Get underlying database connection.

        Returns:
            Database instance.
        """
        return self._db

    def get_memory_cache(self) -> Optional[ContainerInMemory]:
        """
        Get memory cache if available.

        For SQL queries, data is pre-loaded into a ContainerInMemory
        instance to avoid holding database locks during iteration.

        Returns:
            ContainerInMemory instance if this is a SQL query, None for tables.
        """
        return self._memory_cache

    def get_table_or_sql(self) -> str:
        """
        Get table name or SQL query.

        Returns:
            Table name or SQL string.
        """
        return self._table_or_sql

    def get_table_name(self) -> str:
        """
        Get table name if container is based on a single table.

        Returns:
            Table name, or empty string if container is based on SQL query.
        """
        if self._is_sql_query:
            return ""
        return self._table_or_sql

    @property
    def is_writable(self) -> bool:
        """
        Check if container supports write operations.

        Write operations (INSERT, UPDATE, DELETE) are only supported
        when the container is based on a single table (not a SQL query).

        Returns:
            True if container is writable.
        """
        return not self._is_sql_query

    def close(self) -> None:
        """Close cursor and release resources."""
        self._close_cursor()
        # log_msg(f"DatabaseContainer für '{self._get_display_name()}' geschlossen.")

    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        self._close_cursor()


__all__ = ['DatabaseContainer']
