from abc import ABC
from dataclasses import dataclass, field


class IContent(ABC):
    """
    Element of the structure of a document.
    id: index of the block in the body (see docx_utils.iter_body_blocks);
    anchor: id of the last block of the element, after which new contents are inserted;
    layout: position of the element inside a layout table (see SectionAnalyzer), None otherwise.
    Elements of a layout table have the table's block as id and anchor: they only move together with it, while
    they are edited and deleted by also giving layout (see DocumentBuilder.replace_layout); block is their
    paragraph or nested table (not serialized).
    """

    id: int | None
    anchor: int | None
    layout: int | None = None
    block = None

    def to_dict(self) -> dict:
        """JSON representation of the element, sent to the frontend."""
        raise NotImplementedError


@dataclass
class TextContent(IContent):
    """
    Text of a paragraph with its style. For editing in the Builder: html (see paragraph_reader.paragraph_html),
    direct formatting, has_image (the paragraph also contains images) and has_fields (hyperlinks or fields).
    """
    text: str
    style: str | None = None
    id: int | None = None
    anchor: int | None = None
    html: str = ""
    formatting: dict = field(default_factory=dict)
    has_image: bool = False
    has_fields: bool = False

    def to_dict(self) -> dict:
        """Type "paragraph" with text, style and the data for editing."""
        return {
            "type": "paragraph",
            "id": self.id,
            "anchor": self.anchor,
            "layout": self.layout,
            "text": self.text,
            "style": self.style,
            "html": self.html,
            "formatting": self.formatting,
            "has_image": self.has_image,
            "has_fields": self.has_fields,
        }


@dataclass
class ImageContent(IContent):
    """Image contained in a paragraph, with the bytes and the MIME type of the original file."""
    data: bytes
    content_type: str
    filename: str
    id: int | None = None
    anchor: int | None = None

    def to_dict(self) -> dict:
        """Type "image" without the bytes (the frontend only shows a placeholder)."""
        return {"type": "image", "id": self.id, "anchor": self.anchor, "layout": self.layout, "filename": self.filename}


@dataclass
class Section(IContent):
    """Section introduced by a heading; contents can hold other sections of a lower level."""
    title: str
    level: int
    style: str | None = None
    contents: list[IContent] = field(default_factory=list)
    id: int | None = None
    anchor: int | None = None
    formatting: dict = field(default_factory=dict)
    has_fields: bool = False

    def to_dict(self) -> dict:
        """Type "heading" with title, level, style and nested contents."""
        return {
            "type": "heading",
            "id": self.id,
            "anchor": self.anchor,
            "layout": self.layout,
            "text": self.title,
            "level": self.level,
            "style": self.style,
            "formatting": self.formatting,
            "has_fields": self.has_fields,
            "children": [content.to_dict() for content in self.contents],
        }
