import base64
import binascii
from copy import deepcopy
from dataclasses import dataclass, field
from io import BytesIO

from docx.document import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.image.exceptions import UnrecognizedImageError
from docx.image.image import Image
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph

from ..compilers.docx_utils import style_heading_level
from ..i18n import t
from .content_interface import IDocumentContent, new_content_id, parse_content_id
from .formatting import ALIGNMENTS, Formatting
from .html_converter import HtmlBlock, html_to_blocks
from .rich_text import append_html_runs
from .styles import find_style
from .word_table import WordTable

BULLET_STYLES = ("List Bullet", "List Bullet 2", "List Bullet 3")
NUMBER_STYLES = ("List Number", "List Number 2", "List Number 3")
LIST_INDENT = Cm(0.63)


@dataclass
class NewHeading(IDocumentContent):
    """Heading with a heading style of the document (by default "Heading <level>") and direct formatting."""
    text: str
    level: int
    style: str | None = None
    formatting: Formatting = field(default_factory=Formatting)
    # Heading this one replaces (edit): its paragraph properties and bookmarks are kept.
    original: Paragraph | None = field(default=None, repr=False, compare=False)
    content_id: str = field(default_factory=new_content_id)

    def serialize(self) -> dict:
        """Type "heading" with text, level, style and formatting."""
        return {
            "type": "heading",
            "id": self.content_id,
            "text": self.text,
            "level": self.level,
            "style": self.style,
            "formatting": self.formatting.to_dict(),
        }

    def build(self, document: Document) -> list:
        """Creates the heading paragraph."""
        style = find_style(document, self.style, WD_STYLE_TYPE.PARAGRAPH) or _heading_style(document, self.level)
        paragraph = document.add_paragraph(self.text, style=style)
        if self.original is not None:
            keep_paragraph_properties(self.original, [paragraph])
        self.formatting.apply_to_paragraph(paragraph)
        if self.original is not None:
            keep_bookmarks(self.original, [paragraph])
        return [paragraph._p]


@dataclass
class NewParagraph(IDocumentContent):
    """
    One or more paragraphs written with the visual editor (HTML), with a paragraph style and direct formatting.
    Lists use the "List Bullet"/"List Number" styles if the document defines them, otherwise a prefix.
    """
    html: str
    style: str | None = None
    formatting: Formatting = field(default_factory=Formatting)
    # Paragraph this one replaces (edit): its paragraph properties and bookmarks are kept.
    original: Paragraph | None = field(default=None, repr=False, compare=False)
    content_id: str = field(default_factory=new_content_id)

    def serialize(self) -> dict:
        """Type "paragraph" with HTML, style and formatting."""
        return {
            "type": "paragraph",
            "id": self.content_id,
            "html": self.html,
            "style": self.style,
            "formatting": self.formatting.to_dict(),
        }

    def build(self, document: Document) -> list:
        """Creates a paragraph for each block of the HTML."""
        blocks = html_to_blocks(self.html)
        if not blocks:
            raise ValueError(t("errors.emptyParagraph"))
        style = find_style(document, self.style, WD_STYLE_TYPE.PARAGRAPH)
        paragraphs = [self._build_block(document, block, style) for block in blocks]
        if self.original is not None:
            # List items created in the editor keep the properties of their own list style.
            keep_paragraph_properties(
                self.original, [paragraph for paragraph, block in zip(paragraphs, blocks) if not block.list_type]
            )
        # The form's formatting applies to the whole paragraph; bold and the like stay those of the editor.
        formatting = Formatting(font=self.formatting.font, size=self.formatting.size, color=self.formatting.color,
                                alignment=self.formatting.alignment)
        for paragraph in paragraphs:
            formatting.apply_to_paragraph(paragraph)
        if self.original is not None:
            keep_bookmarks(self.original, paragraphs)
        return [paragraph._p for paragraph in paragraphs]

    def _build_block(self, document: Document, block: HtmlBlock, style):
        """Creates the paragraph of a block, with the runs formatted as in the editor."""
        list_style = _list_style(document, block) if block.list_type else None
        paragraph = document.add_paragraph(style=list_style or style)
        if block.list_type and list_style is None:
            # Without list styles in the template: text prefix and indent.
            paragraph.add_run("• " if block.list_type == "bullet" else f"{block.list_index}. ")
            paragraph.paragraph_format.left_indent = LIST_INDENT * (block.list_level + 1)
        append_html_runs(paragraph, block.runs)
        return paragraph


@dataclass
class NewImage(IDocumentContent):
    """
    Image in a paragraph of its own. width in centimeters: without it, the image uses its native size; in both
    cases it is reduced, if needed, to the usable page width keeping its proportions.
    alignment is one of "left", "center", "right", "justify" (None = the style's one).
    """
    data: bytes = field(repr=False)
    filename: str = "image"
    width: float | None = None
    alignment: str | None = None
    style: str | None = None
    content_id: str = field(default_factory=new_content_id)

    @property
    def content_type(self) -> str:
        """MIME type of the image, read from the bytes."""
        return Image.from_blob(self.data).content_type

    def build(self, document: Document) -> list:
        """Creates the paragraph with the image."""
        paragraph = document.add_paragraph(style=find_style(document, self.style, WD_STYLE_TYPE.PARAGRAPH))
        if self.alignment:
            paragraph.alignment = ALIGNMENTS[self.alignment]
        shape = paragraph.add_run().add_picture(BytesIO(self.data))
        section = document.sections[-1]
        max_width = section.page_width - section.left_margin - section.right_margin
        width = min(Cm(self.width) if self.width else shape.width, max_width)
        if width != shape.width:
            shape.height = int(shape.height * width / shape.width)
            shape.width = int(width)
        return [paragraph._p]

    def serialize(self) -> dict:
        """Type "image" with the bytes in base64."""
        return {
            "type": "image",
            "id": self.content_id,
            "data": base64.b64encode(self.data).decode("ascii"),
            "filename": self.filename,
            "content_type": self.content_type,
            "width": self.width,
            "alignment": self.alignment,
            "style": self.style,
        }

    @classmethod
    def from_dict(cls, value: dict, content_id: str) -> "NewImage":
        """Creates the image from JSON; raises ValueError if the data is not an image Word supports."""
        try:
            data = base64.b64decode(value.get("data") or "", validate=True)
            Image.from_blob(data)
        except (binascii.Error, TypeError, UnrecognizedImageError) as error:
            raise ValueError(t("errors.invalidImage")) from error
        filename = value.get("filename") or "image"
        width = value.get("width")
        alignment = value.get("alignment") or None
        if not isinstance(filename, str):
            raise ValueError(t("errors.imageFilename"))
        if width is not None and (isinstance(width, bool) or not isinstance(width, (int, float)) or not 0 < width <= 100):
            raise ValueError(t("errors.imageWidth"))
        if alignment is not None and alignment not in ALIGNMENTS:
            raise ValueError(t("errors.unsupportedAlignment", alignment=alignment))
        return cls(data, filename, width, alignment, value.get("style") or None, content_id)


def keep_paragraph_properties(original: Paragraph, paragraphs: list[Paragraph]) -> None:
    """
    Copies original's paragraph properties (indents, spacing, numbering...) to the paragraphs replacing it, if they
    have the same style. A section break of original always moves to the last paragraph.
    """
    original_properties = original._p.pPr
    if original_properties is None or not paragraphs:
        return
    original_style = original.style.style_id if original.style else None
    for paragraph in paragraphs:
        if (paragraph.style.style_id if paragraph.style else None) != original_style:
            continue
        if paragraph._p.pPr is not None:
            paragraph._p.remove(paragraph._p.pPr)
        paragraph._p.insert(0, deepcopy(original_properties))
    section = original_properties.find(qn("w:sectPr"))
    last_properties = paragraphs[-1]._p.get_or_add_pPr()
    if section is not None and last_properties.find(qn("w:sectPr")) is None:
        last_properties.append(deepcopy(section))


def keep_bookmarks(original: Paragraph, paragraphs: list[Paragraph]) -> None:
    """Moves original's bookmarks (e.g. those of Word's table of contents links) to the new paragraphs."""
    starts = [deepcopy(element) for element in original._p.iter(qn("w:bookmarkStart"))]
    ends = [deepcopy(element) for element in original._p.iter(qn("w:bookmarkEnd"))]
    first = paragraphs[0]._p
    position = 1 if first.pPr is not None else 0
    for start in reversed(starts):
        first.insert(position, start)
    for end in ends:
        paragraphs[-1]._p.append(end)


def _heading_style(document: Document, level: int):
    """Heading style of the requested level: "Heading <level>" if it exists, otherwise the first of that level."""
    candidates = [
        style for style in document.styles
        if style.type == WD_STYLE_TYPE.PARAGRAPH and style_heading_level(style) == level
    ]
    if not candidates:
        raise ValueError(t("errors.noHeadingStyle", level=level))
    return next((style for style in candidates if style.style_id == f"Heading{level}"), candidates[0])


def _list_style(document: Document, block: HtmlBlock):
    """List style of the document for the type and level of the block, or None if the template lacks it."""
    names = BULLET_STYLES if block.list_type == "bullet" else NUMBER_STYLES
    name = names[min(block.list_level, len(names) - 1)]
    return next(
        (style for style in document.styles if style.type == WD_STYLE_TYPE.PARAGRAPH and style.name == name),
        None,
    )


def content_from_dict(value) -> IDocumentContent:
    """
    Creates a content from JSON (Builder requests, ContentBlocks, database); it is the inverse of serialize.
    "id" is the hexadecimal ID of the content: one is generated if missing. Raises ValueError if it is not valid.
    """
    if not isinstance(value, dict):
        raise ValueError(t("errors.contentNotObject"))
    content_type = value.get("type")
    content_id = parse_content_id(value.get("id"))
    style = value.get("style") or None
    if style is not None and not isinstance(style, str):
        raise ValueError(t("errors.styleNotString"))

    if content_type == "heading":
        text = value.get("text")
        level = value.get("level")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(t("errors.emptyHeading"))
        if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 9:
            raise ValueError(t("errors.headingLevel"))
        return NewHeading(text.strip(), level, style, Formatting.from_dict(value.get("formatting")), content_id=content_id)
    if content_type == "paragraph":
        html = value.get("html")
        if not isinstance(html, str):
            raise ValueError(t("errors.paragraphNotHtml"))
        return NewParagraph(html, style, Formatting.from_dict(value.get("formatting")), content_id=content_id)
    if content_type == "image":
        return NewImage.from_dict(value, content_id)
    if content_type == "table":
        table = WordTable.from_dict(value)
        table.content_id = content_id
        return table
    raise ValueError(t("errors.unsupportedContentType", type=content_type))
