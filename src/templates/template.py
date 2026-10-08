from dataclasses import dataclass, field
from uuid import uuid4

from ..content_blocks.content_block import utc_now

# How a template was created: saved from a document of the Builder, or imported from a Word file.
BUILDER = "builder"
IMPORT = "import"
ORIGINS = (BUILDER, IMPORT)


@dataclass
class DocumentTemplateSummary:
    """Data of a DocumentTemplate for lists, without the Word file."""
    id: str
    name: str
    description: str
    version: str
    origin: str
    source: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        """JSON of the summary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "origin": self.origin,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class DocumentTemplate:
    """
    Template of a document: a Word file (.docx) whose structure, the graph of the Builder, holds the preallocated
    nodes (headings, paragraphs, tables, ...) of the documents created from it.
    id is hexadecimal; name, description and version describe it; origin is BUILDER or IMPORT and source the name of
    the Word file it comes from. Saved with an ITemplateRepository.
    """
    docx: bytes
    name: str
    description: str = ""
    version: str = ""
    origin: str = IMPORT
    source: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def summary(self) -> DocumentTemplateSummary:
        """Summary for lists."""
        return DocumentTemplateSummary(
            self.id, self.name, self.description, self.version, self.origin, self.source, self.created_at,
            self.updated_at,
        )
