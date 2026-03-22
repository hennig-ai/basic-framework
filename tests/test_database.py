"""
Tests for database module.

Tests AbstractDatabase interface and SQLiteDB implementation.
MSAccessDB tests require pyodbc and MS Access Database Engine.
"""

import os
import tempfile
import unittest

from basic_framework.database import (
    AbstractDatabase,
    SQLiteDB,
    MSAccessDB,
    DatabaseContainer,
    DatabaseIterator,
)
from basic_framework import ConditionEquals


class TestAbstractDatabase(unittest.TestCase):
    """Tests for AbstractDatabase interface."""

    def test_abstract_database_cannot_be_instantiated(self) -> None:
        """AbstractDatabase should not be directly instantiable."""
        with self.assertRaises(TypeError):
            AbstractDatabase("test.db")  # type: ignore[abstract]


class TestSQLiteDB(unittest.TestCase):
    """Tests for SQLiteDB implementation."""

    def setUp(self) -> None:
        """Create temporary database file."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

    def tearDown(self) -> None:
        """Clean up temporary files."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_init_creates_connection(self) -> None:
        """__init__() should create database connection."""
        db = SQLiteDB(self.db_path)

        self.assertTrue(db._is_connected)
        self.assertEqual(db.get_name(), self.db_path)

        db.close()

    def test_close_disconnects(self) -> None:
        """close() should disconnect from database."""
        db = SQLiteDB(self.db_path)
        db.close()

        self.assertFalse(db._is_connected)

    def test_context_manager(self) -> None:
        """SQLiteDB should work as context manager."""
        with SQLiteDB(self.db_path) as db:
            self.assertTrue(db._is_connected)  # type: ignore[attr-defined]

        self.assertFalse(db._is_connected)  # type: ignore[attr-defined]

    def test_table_exists_false_for_nonexistent(self) -> None:
        """table_exists() should return False for non-existent table."""
        db = SQLiteDB(self.db_path)

        result = db.table_exists("nonexistent_table")

        self.assertFalse(result)
        db.close()

    def test_table_exists_true_after_create(self) -> None:
        """table_exists() should return True after CREATE TABLE."""
        db = SQLiteDB(self.db_path)

        db.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        result = db.table_exists("test_table")

        self.assertTrue(result)
        db.close()

    def test_execute_creates_table(self) -> None:
        """execute() should create table successfully."""
        db = SQLiteDB(self.db_path)

        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

        self.assertTrue(db.table_exists("users"))
        db.close()

    def test_execute_with_params_inserts_data(self) -> None:
        """execute_with_params() should insert data with parameters."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

        db.execute_with_params("INSERT INTO users (name) VALUES (?)", ("Alice",))
        db.commit()

        cursor = db.open_cursor("SELECT name FROM users")
        row = cursor.fetchone()

        self.assertIsNotNone(row)
        assert row is not None  # Type narrowing for mypy
        self.assertEqual(row[0], "Alice")
        db.close()

    def test_open_cursor_returns_iterable(self) -> None:
        """open_cursor() should return iterable cursor."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE items (id INTEGER, value TEXT)")
        db.execute("INSERT INTO items VALUES (1, 'one')")
        db.execute("INSERT INTO items VALUES (2, 'two')")
        db.commit()

        cursor = db.open_cursor("SELECT * FROM items ORDER BY id")
        rows = list(cursor)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], (1, "one"))
        self.assertEqual(rows[1], (2, "two"))
        db.close()

    def test_open_cursor_with_params(self) -> None:
        """open_cursor_with_params() should filter with parameters."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE items (id INTEGER, value TEXT)")
        db.execute("INSERT INTO items VALUES (1, 'one')")
        db.execute("INSERT INTO items VALUES (2, 'two')")
        db.commit()

        cursor = db.open_cursor_with_params(
            "SELECT * FROM items WHERE id = ?", (2,)
        )
        rows = list(cursor)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], (2, "two"))
        db.close()

    def test_get_table_columns(self) -> None:
        """get_table_columns() should return column names."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE users (id INTEGER, name TEXT, email TEXT)")

        columns = db.get_table_columns("users")

        self.assertEqual(columns, ["id", "name", "email"])
        db.close()

    def test_get_table_columns_raises_for_nonexistent(self) -> None:
        """get_table_columns() should raise for non-existent table."""
        db = SQLiteDB(self.db_path)

        with self.assertRaises(ValueError):
            db.get_table_columns("nonexistent")

        db.close()

    def test_get_table_column_types(self) -> None:
        """get_table_column_types() should return column names and types."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE users (id INTEGER, name TEXT, score REAL)")

        columns = db.get_table_column_types("users")

        self.assertEqual(len(columns), 3)
        self.assertEqual(columns[0], ("id", "INTEGER"))
        self.assertEqual(columns[1], ("name", "TEXT"))
        self.assertEqual(columns[2], ("score", "REAL"))
        db.close()

    def test_get_tables(self) -> None:
        """get_tables() should return list of table names."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE users (id INTEGER)")
        db.execute("CREATE TABLE orders (id INTEGER)")

        tables = db.get_tables()

        self.assertIn("users", tables)
        self.assertIn("orders", tables)
        self.assertEqual(len(tables), 2)
        db.close()

    def test_commit_persists_changes(self) -> None:
        """commit() should persist changes."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE test (value TEXT)")
        db.execute("INSERT INTO test VALUES ('data')")
        db.commit()
        db.close()

        # Reopen and verify data persisted
        db2 = SQLiteDB(self.db_path)
        cursor = db2.open_cursor("SELECT * FROM test")
        rows = list(cursor)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "data")
        db2.close()

    def test_rollback_discards_changes(self) -> None:
        """rollback() should discard uncommitted changes."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE test (value TEXT)")
        db.commit()

        db.execute("INSERT INTO test VALUES ('data')")
        db.rollback()

        cursor = db.open_cursor("SELECT * FROM test")
        rows = list(cursor)

        self.assertEqual(len(rows), 0)
        db.close()

    def test_get_primary_key_single_column(self) -> None:
        """get_primary_key() should return single PK column."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

        pk = db.get_primary_key("users")

        self.assertEqual(pk, ["id"])
        db.close()

    def test_get_primary_key_composite(self) -> None:
        """get_primary_key() should return composite PK columns in order."""
        db = SQLiteDB(self.db_path)
        db.execute("""
            CREATE TABLE order_items (
                order_id INTEGER,
                item_id INTEGER,
                quantity INTEGER,
                PRIMARY KEY (order_id, item_id)
            )
        """)

        pk = db.get_primary_key("order_items")

        self.assertEqual(pk, ["order_id", "item_id"])
        db.close()

    def test_get_primary_key_no_pk(self) -> None:
        """get_primary_key() should return empty list if no PK."""
        db = SQLiteDB(self.db_path)
        db.execute("CREATE TABLE data (value TEXT, other TEXT)")

        pk = db.get_primary_key("data")

        self.assertEqual(pk, [])
        db.close()

    def test_get_primary_key_nonexistent_table(self) -> None:
        """get_primary_key() should raise for non-existent table."""
        db = SQLiteDB(self.db_path)

        with self.assertRaises(ValueError):
            db.get_primary_key("nonexistent")

        db.close()


class TestMSAccessDBImport(unittest.TestCase):
    """Tests for MSAccessDB import and basic structure."""

    def test_ms_access_db_class_exists(self) -> None:
        """MSAccessDB class should be importable."""
        self.assertTrue(hasattr(MSAccessDB, '__init__'))
        self.assertTrue(hasattr(MSAccessDB, 'close'))
        self.assertTrue(hasattr(MSAccessDB, 'table_exists'))
        self.assertTrue(hasattr(MSAccessDB, 'query_exists'))

    def test_ms_access_db_has_query_exists(self) -> None:
        """MSAccessDB should have query_exists method (MS Access specific)."""
        # query_exists is MS Access specific - not in AbstractDatabase
        self.assertTrue(callable(getattr(MSAccessDB, 'query_exists', None)))

    def test_ms_access_db_has_get_queries(self) -> None:
        """MSAccessDB should have get_queries method (MS Access specific)."""
        self.assertTrue(callable(getattr(MSAccessDB, 'get_queries', None)))


class TestDatabaseContainer(unittest.TestCase):
    """Tests for DatabaseContainer implementation."""

    def setUp(self) -> None:
        """Create temporary database with test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_container.db")

        self.db = SQLiteDB(self.db_path)

        # Create test table with data
        self.db.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT,
                active INTEGER
            )
        """)
        self.db.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@test.com', 1)")
        self.db.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@test.com', 1)")
        self.db.execute("INSERT INTO users VALUES (3, 'Charlie', 'charlie@test.com', 0)")
        self.db.commit()

    def tearDown(self) -> None:
        """Clean up."""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_init_with_table_name(self) -> None:
        """DatabaseContainer should initialize with table name."""
        container = DatabaseContainer(self.db, "users")

        self.assertTrue(container.field_exists("id"))
        self.assertTrue(container.field_exists("name"))
        self.assertTrue(container.field_exists("email"))
        self.assertFalse(container.field_exists("nonexistent"))

        container.close()

    def test_init_with_sql_query(self) -> None:
        """DatabaseContainer should initialize with SQL query."""
        container = DatabaseContainer(self.db, "SELECT id, name FROM users")

        self.assertTrue(container.field_exists("id"))
        self.assertTrue(container.field_exists("name"))
        self.assertFalse(container.field_exists("email"))  # Not in SELECT

        container.close()

    def test_init_nonexistent_table_raises(self) -> None:
        """DatabaseContainer should raise for non-existent table."""
        with self.assertRaises(ValueError):
            DatabaseContainer(self.db, "nonexistent_table")

    def test_get_list_of_fields(self) -> None:
        """get_list_of_fields_as_ref() should return column names."""
        container = DatabaseContainer(self.db, "users")

        fields = list(container.get_list_of_fields_as_ref())

        self.assertIn("id", fields)
        self.assertIn("name", fields)
        self.assertIn("email", fields)
        self.assertIn("active", fields)

        container.close()

    def test_get_technical_container_name(self) -> None:
        """get_technical_container_name() should return db.table."""
        container = DatabaseContainer(self.db, "users")

        name = container.get_technical_container_name()

        self.assertIn("users", name)
        container.close()

    def test_create_iterator_and_iterate(self) -> None:
        """create_iterator() should allow iteration over rows."""
        container = DatabaseContainer(self.db, "users")
        iterator = container.create_iterator()

        rows = []
        while not iterator.is_empty():
            rows.append({
                "id": iterator.value("id"),
                "name": iterator.value("name"),
            })
            iterator.pp()

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["name"], "Alice")
        self.assertEqual(rows[1]["name"], "Bob")
        self.assertEqual(rows[2]["name"], "Charlie")

        container.close()

    def test_create_iterator_with_condition(self) -> None:
        """create_iterator() with condition should filter at SQL level."""
        container = DatabaseContainer(self.db, "users")
        condition = ConditionEquals("active", 1)
        iterator = container.create_iterator(condition=condition)

        rows = []
        while not iterator.is_empty():
            rows.append(iterator.value("name"))
            iterator.pp()

        self.assertEqual(len(rows), 2)
        self.assertIn("Alice", rows)
        self.assertIn("Bob", rows)
        self.assertNotIn("Charlie", rows)

        container.close()

    def test_iterate_with_sql_query(self) -> None:
        """Iteration should work with SQL query."""
        container = DatabaseContainer(
            self.db,
            "SELECT name FROM users WHERE active = 1 ORDER BY name"
        )
        iterator = container.create_iterator()

        names = []
        while not iterator.is_empty():
            names.append(iterator.value("name"))
            iterator.pp()

        self.assertEqual(names, ["Alice", "Bob"])
        container.close()

    def test_get_value_nonexistent_column_raises(self) -> None:
        """get_value() should raise for non-existent column."""
        container = DatabaseContainer(self.db, "users")
        container.create_iterator()

        with self.assertRaises(ValueError):
            container.get_value(1, "nonexistent_column")

        container.close()

    def test_set_value_raises_not_implemented(self) -> None:
        """set_value() should raise NotImplementedError."""
        container = DatabaseContainer(self.db, "users")
        container.create_iterator()

        with self.assertRaises(NotImplementedError):
            container.set_value(1, "name", "NewName")

        container.close()

    def test_get_database_returns_db(self) -> None:
        """get_database() should return the database instance."""
        container = DatabaseContainer(self.db, "users")

        self.assertIs(container.get_database(), self.db)

        container.close()

    def test_empty_table_iteration(self) -> None:
        """Iteration over empty table should work."""
        self.db.execute("CREATE TABLE empty_table (id INTEGER)")
        self.db.commit()

        container = DatabaseContainer(self.db, "empty_table")
        iterator = container.create_iterator()

        self.assertTrue(iterator.is_empty())
        container.close()

    def test_multiple_iterations(self) -> None:
        """Multiple calls to create_iterator() should work."""
        container = DatabaseContainer(self.db, "users")

        # First iteration
        iterator1 = container.create_iterator()
        count1 = 0
        while not iterator1.is_empty():
            count1 += 1
            iterator1.pp()

        # Second iteration
        iterator2 = container.create_iterator()
        count2 = 0
        while not iterator2.is_empty():
            count2 += 1
            iterator2.pp()

        self.assertEqual(count1, 3)
        self.assertEqual(count2, 3)

        container.close()

    def test_is_writable_true_for_table(self) -> None:
        """is_writable should be True for table-based container."""
        container = DatabaseContainer(self.db, "users")

        self.assertTrue(container.is_writable)

        container.close()

    def test_is_writable_false_for_sql_query(self) -> None:
        """is_writable should be False for SQL query container."""
        container = DatabaseContainer(self.db, "SELECT * FROM users")

        self.assertFalse(container.is_writable)

        container.close()

    def test_get_table_name_returns_table(self) -> None:
        """get_table_name() should return table name for table container."""
        container = DatabaseContainer(self.db, "users")

        self.assertEqual(container.get_table_name(), "users")

        container.close()

    def test_get_table_name_empty_for_sql_query(self) -> None:
        """get_table_name() should return empty string for SQL query."""
        container = DatabaseContainer(self.db, "SELECT * FROM users")

        self.assertEqual(container.get_table_name(), "")

        container.close()


class TestDatabaseIterator(unittest.TestCase):
    """Tests for DatabaseIterator implementation."""

    def setUp(self) -> None:
        """Create temporary database with test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_iterator.db")

        self.db = SQLiteDB(self.db_path)

        # Create test table with data
        self.db.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT,
                price REAL,
                stock INTEGER
            )
        """)
        self.db.execute("INSERT INTO products VALUES (1, 'Apple', 1.50, 100)")
        self.db.execute("INSERT INTO products VALUES (2, 'Banana', 0.75, 150)")
        self.db.execute("INSERT INTO products VALUES (3, 'Cherry', 3.00, 50)")
        self.db.commit()

    def tearDown(self) -> None:
        """Clean up."""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_iterator_read_all_rows(self) -> None:
        """DatabaseIterator should read all rows."""
        container = DatabaseContainer(self.db, "products")
        iterator = container.create_iterator()

        rows = []
        while not iterator.is_empty():
            rows.append({
                "id": iterator.value("id"),
                "name": iterator.value("name"),
                "price": iterator.value("price"),
            })
            iterator.pp()

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["name"], "Apple")
        self.assertEqual(rows[1]["name"], "Banana")
        self.assertEqual(rows[2]["name"], "Cherry")

        iterator.finish()
        container.close()

    def test_iterator_reset(self) -> None:
        """DatabaseIterator reset() should restart from first row."""
        container = DatabaseContainer(self.db, "products")
        iterator = container.create_iterator()

        # Read first row
        first_name = iterator.value("name")
        iterator.pp()

        # Reset and read again
        iterator.reset()
        reset_name = iterator.value("name")

        self.assertEqual(first_name, reset_name)

        iterator.finish()
        container.close()

    def test_iterator_insert(self) -> None:
        """DatabaseIterator should insert new rows."""
        container = DatabaseContainer(self.db, "products")
        iterator = container.create_iterator(auto_commit=True)

        # Move to end
        while not iterator.is_empty():
            iterator.pp()

        # Insert new row
        iterator.start_insert()
        iterator.set_value("id", 4)
        iterator.set_value("name", "Date")
        iterator.set_value("price", 5.00)
        iterator.set_value("stock", 25)
        iterator.pp()

        iterator.finish()

        # Verify insert
        cursor = self.db.open_cursor("SELECT name FROM products WHERE id = 4")
        row = cursor.fetchone()
        cursor.close()

        self.assertIsNotNone(row)
        assert row is not None  # Type narrowing for mypy
        self.assertEqual(row[0], "Date")

        container.close()

    def test_iterator_update(self) -> None:
        """DatabaseIterator should update existing rows."""
        container = DatabaseContainer(self.db, "products")
        iterator = container.create_iterator(auto_commit=True)

        # Find Apple and update price
        while not iterator.is_empty():
            if iterator.value("name") == "Apple":
                iterator.start_update()
                iterator.set_value("price", 2.00)
            iterator.pp()

        iterator.finish()

        # Verify update
        cursor = self.db.open_cursor("SELECT price FROM products WHERE name = 'Apple'")
        row = cursor.fetchone()
        cursor.close()

        assert row is not None  # Type narrowing for mypy
        self.assertEqual(row[0], 2.00)

        container.close()

    def test_iterator_delete(self) -> None:
        """DatabaseIterator should delete rows."""
        container = DatabaseContainer(self.db, "products")
        iterator = container.create_iterator(auto_commit=True)

        # Delete Banana
        while not iterator.is_empty():
            if iterator.value("name") == "Banana":
                iterator.delete()
            iterator.pp()

        iterator.finish()

        # Verify delete
        cursor = self.db.open_cursor("SELECT COUNT(*) FROM products")
        count_row = cursor.fetchone()
        cursor.close()
        assert count_row is not None  # Type narrowing for mypy
        count = count_row[0]

        self.assertEqual(count, 2)

        cursor = self.db.open_cursor("SELECT name FROM products WHERE name = 'Banana'")
        row = cursor.fetchone()
        cursor.close()

        self.assertIsNone(row)

        container.close()

    def test_iterator_auto_start_insert_on_empty(self) -> None:
        """set_value() should auto-start INSERT when at end."""
        container = DatabaseContainer(self.db, "products")
        iterator = container.create_iterator(auto_commit=True)

        # Move to end
        while not iterator.is_empty():
            iterator.pp()

        # set_value without start_insert should auto-start INSERT
        iterator.set_value("id", 5)
        iterator.set_value("name", "Elderberry")
        iterator.set_value("price", 8.00)
        iterator.set_value("stock", 10)
        iterator.pp()

        iterator.finish()

        # Verify
        cursor = self.db.open_cursor("SELECT name FROM products WHERE id = 5")
        row = cursor.fetchone()
        cursor.close()

        assert row is not None  # Type narrowing for mypy
        self.assertEqual(row[0], "Elderberry")

        container.close()

    def test_iterator_auto_start_update_on_current_row(self) -> None:
        """set_value() should auto-start UPDATE when on current row."""
        container = DatabaseContainer(self.db, "products")
        iterator = container.create_iterator(auto_commit=True)

        # On first row, set_value without start_update should auto-start UPDATE
        iterator.set_value("stock", 200)
        iterator.pp()

        iterator.finish()

        # Verify
        cursor = self.db.open_cursor("SELECT stock FROM products WHERE id = 1")
        row = cursor.fetchone()
        cursor.close()

        assert row is not None  # Type narrowing for mypy
        self.assertEqual(row[0], 200)

        container.close()

    def test_iterator_write_not_allowed_on_sql_query(self) -> None:
        """Write operations should fail on SQL query containers."""
        container = DatabaseContainer(self.db, "SELECT * FROM products")
        iterator = container.create_iterator()

        with self.assertRaises(ValueError):
            iterator.start_insert()

        with self.assertRaises(ValueError):
            iterator.start_update()

        with self.assertRaises(ValueError):
            iterator.delete()

        iterator.finish()
        container.close()

    def test_iterator_returns_database_iterator_type(self) -> None:
        """create_iterator() should return DatabaseIterator instance."""
        container = DatabaseContainer(self.db, "products")
        iterator = container.create_iterator()

        self.assertIsInstance(iterator, DatabaseIterator)

        iterator.finish()
        container.close()


if __name__ == "__main__":
    unittest.main()
