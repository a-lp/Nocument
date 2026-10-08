from dataclasses import dataclass, field

from docx.document import Document
from docx.image.exceptions import UnrecognizedImageError
from docx.image.image import Image

from ..analyzers.section_analyzer import SectionAnalyzer
from ..builder.content_interface import IDocumentContent
from ..builder.contents import NewHeading, NewImage, NewParagraph
from ..builder.formatting import Formatting
from ..builder.model import IContent, ImageContent, Section, TextContent
from ..builder.word_table import WordTable
from ..i18n import t


@dataclass
class ImportGroup:
    """
    Imported contents that become a ContentBlock: a section of the document (title is its heading) or, with
    title None, the content before the first heading (or the whole document, if it has no headings).
    """
    title: str | None
    contents: list[IDocumentContent] = field(default_factory=list)


@dataclass
class ImportResult:
    """Groups of contents imported from a Word document, in order, and warnings about what was not imported."""
    groups: list[ImportGroup] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def import_contents(document: Document) -> ImportResult:
    """
    Converts the document body into contents for ContentBlocks (see SectionAnalyzer): headings, paragraphs
    (in HTML, with style and formatting), tables with caption and images, grouped by top level heading.
    Each group holds the heading and all the content of its section, subsections included; the content before the
    first heading forms a group without heading, which is the whole document if there are no headings.
    Tables of contents, empty paragraphs, headings without text and empty groups are skipped; images in formats
    Word cannot insert again (e.g. EMF, WMF) are reported in the warnings.
    """
    analyzer = SectionAnalyzer()
    analyzer.analyze(document)
    result = ImportResult()
    skipped_images = 0
    preamble = ImportGroup(None)
    groups = [preamble]
    for top_level in analyzer.contents:
        if isinstance(top_level, Section):
            # The group name is on one line (a heading can contain line breaks).
            groups.append(ImportGroup(" ".join(top_level.title.split()) or None))
        for item in _flatten([top_level]):
            content = _to_content(item)
            if content is None and isinstance(item, ImageContent):
                skipped_images += 1
            elif content is not None:
                (groups[-1] if isinstance(top_level, Section) else preamble).contents.append(content)
    result.groups = [group for group in groups if group.contents]
    if skipped_images:
        result.warnings.append(t("warnings.skippedImages", count=skipped_images))
    return result


def _to_content(item: IContent) -> IDocumentContent | None:
    """Content matching a structure element, or None if it must be skipped."""
    if isinstance(item, Section):
        return NewHeading(item.title, item.level, item.style, Formatting.from_dict(item.formatting)) if item.title else None
    if isinstance(item, TextContent):
        return NewParagraph(item.html, item.style, Formatting.from_dict(item.formatting))
    if isinstance(item, WordTable):
        # The position in the source document (id, anchor) is not needed in the block.
        return WordTable(item.rows, item.caption, item.caption_position, item.header, item.style, item.alignment)
    if isinstance(item, ImageContent):
        try:
            Image.from_blob(item.data)
        except UnrecognizedImageError:
            return None
        return NewImage(item.data, item.filename)
    return None


def _flatten(contents: list[IContent]):
    """Structure elements in document order: each heading followed by the contents of its section."""
    for content in contents:
        yield content
        if isinstance(content, Section):
            yield from _flatten(content.contents)
