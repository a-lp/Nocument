"""
Base of the repositories saved in a SQLite file (content blocks, templates): connections, schema and errors.
All the repositories can share the same file (NOCUMENT_DATABASE), each with its own tables.
"""
from pathlib import Path
import sqlite3
import threading


class SqliteStoreError(Exception):
    """SQLite error raised by _run; each repository converts it into its own RepositoryError."""


class SqliteStore:
    """
    Every operation opens its own connection: the repository can be used by several threads and, thanks to the
    WAL journal, by several processes (gunicorn workers) on the same file. Text is searched with contains_text, literal
    and case insensitive also beyond ASCII (e.g. "È" finds "è").
    Subclasses set SCHEMA (CREATE ... IF NOT EXISTS statements) and ERROR (exception raised for database errors).
    """
    SCHEMA = ""
    ERROR: type[Exception] = SqliteStoreError

    def __init__(self, path: str | Path):
        """path: database file, created with its folder at the first operation; ":memory:" is not supported."""
        self.path = Path(path)
        self._schema_ready = False
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        """New connection, with rows by column name, the search function and, the first time, the schema."""
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        # Literal and case insensitive (casefold) search: LIKE would treat % and _ as wildcards and ignore the
        # case only for ASCII letters.
        connection.create_function(
            "contains_text", 2, lambda text, search: search.casefold() in (text or "").casefold(), deterministic=True
        )
        if not self._schema_ready:
            with self._lock:
                if not self._schema_ready:
                    connection.execute("PRAGMA journal_mode = WAL")
                    connection.executescript(self.SCHEMA)
                    self._schema_ready = True
        return connection

    def _run(self, operation):
        """Runs an operation in a transaction (committed if it succeeds), converting SQLite errors into ERROR."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = self._connect()
            try:
                with connection:
                    return operation(connection)
            finally:
                connection.close()
        except (sqlite3.Error, OSError) as error:
            raise self.ERROR(f"Database error: {error}") from error
