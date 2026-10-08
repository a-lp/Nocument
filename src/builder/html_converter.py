from dataclasses import dataclass, field
from html.parser import HTMLParser
import re

# Tag of the visual editor -> HtmlRun attribute it turns on.
INLINE_TAGS = {
    "strong": "bold", "b": "bold",
    "em": "italic", "i": "italic",
    "u": "underline",
    "s": "strike", "strike": "strike", "del": "strike",
}
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "blockquote"}
LIST_TAGS = {"ul": "bullet", "ol": "number"}
# Addresses accepted for hyperlinks (<a href>): web pages, e-mail and FTP; others (e.g. javascript:) stay plain text.
LINK_ADDRESS = re.compile(r"^(https?://|mailto:|ftp://)\S+$", re.IGNORECASE)


def safe_link(href) -> str | None:
    """The address if it can be a hyperlink of the document, otherwise None."""
    href = (href or "").strip()
    return href if LINK_ADDRESS.match(href) else None


@dataclass
class HtmlRun:
    """
    Piece of text with uniform formatting; text "\n" stands for a line break (<br>). link: address of the hyperlink
    the text belongs to (<a href>), None if it is not a link.
    """
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    link: str | None = None


@dataclass
class HtmlBlock:
    """
    Paragraph produced by the editor. list_type: None, "bullet" or "number";
    list_level: nesting level (0 = first); list_index: position in the list (from 1).
    """
    runs: list[HtmlRun] = field(default_factory=list)
    list_type: str | None = None
    list_level: int = 0
    list_index: int = 0


class _Parser(HTMLParser):
    """
    Converts the editor's HTML (paragraphs, bold, italic, underline, strikethrough, hyperlinks, lists) into
    HtmlBlocks.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[HtmlBlock] = []
        self.current: HtmlBlock | None = None
        self.formats = {"bold": 0, "italic": 0, "underline": 0, "strike": 0}
        # For each open list: [type, item counter].
        self.lists: list[list] = []
        # Addresses of the open <a> elements (None for those without a valid address).
        self.links: list[str | None] = []

    def handle_starttag(self, tag, attrs):
        if tag in INLINE_TAGS:
            self.formats[INLINE_TAGS[tag]] += 1
        elif tag == "a":
            self.links.append(safe_link(dict(attrs).get("href")))
        elif tag in LIST_TAGS:
            self.current = None
            self.lists.append([LIST_TAGS[tag], 0])
        elif tag == "li":
            if self.lists:
                self.lists[-1][1] += 1
            self._open_block(new_item=True)
        elif tag in BLOCK_TAGS:
            # The <p> inside a <li> just opened belongs to the same item.
            if not (self.current is not None and self.current.list_type and not self.current.runs):
                self._open_block()
        elif tag == "br":
            self._add_text("\n")

    def handle_endtag(self, tag):
        if tag in INLINE_TAGS:
            self.formats[INLINE_TAGS[tag]] = max(0, self.formats[INLINE_TAGS[tag]] - 1)
        elif tag == "a":
            if self.links:
                self.links.pop()
        elif tag in LIST_TAGS:
            if self.lists:
                self.lists.pop()
            self.current = None
        elif tag in BLOCK_TAGS:
            self.current = None

    def handle_data(self, data):
        # Whitespace between tags (HTML indentation) is not text.
        if self.current is None and not data.strip():
            return
        self._add_text(data)

    def _open_block(self, new_item: bool = False) -> None:
        """Opens a new paragraph; inside a list it inherits type, level and (for a new item) the number."""
        block = HtmlBlock()
        if self.lists and (new_item or self.current is None):
            block.list_type = self.lists[-1][0]
            block.list_level = len(self.lists) - 1
            block.list_index = self.lists[-1][1]
        self.blocks.append(block)
        self.current = block

    def _add_text(self, text: str) -> None:
        """Adds text to the current paragraph with the active formatting."""
        if self.current is None:
            self._open_block()
        flags = {name: count > 0 for name, count in self.formats.items()}
        flags["link"] = next((link for link in reversed(self.links) if link), None)
        runs = self.current.runs
        if runs and text != "\n" and runs[-1].text != "\n" and all(getattr(runs[-1], name) == flag for name, flag in flags.items()):
            runs[-1].text += text
        else:
            runs.append(HtmlRun(text, **flags))


def html_to_blocks(html: str) -> list[HtmlBlock]:
    """Converts the visual editor's HTML into the paragraphs to insert in the document (without empty ones)."""
    parser = _Parser()
    parser.feed(html)
    parser.close()
    return [block for block in parser.blocks if "".join(run.text for run in block.runs).strip()]
