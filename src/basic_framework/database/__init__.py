"""
Database module for basic_framework.

Provides abstract database interface and concrete implementations
for different database backends.

Classes:
    AbstractDatabase: Abstract base class for all database connections
    DatabaseCursor: Protocol defining cursor interface
    SQLiteDB: SQLite implementation (no extra dependencies)
    MSAccessDB: MS Access implementation (requires pyodbc)
    DatabaseContainer: Container for database tables/queries
    DatabaseIterator: Iterator with read/write support for databases

Example usage with SQLite (reading):
    from basic_framework.database import SQLiteDB, DatabaseContainer

    db = SQLiteDB("my_database.db")

    container = DatabaseContainer(db, "users")
    iterator = container.create_iterator()

    while not iterator.is_empty():
        print(iterator.value("name"))
        iterator.pp()

    db.close()

Example usage with SQLite (writing):
    container = DatabaseContainer(db, "users")
    iterator = container.create_iterator()

    # Insert new row
    iterator.start_insert()
    iterator.set_value("name", "New User")
    iterator.set_value("email", "new@example.com")
    iterator.pp()  # Commits the insert

    # Update existing row
    while not iterator.is_empty():
        if iterator.value("status") == "old":
            iterator.start_update()
            iterator.set_value("status", "archived")
        iterator.pp()

    iterator.finish()
    db.close()
"""

from .abstract_database import AbstractDatabase, DatabaseCursor
from .sqlite_db import SQLiteDB
from .ms_access_db import MSAccessDB
from .database_container import DatabaseContainer
from .database_iterator import DatabaseIterator

__all__ = [
    'AbstractDatabase',
    'DatabaseCursor',
    'SQLiteDB',
    'MSAccessDB',
    'DatabaseContainer',
    'DatabaseIterator',
]
