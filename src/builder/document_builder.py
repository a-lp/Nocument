from docx.document import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from ..compilers.docx_utils import heading_level, is_layout_table, iter_body_blocks, table_of_contents_paragraphs
from ..analyzers.section_analyzer import SectionAnalyzer
from ..i18n import t
from .content_interface import IDocumentContent
from .contents import NewHeading, NewParagraph
from .model import IContent, Section, TextContent
from .word_table import WordTable


class ContentSequence(IDocumentContent):
    """Several contents inserted together, in order (e.g. the elements of a ContentBlock)."""

    def __init__(self, contents: list[IDocumentContent]):
        """contents: contents to insert, in the order they must appear."""
        self.contents = contents
        self.content_id = ""

    def build(self, document: Document) -> list:
        """Elements of all the contents, in order."""
        return [element for content in self.contents for element in content.build(document)]

    def serialize(self) -> dict:
        """Not serializable as a single content: the contents are serialized one by one."""
        raise NotImplementedError("ContentSequence is not a content that can be saved.")


def block_insertion_point(document: Document, after: int | None, level: int,
                          moved: tuple[int, int] | None = None) -> int | None:
    """
    Where to insert, after the block after (None = beginning), contents whose highest heading has the given level, so
    that they stay a block: a heading takes as its section everything that follows it up to the next heading of the
    same or a higher level, so inserted right after a block it would take over the contents and subsections that
    follow it (e.g. the rest of the section of the target). The point moves forward past those contents, up to the
    next heading of level <= level (or the end of the document), and the insertion goes right before it.
    Layout table elements share the table's block: the insertion can only go before or after the whole table.
    moved: blocks (first, last) being moved, ignored as they leave their place.
    """
    analyzer = SectionAnalyzer()
    analyzer.analyze(document)
    point = after
    for item in _walk(analyzer.contents):
        if after is not None and item.id <= after:
            # Before the insertion point, or the block itself (e.g. the target heading, whose section follows).
            continue
        if moved is not None and moved[0] <= item.id <= moved[1]:
            continue
        if isinstance(item, Section) and item.level <= level:
            break
        point = item.anchor if point is None else max(point, item.anchor)
    return point


class DocumentBuilder:
    """
    Inserts, edits and deletes contents in a Word document. Positions are the ids of the document blocks as they
    were when it was opened (see SectionAnalyzer): a structure element takes the blocks from id to anchor
    (e.g. table and caption).
    """

    def __init__(self, document: Document):
        """document: python-docx document to edit (the caller saves it)."""
        self.document = document
        self.blocks = list(iter_body_blocks(document))
        # Table of contents paragraphs are regenerated at every update: they are not edited nor used as insertion
        # points (the content would end up inside the table of contents field and be deleted).
        self.table_of_contents = table_of_contents_paragraphs(document)
        # Elements of the layout tables by (table id, position), read at the first request.
        self._layout_items: dict[tuple[int, int], IContent] | None = None

    def insert(self, after: int | None, content: IDocumentContent) -> None:
        """
        Inserts content after the block with id after, or at the beginning of the document with after None.
        Raises ValueError if after is not a block.
        """
        if after is not None and not 0 <= after < len(self.blocks):
            raise ValueError(t("errors.invalidInsertPositionAt", position=after))
        if after is not None:
            self._check_not_table_of_contents([self.blocks[after]])

        elements = content.build(self.document)
        if after is None:
            body = self.document.element.body
            first = self.blocks[0]._element if self.blocks else body.find(qn("w:sectPr"))
            for element in elements:
                if first is not None:
                    first.addprevious(element)
            return

        anchor = self.blocks[after]._element
        # addnext moves the element: in reverse order, so they keep the order of elements.
        for element in reversed(elements):
            anchor.addnext(element)

    def replace(self, first: int, last: int, content: IDocumentContent) -> None:
        """
        Replaces the element taking the blocks from first to last with content. Headings and paragraphs keep the
        original's paragraph properties and bookmarks; tables are updated in place if the number of columns does
        not change. Raises ValueError if the range is not valid or the type does not match.
        """
        originals = self._range(first, last)
        if isinstance(content, WordTable):
            table = next((block for block in originals if isinstance(block, Table)), None)
            if table is None:
                raise ValueError(t("errors.targetNotTable"))
            if is_layout_table(table):
                # The elements of a layout table have the whole table as position (see SectionAnalyzer).
                raise ValueError(t("errors.layoutTableNotEditable"))
            caption = next((block for block in originals if isinstance(block, Paragraph)), None)
            if content.update(self.document, table, caption):
                return
        elif isinstance(content, (NewHeading, NewParagraph)):
            if len(originals) != 1 or not isinstance(originals[0], Paragraph):
                raise ValueError(t("errors.targetNotParagraph"))
            content.original = originals[0]

        elements = content.build(self.document)
        for element in elements:
            originals[0]._element.addprevious(element)
        for block in originals:
            block._element.getparent().remove(block._element)

    def replace_layout(self, table_id: int, position: int, content: IDocumentContent) -> None:
        """
        Replaces the element at position of the layout table of block table_id (see SectionAnalyzer): headings and
        paragraphs with a heading or a paragraph, keeping their properties and bookmarks; nested tables with a
        table, updated in place if the number of columns does not change.
        Raises ValueError if the element does not exist or cannot be replaced with content.
        """
        item = self._layout_item(table_id, position)
        if isinstance(item, WordTable):
            if not isinstance(content, WordTable):
                raise ValueError(t("errors.targetIsTable"))
            if content.update(self.document, item.block, None):
                return
        elif isinstance(item, (Section, TextContent)):
            if not isinstance(content, (NewHeading, NewParagraph)):
                raise ValueError(t("errors.targetNotTable"))
            if isinstance(item, TextContent) and item.has_image:
                raise ValueError(t("errors.paragraphWithImages"))
            content.original = item.block
        else:
            raise ValueError(t("errors.imagesNotEditable"))

        original = item.block._element
        for element in content.build(self.document):
            original.addprevious(element)
        original.getparent().remove(original)

    def delete(self, first: int, last: int) -> None:
        """
        Deletes the element taking the blocks from first to last. A paragraph that closes a document section
        (section break) is only emptied, so the page layout does not change.
        """
        self.delete_many([(first, last)])

    def delete_many(self, ranges: list[tuple[int, int]], layout_items: list[tuple[int, int]] = ()) -> None:
        """
        Deletes several elements, each given by the blocks (first, last) it takes, and the layout table elements
        given by (table id, position). Everything is validated before changing the document: if an element is not
        valid the document stays unchanged. A block given more than once (e.g. text and image of the same
        paragraph) is deleted once.
        """
        cell_elements = []
        for table_id, position in layout_items:
            element = self._layout_item(table_id, position).block._element
            if element not in cell_elements:
                cell_elements.append(element)
        blocks = []
        for first, last in ranges:
            blocks.extend(block for block in self._range(first, last) if block not in blocks)
        for element in cell_elements:
            self._remove_from_cell(element)
        for block in blocks:
            properties = block._element.pPr if isinstance(block, Paragraph) else None
            if properties is not None and properties.find(qn("w:sectPr")) is not None:
                for child in list(block._element):
                    if child is not properties:
                        block._element.remove(child)
            else:
                block._element.getparent().remove(block._element)

    def heading_level_at(self, block_id: int) -> int | None:
        """Heading level of the block (None if it is not a heading paragraph), e.g. of the first moved block."""
        block = self.blocks[block_id] if 0 <= block_id < len(self.blocks) else None
        return heading_level(block) if isinstance(block, Paragraph) else None

    def move(self, first: int, last: int, after: int | None) -> None:
        """
        Moves the blocks from first to last (e.g. a heading with its whole section) right after the block with id
        after, or to the beginning of the document with after None. Raises ValueError if the position is inside the
        moved blocks or if the blocks contain a section break (moving it would change the page layout).
        """
        blocks = self._range(first, last)
        if after is not None and not 0 <= after < len(self.blocks):
            raise ValueError(t("errors.invalidMovePositionAt", position=after))
        if after is not None and first <= after <= last:
            raise ValueError(t("errors.moveIntoItself"))
        if after is not None:
            self._check_not_table_of_contents([self.blocks[after]])
        for block in blocks:
            properties = block._element.pPr if isinstance(block, Paragraph) else None
            if properties is not None and properties.find(qn("w:sectPr")) is not None:
                raise ValueError(t("errors.moveSectionBreak"))

        elements = [block._element for block in blocks]
        if after is None:
            if first == 0:
                return
            start = self.blocks[0]._element
            for element in elements:
                start.addprevious(element)
            return

        anchor = self.blocks[after]._element
        # addnext moves the element: in reverse order, so they keep their original order.
        for element in reversed(elements):
            anchor.addnext(element)

    def _layout_item(self, table_id: int, position: int) -> IContent:
        """Element of the layout table of block table_id at position; ValueError if there is none."""
        if self._layout_items is None:
            # The same analysis as the structure sent to the frontend: the positions match.
            analyzer = SectionAnalyzer()
            analyzer.analyze(self.document)
            self._layout_items = {
                (item.id, item.layout): item for item in _walk(analyzer.contents) if item.layout is not None
            }
        item = self._layout_items.get((table_id, position))
        if item is None:
            raise ValueError(t("errors.layoutItemNotFound"))
        return item

    @staticmethod
    def _remove_from_cell(element) -> None:
        """
        Removes a paragraph or a table from a cell. Word requires a cell to contain at least one paragraph and to
        end with a paragraph: an empty one is added if needed.
        """
        parent = element.getparent()
        parent.remove(element)
        cell = parent if parent.tag == qn("w:tc") else next(parent.iterancestors(qn("w:tc")))
        if cell[-1].tag != qn("w:p"):
            cell.append(OxmlElement("w:p"))

    def _range(self, first: int, last: int) -> list:
        """Blocks from first to last included; raises ValueError if the range is not valid."""
        if not 0 <= first <= last < len(self.blocks):
            raise ValueError(t("errors.invalidRange", first=first, last=last))
        blocks = self.blocks[first:last + 1]
        self._check_not_table_of_contents(blocks)
        return blocks

    def _check_not_table_of_contents(self, blocks: list) -> None:
        """Raises ValueError if one of the blocks belongs to a table of contents."""
        if any(block._element in self.table_of_contents for block in blocks):
            raise ValueError(t("errors.tocNotEditable"))


def _walk(contents: list[IContent]):
    """Structure elements in document order, nested sections included."""
    for content in contents:
        yield content
        if isinstance(content, Section):
            yield from _walk(content.contents)
