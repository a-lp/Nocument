from dataclasses import asdict, dataclass
import re

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from ..i18n import t

ALIGNMENTS = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}
HEX_COLOR = re.compile(r"#?([0-9A-Fa-f]{6})$")


@dataclass
class Formatting:
    """
    Direct formatting applied over the style. Every None field keeps the style's value.
    size in points, color as "#RRGGBB", alignment one of "left", "center", "right", "justify".
    """
    font: str | None = None
    size: float | None = None
    color: str | None = None
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    alignment: str | None = None

    @classmethod
    def from_dict(cls, value) -> "Formatting":
        """Creates the formatting from the request JSON; raises ValueError if a field is not valid."""
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError(t("errors.formattingNotObject"))

        font = value.get("font") or None
        if font is not None and not isinstance(font, str):
            raise ValueError(t("errors.fontNotString"))
        size = value.get("size")
        if size is not None and (isinstance(size, bool) or not isinstance(size, (int, float)) or not 1 <= size <= 400):
            raise ValueError(t("errors.fontSize"))
        color = value.get("color") or None
        if color is not None and not (isinstance(color, str) and HEX_COLOR.match(color)):
            raise ValueError(t("errors.color"))
        alignment = value.get("alignment") or None
        if alignment is not None and alignment not in ALIGNMENTS:
            raise ValueError(t("errors.unsupportedAlignment", alignment=alignment))
        flags = {}
        for name in ("bold", "italic", "underline"):
            flag = value.get(name)
            if flag is not None and not isinstance(flag, bool):
                raise ValueError(t("errors.flagValue", name=name))
            flags[name] = flag
        return cls(font=font, size=size, color=color, alignment=alignment, **flags)

    def to_dict(self) -> dict:
        """JSON of the formatting with only the fields that are set (inverse of from_dict)."""
        return {name: value for name, value in asdict(self).items() if value is not None}

    def apply_to_paragraph(self, paragraph: Paragraph) -> None:
        """Applies the alignment to the paragraph and the character formatting to all its runs."""
        if self.alignment:
            paragraph.alignment = ALIGNMENTS[self.alignment]
        for run in paragraph.runs:
            self.apply_to_run(run)

    def apply_to_run(self, run: Run) -> None:
        """Applies the character formatting to the run (None fields are left alone)."""
        if self.font:
            run.font.name = self.font
        if self.size is not None:
            run.font.size = Pt(self.size)
        if self.color:
            run.font.color.rgb = RGBColor.from_string(HEX_COLOR.match(self.color).group(1).upper())
        if self.bold is not None:
            run.font.bold = self.bold
        if self.italic is not None:
            run.font.italic = self.italic
        if self.underline is not None:
            run.font.underline = self.underline
