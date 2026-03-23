"""
MS Access database implementation.

This module provides a concrete implementation of AbstractDatabase
for Microsoft Access databases using pyodbc.

Requirements:
    - pyodbc: pip install pyodbc
    - Microsoft Access Database Engine (free download from Microsoft)
"""

from typing import Any, List, Tuple, cast

from .abstract_database import AbstractDatabase, DatabaseCursor
from ..proc_frame import log_and_raise, log_msg


class MSAccessDB(AbstractDatabase):
    """
    MS Access implementation of AbstractDatabase.

    Uses pyodbc for database access. Requires Microsoft Access Database Engine
    to be installed on the system.

    Example:
        db = MSAccessDB("C:/path/to/database.accdb")

        if db.table_exists("Customers"):
            cursor = db.open_cursor("SELECT * FROM Customers")
            for row in cursor:
                print(row)

        db.close()

    Or with context manager:
        with MSAccessDB("C:/path/to/database.accdb") as db:
            # ... operations ...

    Note:
        - Requires pyodbc: pip install pyodbc
        - Requires Microsoft Access Database Engine (32 or 64 bit matching Python)
    """

    def __init__(self, connection_info: str) -> None:
        """
        Initialize MS Access database connection.

        Args:
            connection_info: Path to MS Access database file (.accdb or .mdb).

        Raises:
            ImportError: If pyodbc is not installed.
            Exception: If connection fails.
        """
        try:
            import pyodbc as _pyodbc  # type: ignore[reportMissingImports]  # noqa: F811
        except ImportError:
            log_and_raise(ImportError(
                "pyodbc ist nicht installiert. "
                "Bitte installieren mit: pip install pyodbc"
            ))
            raise  # unreachable, for type checker

        self._pyodbc_module: Any = _pyodbc
        self._connection: Any = None
        self._db_path: str = connection_info
        self._is_connected: bool = False
        self._in_transaction: bool = False

        # Build connection string for MS Access
        connection_string: str = (
            f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};"
            f"DBQ={connection_info};"
        )

        try:
            self._connection = _pyodbc.connect(connection_string)  # type: ignore[reportUnknownMemberType]
            self._is_connected = True
            log_msg(f"MS Access Datenbank '{connection_info}' wurde geöffnet.")
        except Exception as e:
            log_and_raise(type(e)(
                f"MS Access Verbindung fehlgeschlagen für '{connection_info}': {e}"
            ))

    def close(self) -> None:
        """
        Close MS Access database connection.
        """
        if self._is_connected:
            log_msg(f"MS Access Datenbankverbindung zu '{self._db_path}' wird geschlossen...")
            self._connection.close()  # type: ignore[reportUnknownMemberType]
            self._is_connected = False

    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists in MS Access database.

        Args:
            table_name: Name of table to check.

        Returns:
            True if table exists, False otherwise.
        """
        self._ensure_connected()

        cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
        # Get list of tables from Access system catalog
        tables: Any = cursor.tables(tableType='TABLE')  # type: ignore[reportUnknownMemberType]
        result: bool = any(
            str(row.table_name).lower() == table_name.lower()  # type: ignore[reportUnknownMemberType]
            for row in tables  # type: ignore[reportUnknownVariableType]
        )
        cursor.close()  # type: ignore[reportUnknownMemberType]
        return result

    def query_exists(self, query_name: str) -> bool:
        """
        Check if saved query exists in MS Access database.

        MS Access specific - saved queries are stored in the database.

        Args:
            query_name: Name of query to check.

        Returns:
            True if query exists, False otherwise.
        """
        self._ensure_connected()

        cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
        # Get list of views (queries) from Access system catalog
        views: Any = cursor.tables(tableType='VIEW')  # type: ignore[reportUnknownMemberType]
        result: bool = any(
            str(row.table_name).lower() == query_name.lower()  # type: ignore[reportUnknownMemberType]
            for row in views  # type: ignore[reportUnknownVariableType]
        )
        cursor.close()  # type: ignore[reportUnknownMemberType]
        return result

    def execute(self, sql: str) -> None:
        """
        Execute SQL statement without returning results.

        Args:
            sql: SQL statement to execute.

        Raises:
            Exception: If SQL execution fails.
        """
        self._ensure_connected()

        try:
            cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
            cursor.execute(sql)  # type: ignore[reportUnknownMemberType]
            cursor.close()  # type: ignore[reportUnknownMemberType]
        except Exception as e:
            log_and_raise(type(e)(f"Execute: SQL '{sql}' fehlgeschlagen: {e}"))

    def execute_with_params(self, sql: str, params: Tuple[Any, ...]) -> None:
        """
        Execute parameterized SQL statement.

        Args:
            sql: SQL statement with ? placeholders.
            params: Tuple of parameter values.

        Raises:
            Exception: If SQL execution fails.
        """
        self._ensure_connected()

        try:
            cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
            cursor.execute(sql, params)  # type: ignore[reportUnknownMemberType]
            cursor.close()  # type: ignore[reportUnknownMemberType]
        except Exception as e:
            log_and_raise(type(e)(f"Execute: SQL '{sql}' mit Parametern fehlgeschlagen: {e}"))

    def open_cursor(self, sql: str) -> DatabaseCursor:
        """
        Open cursor for SELECT query.

        Args:
            sql: SELECT statement to execute.

        Returns:
            Cursor object for iterating results.

        Raises:
            Exception: If query fails.
        """
        self._ensure_connected()

        try:
            cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
            cursor.execute(sql)  # type: ignore[reportUnknownMemberType]
            return cast(DatabaseCursor, cursor)
        except Exception as e:
            log_and_raise(type(e)(f"OpenCursor: SQL '{sql}' fehlgeschlagen: {e}"))
            raise  # For type checker - never reached

    def open_cursor_with_params(self, sql: str, params: Tuple[Any, ...]) -> DatabaseCursor:
        """
        Open cursor for parameterized SELECT query.

        Args:
            sql: SELECT statement with ? placeholders.
            params: Tuple of parameter values.

        Returns:
            Cursor object for iterating results.

        Raises:
            Exception: If query fails.
        """
        self._ensure_connected()

        try:
            cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
            cursor.execute(sql, params)  # type: ignore[reportUnknownMemberType]
            return cast(DatabaseCursor, cursor)
        except Exception as e:
            log_and_raise(type(e)(f"OpenCursor: SQL '{sql}' mit Parametern fehlgeschlagen: {e}"))
            raise  # For type checker - never reached

    def get_name(self) -> str:
        """
        Get database file path.

        Returns:
            Path to MS Access database file.
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

        cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
        columns_info: Any = cursor.columns(table=table_name)  # type: ignore[reportUnknownMemberType]
        columns: List[str] = [
            str(row.column_name)  # type: ignore[reportUnknownMemberType]
            for row in columns_info  # type: ignore[reportUnknownVariableType]
        ]
        cursor.close()  # type: ignore[reportUnknownMemberType]
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

        cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
        columns_info: Any = cursor.columns(table=table_name)  # type: ignore[reportUnknownMemberType]
        columns: List[Tuple[str, str]] = [
            (str(row.column_name), str(row.type_name))  # type: ignore[reportUnknownMemberType]
            for row in columns_info  # type: ignore[reportUnknownVariableType]
        ]
        cursor.close()  # type: ignore[reportUnknownMemberType]
        return columns

    def begin_transaction(self) -> None:
        """
        Start explicit transaction.

        Raises:
            RuntimeError: If transaction is already active.
        """
        self._ensure_connected()

        if self._in_transaction:
            log_and_raise(RuntimeError(
                "Transaction ist bereits aktiv. "
                "Verschachtelte Transaktionen werden nicht unterstützt."
            ))

        self._in_transaction = True
        log_msg("Transaction gestartet.")

    def is_in_transaction(self) -> bool:
        """
        Check if transaction is currently active.

        Returns:
            True if transaction is active, False otherwise.
        """
        return self._in_transaction

    def commit(self) -> None:
        """Commit current transaction."""
        self._ensure_connected()
        self._connection.commit()  # type: ignore[reportUnknownMemberType]
        self._in_transaction = False
        log_msg("Transaction committed.")

    def rollback(self) -> None:
        """Rollback current transaction."""
        self._ensure_connected()
        self._connection.rollback()  # type: ignore[reportUnknownMemberType]
        self._in_transaction = False
        log_msg("Transaction rollback.")

    def get_tables(self) -> List[str]:
        """
        Get list of all table names in database.

        Returns:
            List of table names (excluding system tables).
        """
        self._ensure_connected()

        cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
        tables: Any = cursor.tables(tableType='TABLE')  # type: ignore[reportUnknownMemberType]
        # Filter out MSys* system tables
        table_list: List[str] = [
            str(row.table_name)  # type: ignore[reportUnknownMemberType]
            for row in tables  # type: ignore[reportUnknownVariableType]
            if not str(row.table_name).startswith('MSys')  # type: ignore[reportUnknownMemberType]
        ]
        cursor.close()  # type: ignore[reportUnknownMemberType]
        return table_list

    def get_queries(self) -> List[str]:
        """
        Get list of all saved query names in database.

        MS Access specific method.

        Returns:
            List of query names.
        """
        self._ensure_connected()

        cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
        views: Any = cursor.tables(tableType='VIEW')  # type: ignore[reportUnknownMemberType]
        query_list: List[str] = [
            str(row.table_name)  # type: ignore[reportUnknownMemberType]
            for row in views  # type: ignore[reportUnknownVariableType]
        ]
        cursor.close()  # type: ignore[reportUnknownMemberType]
        return query_list

    def get_primary_key(self, table_name: str) -> List[str]:
        """
        Get primary key column(s) for a table.

        Uses pyodbc cursor.primaryKeys() method.

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

        cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
        pk_info: Any = cursor.primaryKeys(table=table_name)  # type: ignore[reportUnknownMemberType]
        # primaryKeys returns rows with: table_cat, table_schem, table_name,
        # column_name, key_seq, pk_name
        pk_columns: List[Tuple[int, str]] = []
        for row in pk_info:  # type: ignore[reportUnknownVariableType]
            pk_columns.append((int(row.key_seq), str(row.column_name)))  # type: ignore[reportUnknownMemberType]
        cursor.close()  # type: ignore[reportUnknownMemberType]

        # Sort by key_seq and return column names
        pk_columns.sort(key=lambda x: x[0])
        return [col[1] for col in pk_columns]

    def get_last_insert_rowid(self) -> int:
        """
        Get the row ID of the last inserted row.

        Uses MS Access @@IDENTITY to retrieve the last auto-generated ID.

        Returns:
            The row ID of the last inserted row.
            Returns 0 if no row was inserted or the table has no
            AUTOINCREMENT/COUNTER column.
        """
        self._ensure_connected()
        cursor: Any = self._connection.cursor()  # type: ignore[reportUnknownMemberType]
        cursor.execute("SELECT @@IDENTITY")  # type: ignore[reportUnknownMemberType]
        result: Any = cursor.fetchone()  # type: ignore[reportUnknownMemberType]
        cursor.close()  # type: ignore[reportUnknownMemberType]
        if result is None or result[0] is None:
            return 0
        return int(result[0])

    def _ensure_connected(self) -> None:
        """
        Ensure database connection is established.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._is_connected:
            log_and_raise(RuntimeError("MSAccessDB: Keine Datenbankverbindung."))


__all__ = ['MSAccessDB']
