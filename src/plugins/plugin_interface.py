"""
Interface of the plugins: Python scripts that bring external data into the web app as document contents
(IDocumentContent: headings, paragraphs, images and tables), inserted by the Builder and by the content blocks.

A plugin is a subclass of IPlugin in a .py file of the plugins folder (see registry.PluginRegistry). It declares:
- id, name, description and version;
- the parameters the user fills in the web app before asking for a content (parameters);
- one compile_<type> method for each content type it can create: the types with a compile method are its
  compatibilities, the content types the web app offers it for.
"""
from abc import ABC
from dataclasses import dataclass, field
from datetime import date
import html
import logging
import re
from typing import Any

from ..builder.content_interface import IDocumentContent
from ..builder.contents import NewHeading, NewImage, NewParagraph
from ..builder.formatting import Formatting
from ..builder.word_table import WordTable
from ..i18n import t
from ..logging_setup import get_logger

HEADING = "heading"
PARAGRAPH = "paragraph"
IMAGE = "image"
TABLE = "table"
CONTENT_TYPES = (HEADING, PARAGRAPH, IMAGE, TABLE)
# Class of the content each compile method must return.
CONTENT_CLASSES: dict[str, type[IDocumentContent]] = {
    HEADING: NewHeading,
    PARAGRAPH: NewParagraph,
    IMAGE: NewImage,
    TABLE: WordTable,
}

PARAMETER_TYPES = ("text", "password", "textarea", "number", "checkbox", "select", "date")
PLUGIN_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class PluginError(Exception):
    """Error of a plugin to show to the user as it is (e.g. "Customer 42 not found"); other exceptions are logged."""


@dataclass(frozen=True)
class PluginParameter:
    """
    Field of the form the web app shows before asking the plugin for a content.
    type: "text", "password" (text hidden while typing, e.g. a token), "textarea", "number", "checkbox", "select" or
    "date" (value "YYYY-MM-DD");
    options: choices of a "select", as values or (value, label) pairs; minimum and maximum limit a "number";
    default: initial value in the form; placeholder: text shown in the empty field (e.g. what happens if it is left
    empty); help: hint shown under the field.
    """
    name: str
    label: str
    type: str = "text"
    required: bool = False
    default: Any = None
    options: tuple = ()
    minimum: float | None = None
    maximum: float | None = None
    help: str = ""
    placeholder: str = ""

    def __post_init__(self):
        """Checks the definition: errors here are the plugin developer's, shown in the plugin list."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError(t("errors.pluginParameterName"))
        if self.type not in PARAMETER_TYPES:
            raise ValueError(t("errors.pluginParameterType", name=self.name, type=self.type))
        if self.type == "select" and not self.options:
            raise ValueError(t("errors.pluginParameterOptions", name=self.name))
        # Options normalized to (value, label) pairs.
        object.__setattr__(self, "options", tuple(
            (str(option[0]), str(option[1])) if isinstance(option, (tuple, list)) else (str(option), str(option))
            for option in self.options
        ))

    def to_dict(self) -> dict:
        """JSON of the parameter, used by the frontend to draw the field."""
        return {
            "name": self.name,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "options": [{"value": value, "label": label} for value, label in self.options],
            "minimum": self.minimum,
            "maximum": self.maximum,
            "help": self.help,
            "placeholder": self.placeholder,
        }

    def parse(self, value):
        """Value sent by the web app converted to the parameter type; raises ValueError if it is not valid."""
        if value is None or value == "":
            if self.required and self.type != "checkbox":
                raise ValueError(t("errors.parameterRequired", label=self.label))
            return False if self.type == "checkbox" else None
        if self.type == "checkbox":
            if not isinstance(value, bool):
                raise ValueError(t("errors.parameterInvalid", label=self.label))
            return value
        if self.type == "number":
            if isinstance(value, bool):
                raise ValueError(t("errors.parameterNumber", label=self.label))
            try:
                number = float(value)
            except (TypeError, ValueError) as error:
                raise ValueError(t("errors.parameterNumber", label=self.label)) from error
            if self.minimum is not None and number < self.minimum:
                raise ValueError(t("errors.parameterMinimum", label=self.label, minimum=self.minimum))
            if self.maximum is not None and number > self.maximum:
                raise ValueError(t("errors.parameterMaximum", label=self.label, maximum=self.maximum))
            return int(number) if number.is_integer() else number
        if not isinstance(value, str):
            raise ValueError(t("errors.parameterInvalid", label=self.label))
        if self.type == "select" and value not in (option[0] for option in self.options):
            raise ValueError(t("errors.parameterOption", label=self.label))
        if self.type == "date":
            try:
                date.fromisoformat(value)
            except ValueError as error:
                raise ValueError(t("errors.parameterDate", label=self.label)) from error
        return value


@dataclass(frozen=True)
class PluginInfo:
    """Description of a loaded plugin, for the lists of the web app."""
    id: str
    name: str
    description: str
    version: str
    file: str
    compatibilities: list[str] = field(default_factory=list)
    # The package has the custom interface (ui.svelte) and the README; legacy: loose script, without package.
    has_ui: bool = False
    has_readme: bool = False
    legacy: bool = False

    def to_dict(self) -> dict:
        """JSON of the plugin; file is the name of its package folder (or of the loose script)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "file": self.file,
            "compatibilities": self.compatibilities,
            "has_ui": self.has_ui,
            "has_readme": self.has_readme,
            "legacy": self.legacy,
        }


class IPlugin(ABC):
    """
    Base class of the plugins. A plugin defines id (lowercase letters, digits, "-" and "_", unique among the
    installed plugins) and name, and overrides the compile methods of the content types it supports: each one
    receives the values of its parameters, already validated and converted (see PluginParameter.parse), and returns
    the content, preferably built with the helpers heading, paragraph, image and table.
    It is created once, without arguments, when its file is loaded; raise PluginError for errors the user should read.
    Messages for the server log go through self.logger (logger "nocument.plugins.<id>"); print() works too: while
    the registry runs the plugin, its output becomes records of the same logger.
    """

    id: str = ""
    name: str = ""
    description: str = ""
    version: str = "1.0"

    @property
    def logger(self) -> logging.Logger:
        """Logger of the plugin, in the centralized log of the backend (see logging_setup)."""
        return get_logger(f"plugins.{self.id or type(self).__name__}")

    def parameters(self, content_type: str) -> list[PluginParameter]:
        """Parameters to ask before creating a content of content_type (one of CONTENT_TYPES); none by default."""
        return []

    def compile_heading(self, values: dict) -> NewHeading:
        """Heading created from the parameter values."""
        raise NotImplementedError

    def compile_paragraph(self, values: dict) -> NewParagraph:
        """Paragraph (or paragraphs) created from the parameter values."""
        raise NotImplementedError

    def compile_image(self, values: dict) -> NewImage:
        """Image created from the parameter values."""
        raise NotImplementedError

    def compile_table(self, values: dict) -> WordTable:
        """Table created from the parameter values."""
        raise NotImplementedError

    def compatibilities(self) -> list[str]:
        """Content types the plugin can create: those whose compile method it overrides."""
        return [
            content_type for content_type in CONTENT_TYPES
            if getattr(type(self), f"compile_{content_type}") is not getattr(IPlugin, f"compile_{content_type}")
        ]

    # ---- Helpers to create the contents ----

    @staticmethod
    def heading(text: str, level: int = 1, style: str | None = None, **formatting) -> NewHeading:
        """
        Heading of the given level (1-9). style is the id of a document style (by default the one of the level);
        formatting: font, size, color ("#RRGGBB"), bold, italic, underline, alignment.
        """
        return NewHeading(text, level, style, Formatting(**formatting))

    @staticmethod
    def paragraph(text: str | None = None, html_text: str | None = None, style: str | None = None,
                  **formatting) -> NewParagraph:
        """
        Paragraph from plain text (each line, separated by an empty line, is a new paragraph) or from HTML
        (html_text: <p>, <b>, <i>, <u>, <s>, <br>, <ul>/<ol> with <li>). formatting as in heading, except the
        emphasis (bold, italic, underline), which goes in the HTML.
        """
        if html_text is None:
            blocks = [block for block in re.split(r"\n\s*\n", text or "") if block.strip()]
            html_text = "".join(f"<p>{html.escape(block.strip()).replace(chr(10), '<br>')}</p>" for block in blocks)
        return NewParagraph(html_text, style, Formatting(**formatting))

    @staticmethod
    def image(data: bytes, filename: str = "image", width: float | None = None,
              alignment: str | None = None) -> NewImage:
        """Image (PNG, JPEG, GIF, BMP or TIFF bytes); width in centimeters, alignment "left", "center", "right"."""
        return NewImage(data, filename, width, alignment)

    @staticmethod
    def table(rows: list[list], header: bool = True, caption: str = "", caption_position: str = "below",
              style: str | None = None, alignment: str | None = None) -> WordTable:
        """
        Table from rows of values (converted to text; None becomes empty); with header the first row is the
        header. caption_position is "above" or "below".
        """
        text_rows = [["" if cell is None else str(cell) for cell in row] for row in rows]
        return WordTable(text_rows, caption, caption_position, header, style, alignment)
