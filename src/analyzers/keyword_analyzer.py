import re

from docx.document import Document

from ..compilers.docx_utils import iter_document_paragraphs
from .analyzer_interface import IAnalyzer

# Keywords in the form "<keyword>".
DEFAULT_KEYWORD_PATTERN = r"<\s*[A-Za-z][^<>]*?>"


class KeywordAnalyzer(IAnalyzer):
    """Extracts the keywords matching pattern, in order of appearance and without duplicates."""

    def __init__(self, pattern: str | re.Pattern = DEFAULT_KEYWORD_PATTERN):
        """pattern: regex (string or compiled) that identifies a keyword in the text of the paragraphs."""
        self.pattern = re.compile(pattern)
        self.keywords: list[str] = []

    def analyze(self, document: Document) -> None:
        """Looks for keywords in body, tables, content controls, headers and footers and saves them in self.keywords."""
        self.keywords = []
        for paragraph in iter_document_paragraphs(document):
            # Same text used by DocumentCompiler: the keywords found are the ones that can be compiled.
            text = "".join(run.text for run in paragraph.runs)
            for match in self.pattern.finditer(text):
                if match.group(0) not in self.keywords:
                    self.keywords.append(match.group(0))
