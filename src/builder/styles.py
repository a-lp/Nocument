from docx.document import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Pt, RGBColor
from docx.styles.style import BaseStyle

from ..i18n import t

CAPTION_STYLE_ID = "Caption"


def find_style(document: Document, style_id: str | None, style_type: WD_STYLE_TYPE) -> BaseStyle | None:
    """
    Returns the style with the given id and of the expected type; None if style_id is empty.
    Raises ValueError if the style does not exist in the document.
    """
    if not style_id:
        return None
    for style in document.styles:
        if style.style_id == style_id and style.type == style_type:
            return style
    raise ValueError(t("errors.styleNotFound", style=style_id))


def is_caption_style(style: BaseStyle | None) -> bool:
    """True if the style is Word's default caption style ("Caption")."""
    return style is not None and (style.style_id == CAPTION_STYLE_ID or (style.name or "").lower() == "caption")


def caption_style(document: Document) -> BaseStyle:
    """
    Caption style of the document. If the template does not define it, creates Word's default style
    (italic 9 pt), which Word recognizes as its Caption style.
    """
    for style in document.styles:
        if style.type == WD_STYLE_TYPE.PARAGRAPH and is_caption_style(style):
            return style
    style = document.styles.add_style("Caption", WD_STYLE_TYPE.PARAGRAPH, builtin=True)
    style.base_style = document.styles.default(WD_STYLE_TYPE.PARAGRAPH)
    style.font.italic = True
    style.font.size = Pt(9)
    style.font.color.rgb = RGBColor(0x44, 0x54, 0x6A)
    return style


def adapt_missing_styles(document: Document, contents: list) -> list[str]:
    """
    Removes from the contents the styles the document does not define (e.g. contents saved from another
    template), so they use the document's default ones instead of making the insertion fail.
    Returns the ids of the removed styles, without duplicates and in alphabetical order.
    """
    available = {(style.style_id, style.type) for style in document.styles}
    missing = set()
    for content in contents:
        style = getattr(content, "style", None)
        # Only tables have table styles; headings, paragraphs and images use paragraph styles.
        style_type = WD_STYLE_TYPE.TABLE if hasattr(content, "rows") else WD_STYLE_TYPE.PARAGRAPH
        if style and (style, style_type) not in available:
            missing.add(style)
            content.style = None
    return sorted(missing)
