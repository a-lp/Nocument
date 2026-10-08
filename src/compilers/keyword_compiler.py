from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from .compiler_interface import ICompiler
from .docx_utils import isolate_keyword_runs


class KeywordCompiler(ICompiler):
    """Replaces the keyword with a text, keeping the keyword's formatting."""

    def __init__(self, value: str | dict):
        """
        value: plain text to insert instead of the keyword, or {"html": ...} for rich text of the visual editor
        (bold and the like, hyperlinks; its paragraphs become line breaks, see rich_text.html_inline_runs).
        """
        self.value = value

    def compile(self, keyword: str, paragraph: Paragraph) -> None:
        """Replaces every occurrence of keyword in the paragraph with the text."""
        # Local import: the builder package imports the compilers' helpers.
        from ..builder.rich_text import html_inline_runs, html_run_elements

        for run in isolate_keyword_runs(paragraph, keyword):
            if isinstance(self.value, str):
                run.text = self.value
                continue
            properties = run._r.find(qn("w:rPr"))
            for element in reversed(html_run_elements(paragraph, html_inline_runs(self.value["html"]), properties)):
                run._r.addnext(element)
            run._r.getparent().remove(run._r)
