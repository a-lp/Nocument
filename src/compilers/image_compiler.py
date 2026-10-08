from typing import IO

from docx.shape import InlineShape
from docx.shared import Length
from docx.text.paragraph import Paragraph

from .compiler_interface import ICompiler
from .docx_utils import isolate_keyword_runs


class ImageCompiler(ICompiler):
    """
    Replaces the keyword with an inline image.
    With only width or only height the image is scaled keeping its proportions; without them, it uses its native
    size, reduced if needed to the usable page width.
    """

    def __init__(self, image: str | IO[bytes], width: Length | None = None, height: Length | None = None):
        """image: path or stream of the image; width/height: optional size in the document."""
        self.image = image
        self.width = width
        self.height = height

    def compile(self, keyword: str, paragraph: Paragraph) -> None:
        """Replaces every occurrence of keyword in the paragraph with the image."""
        for run in isolate_keyword_runs(paragraph, keyword):
            run.text = ""
            # The stream must be rewound: the same image can replace several occurrences.
            if hasattr(self.image, "seek"):
                self.image.seek(0)
            shape = run.add_picture(self.image, width=self.width, height=self.height)
            if self.width is None and self.height is None:
                self._fit_to_page(shape, paragraph)

    @staticmethod
    def _fit_to_page(shape: InlineShape, paragraph: Paragraph) -> None:
        """Reduces the image to the usable page width, keeping its proportions."""
        # At its native size a photo can be wider than the page: it is reduced to the usable width.
        section = paragraph.part.package.main_document_part.document.sections[0]
        max_width = section.page_width - section.left_margin - section.right_margin
        if shape.width > max_width:
            shape.height = int(shape.height * max_width / shape.width)
            shape.width = max_width
