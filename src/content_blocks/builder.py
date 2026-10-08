import base64

from ..builder.content_interface import IDocumentContent, parse_content_id
from ..builder.contents import content_from_dict
from ..i18n import t
from .content_block import ContentBlock, utc_now


class ContentBlockBuilder:
    """
    Builder of the ContentBlocks: adds, moves and removes contents and creates the block with build, which checks
    its consistency and updates the dates. The add_* methods validate the data like the API (content_from_dict).

        block = (ContentBlockBuilder()
                 .with_title("Release notes")
                 .with_description("New features and fixes of the version")
                 .add_heading("New features", level=1)
                 .add_paragraph("<p>This version introduces...</p>")
                 .add_table([["ID", "Description"], ["101", "PDF export"]], caption="Table 1: changes", header=True)
                 .build())
    """

    def __init__(self, block_id: str | None = None):
        """block_id: hexadecimal ID of the block (by default one is generated)."""
        self._id = parse_content_id(block_id)
        self._title = ""
        self._description = ""
        self._source: str | None = None
        self._contents: list[IDocumentContent] = []
        self._created_at: str | None = None

    @classmethod
    def from_block(cls, block: ContentBlock) -> "ContentBlockBuilder":
        """Builder starting from an existing block, to edit it (ID and creation date stay)."""
        builder = cls(block.id)
        builder._title = block.title
        builder._description = block.description
        builder._source = block.source
        builder._contents = list(block.contents)
        builder._created_at = block.created_at
        return builder

    def with_title(self, title: str) -> "ContentBlockBuilder":
        """Sets the title of the block."""
        if not isinstance(title, str):
            raise ValueError(t("errors.blockTitleNotString"))
        self._title = title.strip()
        return self

    def with_description(self, description: str) -> "ContentBlockBuilder":
        """Sets the description of the block (what it contains)."""
        if not isinstance(description, str):
            raise ValueError(t("errors.blockDescriptionNotString"))
        self._description = description.strip()
        return self

    def with_source(self, source: str | None) -> "ContentBlockBuilder":
        """Sets the name of the Word file the block was imported from (None if created by hand)."""
        if source is not None and not isinstance(source, str):
            raise ValueError(t("errors.blockSourceNotString"))
        self._source = (source or "").strip() or None
        return self

    def add(self, content: IDocumentContent, position: int | None = None) -> "ContentBlockBuilder":
        """Adds a content at the end or at the given position."""
        if position is None:
            self._contents.append(content)
        else:
            self._contents.insert(self._check_position(position, len(self._contents)), content)
        return self

    def add_heading(self, text: str, level: int = 1, style: str | None = None, formatting: dict | None = None,
                    position: int | None = None) -> "ContentBlockBuilder":
        """Adds a heading (formatting as in Formatting.from_dict)."""
        return self.add(content_from_dict(
            {"type": "heading", "text": text, "level": level, "style": style, "formatting": formatting}
        ), position)

    def add_paragraph(self, html: str, style: str | None = None, formatting: dict | None = None,
                      position: int | None = None) -> "ContentBlockBuilder":
        """Adds a paragraph written in HTML (see html_converter)."""
        return self.add(content_from_dict(
            {"type": "paragraph", "html": html, "style": style, "formatting": formatting}
        ), position)

    def add_image(self, data: bytes, filename: str = "image", width: float | None = None, alignment: str | None = None,
                  position: int | None = None) -> "ContentBlockBuilder":
        """Adds an image (PNG, JPEG, GIF, BMP or TIFF); width in centimeters."""
        return self.add(content_from_dict({
            "type": "image",
            "data": base64.b64encode(data).decode("ascii"),
            "filename": filename,
            "width": width,
            "alignment": alignment,
        }), position)

    def add_table(self, rows: list[list[str]], caption: str = "", caption_position: str = "below", header: bool = False,
                  style: str | None = None, alignment: str | None = None,
                  position: int | None = None) -> "ContentBlockBuilder":
        """Adds a table with an optional caption."""
        return self.add(content_from_dict({
            "type": "table",
            "rows": rows,
            "caption": caption,
            "caption_position": caption_position,
            "header": header,
            "style": style,
            "alignment": alignment,
        }), position)

    def remove(self, content_id: str) -> "ContentBlockBuilder":
        """Removes the content with the given ID; raises ValueError if it does not exist."""
        self._contents.pop(self._index_of(content_id))
        return self

    def move(self, content_id: str, position: int) -> "ContentBlockBuilder":
        """Moves the content with the given ID to the given position (0 = first)."""
        content = self._contents.pop(self._index_of(content_id))
        self._contents.insert(self._check_position(position, len(self._contents)), content)
        return self

    def clear(self) -> "ContentBlockBuilder":
        """Removes all the contents (e.g. to replace them)."""
        self._contents = []
        return self

    def build(self) -> ContentBlock:
        """Creates the ContentBlock; raises ValueError if two contents have the same ID."""
        content_ids = [content.content_id for content in self._contents]
        if len(set(content_ids)) != len(content_ids):
            raise ValueError(t("errors.duplicateContentId"))
        now = utc_now()
        return ContentBlock(
            self._id, list(self._contents), self._title, self._description, self._source, self._created_at or now, now
        )

    def _index_of(self, content_id: str) -> int:
        """Position of the content with the given ID; raises ValueError if it does not exist."""
        for index, content in enumerate(self._contents):
            if content.content_id == content_id:
                return index
        raise ValueError(t("errors.contentNotInBlock", id=content_id))

    @staticmethod
    def _check_position(position: int, size: int) -> int:
        """Validates an insertion position (from 0 to size included)."""
        if isinstance(position, bool) or not isinstance(position, int) or not 0 <= position <= size:
            raise ValueError(t("errors.invalidPosition", position=position))
        return position
