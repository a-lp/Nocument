import sqlite3

from ..sqlite_store import SqliteStore
from .repository import ITemplateRepository, RepositoryError, TemplateFilter
from .template import DocumentTemplate, DocumentTemplateSummary

SCHEMA = """
CREATE TABLE IF NOT EXISTS document_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    origin TEXT NOT NULL,
    source TEXT,
    docx BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS document_templates_updated_at ON document_templates (updated_at DESC);
"""
SUMMARY_COLUMNS = "id, name, description, version, origin, source, created_at, updated_at"


class SqliteTemplateRepository(SqliteStore, ITemplateRepository):
    """
    DocumentTemplates saved in a SQLite file (by default the same file as the content blocks): one row per template
    in the document_templates table, with the Word file as a BLOB, not read for the summaries.
    """
    SCHEMA = SCHEMA
    ERROR = RepositoryError

    def get(self, template_id: str) -> DocumentTemplate | None:
        row = self._run(lambda connection: connection.execute(
            f"SELECT {SUMMARY_COLUMNS}, docx FROM document_templates WHERE id = ?", (template_id,)
        ).fetchone())
        if row is None:
            return None
        return DocumentTemplate(
            bytes(row["docx"]), row["name"], row["description"], row["version"], row["origin"], row["source"],
            row["id"], row["created_at"], row["updated_at"],
        )

    def list_summaries(self, criteria: TemplateFilter | None = None, skip: int = 0,
                       limit: int = 50) -> list[DocumentTemplateSummary]:
        where, parameters = self._where(criteria)
        rows = self._run(lambda connection: connection.execute(
            f"SELECT {SUMMARY_COLUMNS} FROM document_templates{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (*parameters, limit, skip),
        ).fetchall())
        return [self._to_summary(row) for row in rows]

    def count(self, criteria: TemplateFilter | None = None) -> int:
        where, parameters = self._where(criteria)
        return self._run(lambda connection: connection.execute(
            f"SELECT COUNT(*) FROM document_templates{where}", parameters
        ).fetchone()[0])

    def save(self, template: DocumentTemplate) -> None:
        values = (
            template.id, template.name, template.description, template.version, template.origin, template.source,
            sqlite3.Binary(template.docx), template.created_at, template.updated_at,
        )
        self._run(lambda connection: connection.execute(
            "INSERT INTO document_templates (id, name, description, version, origin, source, docx, created_at,"
            " updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (id) DO UPDATE SET name = excluded.name, description = excluded.description,"
            " version = excluded.version, origin = excluded.origin, source = excluded.source, docx = excluded.docx,"
            " created_at = excluded.created_at, updated_at = excluded.updated_at",
            values,
        ))

    def delete(self, template_id: str) -> bool:
        return self._run(lambda connection: connection.execute(
            "DELETE FROM document_templates WHERE id = ?", (template_id,)
        ).rowcount) == 1

    @staticmethod
    def _where(criteria: TemplateFilter | None) -> tuple[str, list]:
        """WHERE clause (with the leading space, "" without criteria) and its parameters."""
        criteria = criteria or TemplateFilter()
        conditions, parameters = [], []
        if criteria.text:
            conditions.append("(contains_text(name, ?) OR contains_text(description, ?))")
            parameters.extend([criteria.text, criteria.text])
        if criteria.origins:
            conditions.append(f"origin IN ({', '.join('?' * len(criteria.origins))})")
            parameters.extend(criteria.origins)
        return (f" WHERE {' AND '.join(conditions)}" if conditions else ""), parameters

    @staticmethod
    def _to_summary(row: sqlite3.Row) -> DocumentTemplateSummary:
        return DocumentTemplateSummary(
            row["id"], row["name"], row["description"], row["version"], row["origin"], row["source"],
            row["created_at"], row["updated_at"],
        )
