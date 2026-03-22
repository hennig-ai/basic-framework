"""
MS Access database implementation.

This module provides a concrete implementation of AbstractDatabase
for Microsoft Access databases using pyodbc.

Requirements:
    - pyodbc: pip install pyodbc
    - Microsoft Access Database Engine (free download from Microsoft)
"""

from typing import Any, List, Tuple, TYPE_CHECKING, cast

from .abstract_database import AbstractDatabase, DatabaseCursor
from ..proc_frame import log_and_raise, log_msg

if TYPE_CHECKING:
    import pyodbc


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
            pyodbc.Error: If connection fails.
        """
        try:
            import pyodbc
        except ImportError:
            log_and_raise(ImportError(
                "pyodbc ist nicht installiert. "
                "Bitte installieren mit: pip install pyodbc"
            ))

        self._connection: "pyodbc.Connection"
        self._db_path: str = connection_info
        self._is_connected: bool = False
        self._in_transaction: bool = False

        # Build connection string for MS Access
        connection_string = (
            f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};"
            f"DBQ={connection_info};"
        )

        try:
            self._connection = pyodbc.connect(connection_string)
            self._is_connected = True
            log_msg(f"MS Access Datenbank '{connection_info}' wurde geöffnet.")
        except pyodbc.Error as e:
            log_and_raise(pyodbc.Error(
                f"MS Access Verbindung fehlgeschlagen für '{connection_info}': {e}"
            ))

    def close(self) -> None:
        """
        Close MS Access database connection.
        """
        if self._is_connected:
            log_msg(f"MS Access Datenbankverbindung zu '{self._db_path}' wird geschlossen...")
            self._connection.close()
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

        cursor = self._connection.cursor()
        # Get list of tables from Access system catalog
        tables = cursor.tables(tableType='TABLE')
        result = any(row.table_name.lower() == table_name.lower() for row in tables)
        cursor.close()
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

        cursor = self._connection.cursor()
        # Get list of views (queries) from Access system catalog
        views = cursor.tables(tableType='VIEW')
        result = any(row.table_name.lower() == query_name.lower() for row in views)
        cursor.close()
        return result

    def execute(self, sql: str) -> None:
        """
        Execute SQL statement without returning results.

        Args:
            sql: SQL statement to execute.

        Raises:
            pyodbc.Error: If SQL execution fails.
        """
        self._ensure_connected()
        self._ensure_pyodbc_imported()
        import pyodbc

        try:
            cursor = self._connection.cursor()
            cursor.execute(sql)
            cursor.close()
        except pyodbc.Error as e:
            log_and_raise(pyodbc.Error(f"Execute: SQL '{sql}' fehlgeschlagen: {e}"))

    def execute_with_params(self, sql: str, params: Tuple[Any, ...]) -> None:
        """
        Execute parameterized SQL statement.

        Args:
            sql: SQL statement with ? placeholders.
            params: Tuple of parameter values.

        Raises:
            pyodbc.Error: If SQL execution fails.
        """
        self._ensure_connected()
        self._ensure_pyodbc_imported()
        import pyodbc

        try:
            cursor = self._connection.cursor()
            cursor.execute(sql, params)
            cursor.close()
        except pyodbc.Error as e:
            log_and_raise(pyodbc.Error(f"Execute: SQL '{sql}' mit Parametern fehlgeschlagen: {e}"))

    def open_cursor(self, sql: str) -> DatabaseCursor:
        """
        Open cursor for SELECT query.

        Args:
            sql: SELECT statement to execute.

        Returns:
            Cursor object for iterating results.

        Raises:
            pyodbc.Error: If query fails.
        """
        self._ensure_connected()
        self._ensure_pyodbc_imported()
        import pyodbc

        try:
            cursor = self._connection.cursor()
            cursor.execute(sql)
            return cast(DatabaseCursor, cursor)
        except pyodbc.Error as e:
            log_and_raise(pyodbc.Error(f"OpenCursor: SQL '{sql}' fehlgeschlagen: {e}"))
            raise  # Für Type Checker - wird nie erreicht

    def open_cursor_with_params(self, sql: str, params: Tuple[Any, ...]) -> DatabaseCursor:
        """
        Open cursor for parameterized SELECT query.

        Args:
            sql: SELECT statement with ? placeholders.
            params: Tuple of parameter values.

        Returns:
            Cursor object for iterating results.

        Raises:
            pyodbc.Error: If query fails.
        """
        self._ensure_connected()
        self._ensure_pyodbc_imported()
        import pyodbc

        try:
            cursor = self._connection.cursor()
            cursor.execute(sql, params)
            return cast(DatabaseCursor, cursor)
        except pyodbc.Error as e:
            log_and_raise(pyodbc.Error(f"OpenCursor: SQL '{sql}' mit Parametern fehlgeschlagen: {e}"))
            raise  # Für Type Checker - wird nie erreicht

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

        cursor = self._connection.cursor()
        columns_info = cursor.columns(table=table_name)
        columns = [row.column_name for row in columns_info]
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

        cursor = self._connection.cursor()
        columns_info = cursor.columns(table=table_name)
        columns = [(row.column_name, row.type_name) for row in columns_info]
        cursor.close()
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
        self._connection.commit()
        self._in_transaction = False
        log_msg("Transaction committed.")

    def rollback(self) -> None:
        """Rollback current transaction."""
        self._ensure_connected()
        self._connection.rollback()
        self._in_transaction = False
        log_msg("Transaction rollback.")

    def get_tables(self) -> List[str]:
        """
        Get list of all table names in database.

        Returns:
            List of table names (excluding system tables).
        """
        self._ensure_connected()

        cursor = self._connection.cursor()
        tables = cursor.tables(tableType='TABLE')
        # Filter out MSys* system tables
        table_list = [
            row.table_name for row in tables
            if not row.table_name.startswith('MSys')
        ]
        cursor.close()
        return table_list

    def get_queries(self) -> List[str]:
        """
        Get list of all saved query names in database.

        MS Access specific method.

        Returns:
            List of query names.
        """
        self._ensure_connected()

        cursor = self._connection.cursor()
        views = cursor.tables(tableType='VIEW')
        query_list = [row.table_name for row in views]
        cursor.close()
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

        cursor = self._connection.cursor()
        pk_info = cursor.primaryKeys(table=table_name)
        # primaryKeys returns rows with: table_cat, table_schem, table_name,
        # column_name, key_seq, pk_name
        pk_columns = []
        for row in pk_info:
            pk_columns.append((row.key_seq, row.column_name))
        cursor.close()

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
        cursor = self._connection.cursor()
        cursor.execute("SELECT @@IDENTITY")
        result = cursor.fetchone()
        cursor.close()
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

    def _ensure_pyodbc_imported(self) -> None:
        """
        Ensure pyodbc is available.

        Raises:
            ImportError: If pyodbc is not installed.
        """
        try:
            import pyodbc  # noqa: F401
        except ImportError:
            log_and_raise(ImportError(
                "pyodbc ist nicht installiert. "
                "Bitte installieren mit: pip install pyodbc"
            ))


__all__ = ['MSAccessDB']
