import random

from docx.document import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml.shared import OxmlElement
from docx.text.paragraph import Paragraph

from ..compilers.docx_utils import TocField, heading_level, iter_body_blocks, paragraph_text
from ..i18n import t


def write_toc(document: Document, field: TocField, entries: list[dict]) -> bool:
    """
    Replaces the content of the table of contents field with entries ({"level", "text"} with the parts separated by
    tabs, as LibreOffice computes them). Each entry has the style "TOC <level>" and, with the \\h switch, a link to its
    heading. Returns False if the field has an unsupported shape (begin and end in different containers).
    """
    begin_paragraph = next(field.begin.iterancestors(qn("w:p")), None)
    end_paragraph = next(field.end.iterancestors(qn("w:p")), None)
    if begin_paragraph is None or end_paragraph is None or begin_paragraph.getparent() is not end_paragraph.getparent():
        return False
    old_paragraphs = [begin_paragraph]
    while old_paragraphs[-1] is not end_paragraph:
        next_element = old_paragraphs[-1].getnext()
        if next_element is None:
            return False
        old_paragraphs.append(next_element)

    # Container of the new paragraphs: python-docx needs it to resolve the styles.
    parent = document._body
    # Written in the document when there are no headings, in the language of the web app.
    empty_text = t("document.emptyToc")
    headings = _TocHeadings(document)
    hyperlinks = "\\h" in field.instruction
    new_paragraphs = []
    for entry in entries or [{"level": 1, "text": empty_text}]:
        paragraph = Paragraph(OxmlElement("w:p"), parent)
        style = _toc_style(document, entry["level"]) if entries else None
        if style is not None:
            paragraph.style = style
        parts, page, bookmark = headings.match(entry["text"]) if entries else ([empty_text], "", None)
        container = paragraph._p
        if hyperlinks and bookmark:
            container = OxmlElement("w:hyperlink")
            container.set(qn("w:anchor"), bookmark)
            container.set(qn("w:history"), "1")
            paragraph._p.append(container)
        for index, part in enumerate(parts):
            if index:
                container.append(_run(tab=True))
            container.append(_run(text=part))
        if page:
            container.append(_run(tab=True))
            if bookmark:
                # As in Word: the page number is a PAGEREF field to the heading's bookmark.
                container.extend([_field_char("begin"), _instruction(f" PAGEREF {bookmark} \\h "), _field_char("separate")])
                container.append(_run(text=page))
                container.append(_field_char("end"))
            else:
                container.append(_run(text=page))
        new_paragraphs.append(paragraph._p)

    # The field begins in the first paragraph and ends in the last one, as in the tables of contents made by Word.
    first = new_paragraphs[0]
    position = 1 if first.find(qn("w:pPr")) is not None else 0
    for element in reversed([_field_char("begin"), _instruction(field.instruction), _field_char("separate")]):
        first.insert(position, element)
    new_paragraphs[-1].append(_field_char("end"))

    for paragraph in new_paragraphs:
        begin_paragraph.addprevious(paragraph)
    for paragraph in old_paragraphs:
        paragraph.getparent().remove(paragraph)
    return True


class _TocHeadings:
    """Headings of the document in order, to match each table of contents entry to its heading (and bookmark)."""

    def __init__(self, document: Document):
        self.document = document
        self.headings = [
            block for block in iter_body_blocks(document)
            if isinstance(block, Paragraph) and heading_level(block) is not None and paragraph_text(block).strip()
        ]
        self.position = 0

    def match(self, entry_text: str) -> tuple[list[str], str, str | None]:
        """
        Parts of the entry before the page number (numbering and heading), page number and bookmark of the matching
        heading, searched after the previous entry's one. Without a match the parts are those of the entry as it is,
        without bookmark.
        """
        *head_parts, page = entry_text.split("\t") if "\t" in entry_text else (entry_text, "")
        head = " ".join(head_parts)
        for index in range(self.position, len(self.headings)):
            title = paragraph_text(self.headings[index]).strip()
            start = head.rfind(title)
            if start != -1:
                self.position = index + 1
                number = head[:start].strip()
                return ([number, title] if number else [title]), page, self._bookmark(self.headings[index])
        return head_parts or [entry_text], page, None

    def _bookmark(self, heading: Paragraph) -> str:
        """Name of the heading's "_Toc..." bookmark, created if missing."""
        for start in heading._p.iter(qn("w:bookmarkStart")):
            if (start.get(qn("w:name")) or "").startswith("_Toc"):
                return start.get(qn("w:name"))
        body = self.document.element.body
        names = {element.get(qn("w:name")) for element in body.iter(qn("w:bookmarkStart"))}
        ids = [int(element.get(qn("w:id"))) for element in body.iter(qn("w:bookmarkStart")) if (element.get(qn("w:id")) or "").isdigit()]
        name = f"_Toc{random.randint(100000000, 999999999)}"
        while name in names:
            name = f"_Toc{random.randint(100000000, 999999999)}"
        bookmark_id = str(max(ids, default=0) + 1)
        start = OxmlElement("w:bookmarkStart")
        start.set(qn("w:id"), bookmark_id)
        start.set(qn("w:name"), name)
        end = OxmlElement("w:bookmarkEnd")
        end.set(qn("w:id"), bookmark_id)
        heading._p.insert(1 if heading._p.pPr is not None else 0, start)
        heading._p.append(end)
        return name


def _toc_style(document: Document, level: int):
    """Style of the table of contents entries of the level ("toc N" in Word), or None if the document lacks it."""
    for style in document.styles:
        if style.type == WD_STYLE_TYPE.PARAGRAPH and (style.style_id == f"TOC{level}" or (style.name or "").lower() == f"toc {level}"):
            return style
    return None


def _run(text: str = "", tab: bool = False):
    """Run with a text or a tab."""
    run = OxmlElement("w:r")
    if tab:
        run.append(OxmlElement("w:tab"))
    else:
        text_element = OxmlElement("w:t")
        text_element.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text_element.text = text
        run.append(text_element)
    return run


def _field_char(kind: str):
    """Run with a w:fldChar of type kind (begin, separate, end)."""
    run = OxmlElement("w:r")
    field_char = OxmlElement("w:fldChar")
    field_char.set(qn("w:fldCharType"), kind)
    run.append(field_char)
    return run


def _instruction(text: str):
    """Run with the field instruction."""
    run = OxmlElement("w:r")
    instruction = OxmlElement("w:instrText")
    instruction.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    instruction.text = text
    run.append(instruction)
    return run

