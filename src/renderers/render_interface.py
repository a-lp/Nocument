from abc import ABC, abstractmethod


class IRender(ABC):
    """Converter from a Word document to PDF."""

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """True if the renderer can work on this machine (e.g. the program it needs is installed)."""

    @abstractmethod
    def render_pdf(self, input_path: str, output_directory: str) -> str:
        """Converts the Word document to PDF inside output_directory and returns the PDF path."""

    @abstractmethod
    def update_toc(self, document_path: str, working_directory: str) -> bool:
        """
        Updates the tables of contents of the Word document (entries, numbering and pages) and saves it in place.
        working_directory is a temporary folder the renderer may use. Returns False if this renderer cannot
        update tables of contents.
        """
