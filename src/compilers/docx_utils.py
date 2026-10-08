from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass
import re

from docx.document import Document
from docx.oxml.ns import qn
from docx.styles.style import BaseStyle
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.text.run import Run


def isolate_keyword_runs(paragraph: Paragraph, keyword: str) -> list[Run]:
    """
    Rearranges the runs of the paragraph so that every occurrence of keyword is in a dedicated run
    (Word often splits text over several runs) and returns those runs.
    The paragraph text does not change; the new runs inherit the formatting of the keyword's first character.
    """
    keyword_runs = []
    position = 0
    while True:
        runs = paragraph.runs
        text = "".join(run.text for run in runs)
        start = text.find(keyword, position)
        if start == -1:
            return keyword_runs
        keyword_runs.append(_isolate_range(paragraph, runs, start, start + len(keyword)))
        # Isolating does not change the text: the following positions stay valid.
        position = start + len(keyword)


def _isolate_range(paragraph: Paragraph, runs: list[Run], start: int, end: int) -> Run:
    """Moves the characters [start, end) of the paragraph text into a new run and returns it."""
    # Finds the runs containing the first and the last character of the range.
    offset = 0
    first_index = last_index = None
    first_offset = last_offset = 0
    for index, run in enumerate(runs):
        run_end = offset + len(run.text)
        if first_index is None and start < run_end:
            first_index, first_offset = index, start - offset
        if end <= run_end:
            last_index, last_offset = index, end - offset
            break
        offset = run_end

    first_run, last_run = runs[first_index], runs[last_index]
    before = first_run.text[:first_offset]
    after = last_run.text[last_offset:]
    keyword = first_run.text[first_offset:] if first_index != last_index else first_run.text[first_offset:last_offset]
    for run in runs[first_index + 1:last_index + 1]:
        keyword += run.text[:last_offset] if run is last_run else run.text

    keyword_element = deepcopy(first_run._r)
    first_run._r.addnext(keyword_element)
    keyword_run = Run(keyword_element, paragraph)
    keyword_run.text = keyword

    if after:
        after_element = deepcopy(last_run._r)
        keyword_element.addnext(after_element)
        Run(after_element, paragraph).text = after

    for run in runs[first_index + 1:last_index + 1]:
        run._r.getparent().remove(run._r)
    if before:
        first_run.text = before
    else:
        first_run._r.getparent().remove(first_run._r)

    return keyword_run


def set_cell_text(cell: _Cell, text: str) -> None:
    """Replaces the content of the cell keeping the formatting of the first paragraph and of the first run."""
    first_paragraph, *other_paragraphs = cell.paragraphs
    for paragraph in other_paragraphs:
        paragraph._p.getparent().remove(paragraph._p)

    runs = first_paragraph.runs
    if not runs:
        first_paragraph.add_run(text)
        return
    runs[0].text = text
    for run in runs[1:]:
        run._r.getparent().remove(run._r)


def iter_document_paragraphs(document: Document) -> Iterator[Paragraph]:
    """Iterates over the paragraphs of the body, tables, content controls, headers and footers."""
    yield from _iter_blocks(document.element.body, document)

    # Headers and footers: those linked to the previous section share its content, so they are skipped.
    visited = set()
    for section in document.sections:
        for header_footer in (
            section.header, section.first_page_header, section.even_page_header,
            section.footer, section.first_page_footer, section.even_page_footer,
        ):
            if header_footer.is_linked_to_previous or id(header_footer._element) in visited:
                continue
            visited.add(id(header_footer._element))
            yield from _iter_blocks(header_footer._element, header_footer)


def _iter_blocks(element, parent) -> Iterator[Paragraph]:
    """Iterates in order over paragraphs, tables (nested ones too) and content controls, yielding the paragraphs."""
    for child in element.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            table = Table(child, parent)
            for row_element in child.tr_lst:
                for cell_element in row_element.tc_lst:
                    yield from _iter_blocks(cell_element, _Cell(cell_element, table))
        elif child.tag == qn("w:sdt"):
            content = child.find(qn("w:sdtContent"))
            if content is not None:
                yield from _iter_blocks(content, parent)


HEADING_STYLE_NAME = re.compile(r"heading (\d)$", re.IGNORECASE)
# Word's Title and Subtitle styles: they have no outline level, but open a section like headings.
TITLE_STYLE_LEVELS = {"title": 1, "subtitle": 2}
TOC_INSTRUCTION = re.compile(r"^\s*TOC\b")
# Styles of the table of contents entries and title ("toc 1"... and "TOC Heading" in Word).
TOC_STYLE_NAME = re.compile(r"^toc( \d| heading)$", re.IGNORECASE)
TOC_GALLERY = "Table of Contents"


def iter_body_blocks(document: Document) -> Iterator[Paragraph | Table]:
    """
    Iterates in order over the top level paragraphs and tables of the body, entering content controls.
    The index of a block in this sequence is its id in the document structure (see SectionAnalyzer).
    """
    yield from _iter_body_blocks(document.element.body, document)


def _iter_body_blocks(element, parent) -> Iterator[Paragraph | Table]:
    """Iterates over the paragraphs and tables that are children of element, entering content controls."""
    for child in element.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)
        elif child.tag == qn("w:sdt"):
            content = child.find(qn("w:sdtContent"))
            if content is not None:
                yield from _iter_body_blocks(content, parent)


def paragraph_text(paragraph: Paragraph) -> str:
    """
    Full text of the paragraph, including hyperlinks and field results (e.g. caption numbers);
    line breaks become "\n" (e.g. a title "QUARTERLY<line break>Report").
    """
    return "".join(
        "\n" if node.tag in (qn("w:br"), qn("w:cr")) and node.get(qn("w:type")) in (None, "textWrapping") else node.text or ""
        for node in paragraph._p.iter(qn("w:t"), qn("w:br"), qn("w:cr"))
    )


def is_layout_table(table: Table) -> bool:
    """
    True if the table contains (also in nested tables) a heading with text: it is a layout table, used to place the
    document text in its cells, not a data table.
    """
    return any(
        heading_level(paragraph) is not None and paragraph_text(paragraph).strip()
        for paragraph in (Paragraph(element, table) for element in table._tbl.iter(qn("w:p")))
    )


def heading_level(paragraph: Paragraph) -> int | None:
    """Heading level (1 = highest) or None if the paragraph is not a heading."""
    # The outline level can be on the paragraph or on a style of the inheritance chain.
    outline_level = paragraph._p.find(f"{qn('w:pPr')}/{qn('w:outlineLvl')}")
    if outline_level is not None:
        return _outline_value_to_level(outline_level)
    return style_heading_level(paragraph.style)


def style_heading_level(style: BaseStyle | None) -> int | None:
    """
    Heading level defined by the style or its base styles: outline level, name "Heading N",
    or "Title" (level 1) and "Subtitle" (level 2).
    """
    while style is not None:
        name = (style.name or "").lower()
        outline_level = style.element.find(f"{qn('w:pPr')}/{qn('w:outlineLvl')}")
        if outline_level is not None:
            level = _outline_value_to_level(outline_level)
            # Title and Subtitle stay headings even if the style marks them as body text (level 9).
            if level is not None or name not in TITLE_STYLE_LEVELS:
                return level
        match = HEADING_STYLE_NAME.match(name)
        if match:
            return int(match.group(1))
        if name in TITLE_STYLE_LEVELS:
            return TITLE_STYLE_LEVELS[name]
        style = style.base_style
    return None


def _outline_value_to_level(outline_level) -> int | None:
    """Converts w:outlineLvl (0-8, 9 = body text) into the heading level."""
    value = int(outline_level.get(qn("w:val")))
    return value + 1 if value < 9 else None


@dataclass
class TocField:
    """Table of contents (complex) field of the body: its begin and end w:fldChar and the instruction (e.g. TOC \\o "1-3" \\h)."""
    begin: object
    end: object
    instruction: str


def find_toc_fields(document: Document) -> list[TocField]:
    """Table of contents fields of the document body, in document order (nested fields, e.g. PAGEREF, are excluded)."""
    stack = []
    fields = []
    for element in document.element.body.iter(qn("w:fldChar"), qn("w:instrText")):
        if element.tag == qn("w:instrText"):
            if stack:
                stack[-1]["instruction"] += element.text or ""
            continue
        kind = element.get(qn("w:fldCharType"))
        if kind == "begin":
            stack.append({"begin": element, "instruction": ""})
        elif kind == "end" and stack:
            field = stack.pop()
            if not stack and TOC_INSTRUCTION.match(field["instruction"]):
                fields.append(TocField(field["begin"], element, field["instruction"]))
    # Tables of contents are not nested in each other: the closing order is the document order.
    return fields


def table_of_contents_paragraphs(document: Document) -> set:
    """
    w:p elements belonging to a table of contents: those between the begin and end of a TOC field, those with a
    table of contents style and those inside a table of contents content control. They are not document content:
    they are regenerated at every table of contents update.
    """
    paragraphs = set()
    for field in find_toc_fields(document):
        begin = next(field.begin.iterancestors(qn("w:p")), None)
        end = next(field.end.iterancestors(qn("w:p")), None)
        element = begin
        while element is not None:
            if element.tag == qn("w:p"):
                paragraphs.add(element)
            if element is end:
                break
            element = element.getnext()

    for block in iter_body_blocks(document):
        if not isinstance(block, Paragraph):
            continue
        style = block.style
        if style is not None and TOC_STYLE_NAME.match(style.name or ""):
            paragraphs.add(block._p)
        elif any(_is_toc_content_control(sdt) for sdt in block._p.iterancestors(qn("w:sdt"))):
            paragraphs.add(block._p)
    return paragraphs


def _is_toc_content_control(sdt) -> bool:
    """True if the content control is a table of contents (docPartGallery "Table of Contents")."""
    gallery = sdt.find(f"{qn('w:sdtPr')}/{qn('w:docPartObj')}/{qn('w:docPartGallery')}")
    return gallery is not None and gallery.get(qn("w:val")) == TOC_GALLERY
