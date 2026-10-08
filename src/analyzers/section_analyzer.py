from collections.abc import Iterator

from docx.document import Document
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from ..builder.model import IContent, ImageContent, Section, TextContent
from ..builder.paragraph_reader import has_complex_content, paragraph_formatting, paragraph_html
from ..builder.styles import is_caption_style
from ..builder.word_table import WordTable
from ..compilers.docx_utils import (
    heading_level, is_layout_table, iter_body_blocks, paragraph_text, table_of_contents_paragraphs,
)
from .analyzer_interface import IAnalyzer

VML_IMAGEDATA = "{urn:schemas-microsoft-com:vml}imagedata"


class SectionAnalyzer(IAnalyzer):
    """
    Splits the document body into nested sections by its headings (outline level, "Heading N", Title or
    Subtitle style). contents holds, in order, the contents before the first heading and the top level sections.
    Each element has as id the index of its block in docx_utils.iter_body_blocks; tables are WordTables and
    include the caption (paragraph with the "Caption" style) right above or below them.
    Table of contents paragraphs are ignored: they are regenerated at every update and are not edited by hand.
    A table containing headings is a layout table (e.g. templates with the text inside the cells): the content of
    its cells is read in order as headings, paragraphs, images and tables; these elements have the table's block
    as id and anchor and their position inside it in layout.
    """

    def __init__(self):
        """Initializes the content list, filled by analyze."""
        self.contents: list[IContent] = []

    def analyze(self, document: Document) -> None:
        """Builds the section tree of the document body and saves it in self.contents."""
        root = Section("", 0)
        stack = [root]
        blocks = list(iter_body_blocks(document))
        table_of_contents = table_of_contents_paragraphs(document)
        consumed: set[int] = set()
        for index, block in enumerate(blocks):
            if index in consumed or block._element in table_of_contents:
                continue
            next_block = blocks[index + 1] if index + 1 < len(blocks) else None
            if self._is_caption(block) and isinstance(next_block, Table):
                # Caption above a table: _table reads it together with the table.
                continue
            if isinstance(block, Table) and is_layout_table(block):
                self._layout_contents(block, index, stack, table_of_contents)
            elif isinstance(block, Table):
                stack[-1].contents.append(self._table(blocks, index, consumed))
            elif heading_level(block) is not None:
                self._add_section(self._section(block, index), stack)
            else:
                stack[-1].contents.extend(self._paragraph_contents(block, index))
        self.contents = root.contents

    @staticmethod
    def _section(paragraph: Paragraph, index: int) -> Section:
        """Section opened by the heading paragraph, which takes the block index."""
        return Section(
            paragraph_text(paragraph).strip(), heading_level(paragraph), paragraph.style.style_id, id=index, anchor=index,
            formatting=paragraph_formatting(paragraph), has_fields=has_complex_content(paragraph),
        )

    @staticmethod
    def _add_section(section: Section, stack: list[Section]) -> None:
        """Adds the section inside the last section of a higher level and makes it the current section."""
        while stack[-1].level >= section.level:
            stack.pop()
        stack[-1].contents.append(section)
        stack.append(section)

    def _layout_contents(self, table: Table, index: int, stack: list[Section], table_of_contents: set) -> None:
        """
        Adds the content of the layout table of block index to the structure, cell by cell in reading order:
        headings open sections as in the body, nested tables without headings stay tables.
        """
        position = 0
        for block in self._cell_blocks(table):
            if isinstance(block, Paragraph) and block._element in table_of_contents:
                continue
            if isinstance(block, Table):
                word_table = WordTable.from_docx(block)
                word_table.id = word_table.anchor = index
                items = [word_table]
            elif heading_level(block) is not None:
                items = [self._section(block, index)]
            else:
                items = self._paragraph_contents(block, index)
            for item in items:
                item.layout = position
                item.block = block
                position += 1
                if isinstance(item, Section):
                    self._add_section(item, stack)
                else:
                    stack[-1].contents.append(item)

    def _cell_blocks(self, table: Table) -> Iterator[Paragraph | Table]:
        """Paragraphs and tables of the cells, row by row; nested layout tables are opened."""
        for row in table._tbl.tr_lst:
            for cell_element in row.tc_lst:
                cell = _Cell(cell_element, table)
                for block in self._cell_children(cell_element, cell):
                    if isinstance(block, Table) and is_layout_table(block):
                        yield from self._cell_blocks(block)
                    else:
                        yield block

    def _cell_children(self, element, parent) -> Iterator[Paragraph | Table]:
        """Paragraphs and tables that are children of element (a cell), entering content controls."""
        for child in element.iterchildren():
            if child.tag == qn("w:p"):
                yield Paragraph(child, parent)
            elif child.tag == qn("w:tbl"):
                yield Table(child, parent)
            elif child.tag == qn("w:sdt"):
                content = child.find(qn("w:sdtContent"))
                if content is not None:
                    yield from self._cell_children(content, parent)

    def _table(self, blocks: list, index: int, consumed: set[int]) -> WordTable:
        """
        Creates the WordTable of block index with the adjacent caption: the one above wins, the one below is
        marked in consumed so it does not also appear as a paragraph.
        """
        table = blocks[index]
        before = blocks[index - 1] if index > 0 and (index - 1) not in consumed else None
        after = blocks[index + 1] if index + 1 < len(blocks) else None
        if self._is_caption(before):
            word_table = WordTable.from_docx(table, before, "above")
            word_table.id, word_table.anchor = index - 1, index
        elif self._is_caption(after):
            word_table = WordTable.from_docx(table, after, "below")
            word_table.id, word_table.anchor = index, index + 1
            consumed.add(index + 1)
        else:
            word_table = WordTable.from_docx(table)
            word_table.id = word_table.anchor = index
        return word_table

    @staticmethod
    def _is_caption(block) -> bool:
        """True if the block is a caption paragraph."""
        return isinstance(block, Paragraph) and is_caption_style(block.style)

    def _paragraph_contents(self, paragraph: Paragraph, index: int) -> list[IContent]:
        """Converts a paragraph into its contents (text and images); empty paragraphs are skipped."""
        images = list(self._images(paragraph))
        for image in images:
            image.id = image.anchor = index
        text = paragraph_text(paragraph)
        if not text.strip():
            return images
        content = TextContent(
            text,
            paragraph.style.style_id if paragraph.style else None,
            index,
            index,
            html=paragraph_html(paragraph),
            formatting=paragraph_formatting(paragraph),
            has_image=bool(images),
            has_fields=has_complex_content(paragraph),
        )
        return [content, *images]

    @staticmethod
    def _images(paragraph: Paragraph) -> Iterator[ImageContent]:
        """Returns the images of the paragraph, both DrawingML (a:blip) and VML (v:imagedata)."""
        relationship_ids = [blip.get(qn("r:embed")) for blip in paragraph._p.iter(qn("a:blip"))]
        relationship_ids += [data.get(qn("r:id")) for data in paragraph._p.iter(VML_IMAGEDATA)]
        for relationship_id in relationship_ids:
            part = paragraph.part.related_parts.get(relationship_id) if relationship_id else None
            if part is not None:
                yield ImageContent(part.blob, part.content_type, part.partname.split("/")[-1])
