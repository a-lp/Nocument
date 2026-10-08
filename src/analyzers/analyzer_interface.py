from abc import ABC, abstractmethod

from docx.document import Document


class IAnalyzer(ABC):
    """Step of the analysis pipeline run when a document is loaded."""

    @abstractmethod
    def analyze(self, document: Document) -> None:
        """Analyzes the document and keeps the result in the analyzer."""
