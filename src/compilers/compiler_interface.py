from abc import ABC, abstractmethod

from docx.text.paragraph import Paragraph


class ICompiler(ABC):
    """Strategy that replaces a keyword with a content (text, image, table...)."""

    @abstractmethod
    def compile(self, keyword: str, paragraph: Paragraph) -> None:
        """Updates the document at every occurrence of keyword in the paragraph."""
