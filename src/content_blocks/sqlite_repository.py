import json
import sqlite3

from ..sqlite_store import SqliteStore
from .content_block import ContentBlock, ContentBlockSummary
from .repository import ContentBlockFilter, IContentBlockRepository, RepositoryError

SCHEMA = """
CREATE TABLE IF NOT EXISTS content_blocks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    source TEXT,
    content_types TEXT NOT NULL,
    contents TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS content_blocks_updated_at ON content_blocks (updated_at DESC);
CREATE INDEX IF NOT EXISTS content_blocks_source ON content_blocks (source);
"""
SUMMARY_COLUMNS = "id, title, description, source, content_types, created_at, updated_at"


class SqliteContentBlockRepository(SqliteStore, IContentBlockRepository):
    """
    ContentBlocks saved in a SQLite file, with no database server: one row per block in the content_blocks table.
    The contents are a JSON column (images in base64, as in ContentBlock.to_dict); the content types have their own
    column, so the summaries are read without the contents. Title and description are searched as literal text,
    case insensitive also beyond ASCII (e.g. "È" finds "è"). Connections and transactions: see SqliteStore.
    """
    SCHEMA = SCHEMA
    ERROR = RepositoryError

    def get(self, block_id: str) -> ContentBlock | None:
        """Block with the given ID, or None."""
        row = self._run(lambda connection: connection.execute(
            "SELECT id, title, description, source, contents, created_at, updated_at FROM content_blocks WHERE id = ?",
            (block_id,),
        ).fetchone())
        return self._to_block(row) if row is not None else None

    def search(self, criteria: ContentBlockFilter | None = None, skip: int = 0, limit: int = 50) -> list[ContentBlock]:
        """Complete blocks matching the criteria, from the most recent."""
        where, parameters = self._where(criteria)
        rows = self._run(lambda connection: connection.execute(
            "SELECT id, title, description, source, contents, created_at, updated_at FROM content_blocks"
            f"{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (*parameters, limit, skip),
        ).fetchall())
        return [self._to_block(row) for row in rows]

    def list_summaries(self, criteria: ContentBlockFilter | None = None, skip: int = 0,
                       limit: int = 50) -> list[ContentBlockSummary]:
        """Summaries from the most recent, without reading the contents (and their images)."""
        where, parameters = self._where(criteria)
        rows = self._run(lambda connection: connection.execute(
            f"SELECT {SUMMARY_COLUMNS} FROM content_blocks{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (*parameters, limit, skip),
        ).fetchall())
        return [
            ContentBlockSummary(row["id"], row["title"], row["description"], row["source"],
                                json.loads(row["content_types"]), row["created_at"], row["updated_at"])
            for row in rows
        ]

    def count(self, criteria: ContentBlockFilter | None = None) -> int:
        """Number of blocks matching the criteria."""
        where, parameters = self._where(criteria)
        return self._run(lambda connection: connection.execute(
            f"SELECT COUNT(*) FROM content_blocks{where}", parameters
        ).fetchone()[0])

    def sources(self) -> list[str]:
        """Distinct source files, in alphabetical order."""
        rows = self._run(lambda connection: connection.execute(
            "SELECT DISTINCT source FROM content_blocks WHERE source IS NOT NULL AND source <> ''"
        ).fetchall())
        return sorted(row["source"] for row in rows)

    def save(self, block: ContentBlock) -> None:
        """Creates or replaces the row of the block."""
        document = block.to_dict()
        values = (
            document["id"], document["title"], document["description"], document["source"],
            json.dumps([content["type"] for content in document["contents"]]),
            json.dumps(document["contents"], ensure_ascii=False),
            document["created_at"], document["updated_at"],
        )
        self._run(lambda connection: connection.execute(
            "INSERT INTO content_blocks (id, title, description, source, content_types, contents, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (id) DO UPDATE SET title = excluded.title, description = excluded.description,"
            " source = excluded.source, content_types = excluded.content_types, contents = excluded.contents,"
            " created_at = excluded.created_at, updated_at = excluded.updated_at",
            values,
        ))

    def delete(self, block_id: str) -> bool:
        """Deletes the row of the block."""
        return self._run(lambda connection: connection.execute(
            "DELETE FROM content_blocks WHERE id = ?", (block_id,)
        ).rowcount) == 1

    @staticmethod
    def _where(criteria: ContentBlockFilter | None) -> tuple[str, list]:
        """WHERE clause (with the leading space, "" without criteria) and its parameters."""
        criteria = criteria or ContentBlockFilter()
        conditions, parameters = [], []
        if criteria.title:
            conditions.append("contains_text(title, ?)")
            parameters.append(criteria.title)
        if criteria.description:
            conditions.append("contains_text(description, ?)")
            parameters.append(criteria.description)
        if criteria.filters_origin:
            origins = []
            if criteria.sources:
                origins.append(f"source IN ({', '.join('?' * len(criteria.sources))})")
                parameters.extend(criteria.sources)
            if criteria.manual:
                origins.append("source IS NULL OR source = ''")
            conditions.append(f"({' OR '.join(origins)})")
        return (f" WHERE {' AND '.join(conditions)}" if conditions else ""), parameters

    @staticmethod
    def _to_block(row: sqlite3.Row) -> ContentBlock:
        """Block rebuilt from its row."""
        return ContentBlock.from_dict({
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "source": row["source"],
            "contents": json.loads(row["contents"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
