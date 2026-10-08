from dataclasses import dataclass
import logging

from docx import Document
from docx.text.paragraph import Paragraph

from .compiler_interface import ICompiler
from .docx_utils import iter_document_paragraphs
from ..i18n import t

logger = logging.getLogger(__name__)


@dataclass
class KeywordMatch:
    """Occurrence of a keyword in a paragraph of the document."""
    keyword: str
    paragraph: Paragraph


class DocumentCompiler:
    """Compiles a Word document replacing every registered keyword with its own compiler."""

    def __init__(self, document_path: str):
        """document_path: path of the .docx to compile."""
        self.document_path = document_path
        self.keyword_mapping: dict[str, ICompiler] = {}
        self.found_keywords: list[KeywordMatch] = []
        self.document = None

    def add_keyword(self, keyword: str, compiler: ICompiler) -> None:
        """Maps keyword to the compiler to apply to each of its occurrences."""
        if not keyword:
            raise ValueError(t("errors.emptyKeyword"))
        self.keyword_mapping[keyword] = compiler

    def compile(self, output_path: str | None = None) -> bool:
        """
        Opens the document, applies the compilers to the keywords found and saves it in output_path
        (by default it overwrites the original document). Returns False if the document cannot be opened.
        """
        try:
            self.document = Document(self.document_path)
        except Exception:
            logger.exception("Cannot open the document %s", self.document_path)
            return False

        # First all occurrences are collected, then the document is changed: compilers alter its structure.
        self._search_keywords()
        for match in self.found_keywords:
            self.keyword_mapping[match.keyword].compile(match.keyword, match.paragraph)

        self.document.save(output_path or self.document_path)
        return True

    def _search_keywords(self) -> None:
        """Collects in self.found_keywords the paragraphs containing the registered keywords."""
        self.found_keywords = []
        for paragraph in iter_document_paragraphs(self.document):
            # Only the runs' text: it is what the compilers can change (it excludes e.g. hyperlinks).
            text = "".join(run.text for run in paragraph.runs)
            for keyword in self.keyword_mapping:
                if keyword in text:
                    self.found_keywords.append(KeywordMatch(keyword, paragraph))
