from abc import ABC, abstractmethod
import re
import uuid

from docx.document import Document

from ..i18n import t

CONTENT_ID = re.compile(r"^[0-9a-f]{32}$")


def new_content_id() -> str:
    """New hexadecimal ID (32 digits, UUID4) for a content or a ContentBlock."""
    return uuid.uuid4().hex


def parse_content_id(value) -> str:
    """ID received in the JSON: generates a new one if missing; raises ValueError if it is not hexadecimal."""
    if value is None:
        return new_content_id()
    if not isinstance(value, str) or not CONTENT_ID.match(value):
        raise ValueError(t("errors.invalidContentId"))
    return value


class IDocumentContent(ABC):
    """
    Content of a document: heading, paragraph, image or table. It is inserted into a Word document
    (DocumentBuilder) and makes up the ContentBlocks. content_id is its hexadecimal ID.
    """

    content_id: str

    @abstractmethod
    def build(self, document: Document) -> list:
        """
        Creates the content at the end of the document and returns its XML elements in insertion order
        (DocumentBuilder moves them to the requested position).
        """

    @abstractmethod
    def serialize(self) -> dict:
        """JSON of the content ({"type", "id", ...}), in the format read by contents.content_from_dict."""
