"""
Plugins: Python scripts in the plugins folder that create document contents from external data.

Everything a plugin needs is importable from here:

    from src.plugins import IPlugin, PluginParameter, PluginError, HEADING, PARAGRAPH, IMAGE, TABLE
"""
from ..builder.contents import NewHeading, NewImage, NewParagraph
from ..builder.formatting import Formatting
from ..builder.word_table import WordTable
from .plugin_interface import (
    CONTENT_TYPES,
    HEADING,
    IMAGE,
    PARAGRAPH,
    TABLE,
    IPlugin,
    PluginError,
    PluginInfo,
    PluginParameter,
)

__all__ = [
    "CONTENT_TYPES", "HEADING", "IMAGE", "PARAGRAPH", "TABLE",
    "IPlugin", "PluginError", "PluginInfo", "PluginParameter",
    "Formatting", "NewHeading", "NewImage", "NewParagraph", "WordTable",
]
