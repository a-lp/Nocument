from dataclasses import dataclass, field
from datetime import datetime, timezone

from docx.document import Document

from ..builder.content_interface import IDocumentContent, new_content_id, parse_content_id
from ..builder.contents import content_from_dict
from ..i18n import t


def utc_now() -> str:
    """Current date and time in UTC, ISO 8601 (sortable as strings)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class ContentBlockSummary:
    """Data of a ContentBlock for lists, without the contents (which can include heavy images)."""
    id: str
    title: str
    description: str
    source: str | None
    content_types: list[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        """JSON of the summary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "content_count": len(self.content_types),
            "content_types": self.content_types,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ContentBlock:
    """
    Reusable block of contents: headings, paragraphs, images and tables (IDocumentContent) in order.
    id and the content_ids of the contents are hexadecimal; title and description describe the block; source is the
    name of the Word file it was imported from (None if created by hand).
    It is created and edited with ContentBlockBuilder and saved with an IContentBlockRepository;
    build inserts it into a Word document as a single content.
    """
    id: str = field(default_factory=new_content_id)
    contents: list[IDocumentContent] = field(default_factory=list)
    title: str = ""
    description: str = ""
    source: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def find(self, content_id: str) -> IDocumentContent | None:
        """Content with the given ID, or None."""
        return next((content for content in self.contents if content.content_id == content_id), None)

    def build(self, document: Document) -> list:
        """Creates all the contents in order; it is inserted with DocumentBuilder.insert like any content."""
        return [element for content in self.contents for element in content.build(document)]

    def summary(self) -> ContentBlockSummary:
        """Summary for lists."""
        return ContentBlockSummary(
            self.id, self.title, self.description, self.source,
            [content.serialize()["type"] for content in self.contents], self.created_at, self.updated_at,
        )

    def to_dict(self) -> dict:
        """JSON of the block (API and database)."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "contents": [content.serialize() for content in self.contents],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, value) -> "ContentBlock":
        """Creates the block from the JSON of to_dict; raises ValueError if it is not valid."""
        if not isinstance(value, dict):
            raise ValueError(t("errors.blockNotObject"))
        contents = value.get("contents", [])
        if not isinstance(contents, list):
            raise ValueError(t("errors.contentsNotList"))
        title = value.get("title") or ""
        description = value.get("description") or ""
        source = value.get("source") or None
        if not isinstance(title, str) or not isinstance(description, str) or not isinstance(source, (str, type(None))):
            raise ValueError(t("errors.blockFieldsNotStrings"))
        block = cls(
            parse_content_id(value.get("id")), [content_from_dict(item) for item in contents], title, description, source
        )
        block.created_at = value.get("created_at") or block.created_at
        block.updated_at = value.get("updated_at") or block.updated_at
        return block
