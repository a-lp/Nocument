from html import escape

from docx.oxml.ns import qn
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph

from .formatting import ALIGNMENTS
from .html_converter import safe_link

# Elements that editing a paragraph turns into plain text (or loses). Hyperlinks to web pages and e-mail addresses
# are kept (see web_link); the others (e.g. to bookmarks of the document) are lost.
COMPLEX_TAGS = (qn("w:fldSimple"), qn("w:fldChar"), qn("w:drawing"), qn("w:pict"), qn("w:object"))
ALIGNMENT_NAMES = {value: name for name, value in ALIGNMENTS.items()}


def paragraph_runs(paragraph: Paragraph) -> list:
    """Runs of the paragraph in text order, including those inside hyperlinks."""
    runs = []
    for content in paragraph.iter_inner_content():
        runs.extend(content.runs if isinstance(content, Hyperlink) else [content])
    return runs


def paragraph_html(paragraph: Paragraph) -> str:
    """
    HTML of the paragraph for the visual editor: explicit bold, italic, underline and strikethrough of the runs and
    the hyperlinks to web pages and e-mail addresses (<a href>); other hyperlinks become plain text.
    """
    html = ""
    for content in paragraph.iter_inner_content():
        if isinstance(content, Hyperlink):
            inner = "".join(_run_html(run, in_link=True) for run in content.runs)
            address = web_link(content)
            html += f'<a href="{escape(address)}">{inner}</a>' if address and inner else inner
        else:
            html += _run_html(content)
    return f"<p>{html}</p>"


def _run_html(run, in_link: bool = False) -> str:
    """
    HTML of a run: its text with the run's explicit bold, italic, underline and strikethrough. In a link the underline
    is part of the link's look (also when set on the run), not a formatting of the text.
    """
    if not run.text:
        return ""
    text = escape(run.text).replace("\n", "<br>")
    underline = run.underline and not in_link
    for enabled, tag in ((run.font.strike, "s"), (underline, "u"), (run.italic, "em"), (run.bold, "strong")):
        if enabled:
            text = f"<{tag}>{text}</{tag}>"
    return text


def web_link(hyperlink: Hyperlink) -> str | None:
    """Address of a hyperlink to a web page or an e-mail address (see safe_link), None for the others."""
    try:
        address = hyperlink.address
    except KeyError:
        # Relationship missing from the document.
        return None
    return safe_link(address) if address and not hyperlink.fragment else None


def has_web_links(paragraph: Paragraph) -> bool:
    """True if the paragraph contains hyperlinks to web pages or e-mail addresses."""
    return any(web_link(link) for link in paragraph.hyperlinks)


def paragraph_formatting(paragraph: Paragraph) -> dict:
    """
    Direct formatting of the paragraph (see Formatting): alignment and the character properties shared by all the
    runs with text; properties that vary between runs or come from the style are left out.
    """
    formatting = {}
    if paragraph.paragraph_format.alignment in ALIGNMENT_NAMES:
        formatting["alignment"] = ALIGNMENT_NAMES[paragraph.paragraph_format.alignment]
    runs = [run for run in paragraph_runs(paragraph) if run.text.strip()]
    if not runs:
        return formatting

    readers = {
        "font": lambda run: run.font.name,
        "size": lambda run: run.font.size.pt if run.font.size is not None else None,
        "color": lambda run: f"#{run.font.color.rgb}" if run.font.color.type is not None and run.font.color.rgb is not None else None,
        "bold": lambda run: run.bold,
        "italic": lambda run: run.italic,
        "underline": lambda run: bool(run.underline) if run.underline is not None else None,
    }
    for name, read in readers.items():
        values = {read(run) for run in runs}
        if len(values) == 1 and None not in values:
            formatting[name] = values.pop()
    return formatting


def has_complex_content(paragraph: Paragraph) -> bool:
    """True if the paragraph contains fields, objects or internal hyperlinks that editing would turn into plain text."""
    return any(True for _ in paragraph._p.iter(*COMPLEX_TAGS)) or any(
        not web_link(link) for link in paragraph.hyperlinks
    )
