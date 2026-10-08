"""
Example plugin: sample data for every content type, without external services. Copy it as the starting point of a
new plugin (change id and name): a real plugin reads its data from a database, an API or a file instead.

Plugins are found in this folder (files starting with "_" or "." are skipped, free for shared helpers) and
reloaded when they change. They can import the standard library and the packages installed in the backend.
"""
from datetime import date
import struct
import zlib

from src.plugins import HEADING, IMAGE, PARAGRAPH, TABLE, IPlugin, PluginError, PluginParameter

SAMPLE_TEXT = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore "
    "magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo."
)
COLORS = {"teal": (35, 122, 120), "blue": (43, 87, 154), "red": (198, 40, 40)}
PRODUCTS = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"]


class SampleDataPlugin(IPlugin):
    id = "sample-data"
    name = "Sample data"
    description = "Example plugin: a dated heading, placeholder paragraphs, a bar chart and a sales table."
    version = "1.0"

    def parameters(self, content_type):
        """One form per content type; options could also come from the external data (e.g. a list of customers)."""
        if content_type == HEADING:
            return [
                PluginParameter("title", "Title", required=True, default="Status report"),
                PluginParameter("day", "Date", type="date", help="Added after the title."),
                PluginParameter("level", "Level", type="number", default=1, minimum=1, maximum=9),
            ]
        if content_type == PARAGRAPH:
            return [
                PluginParameter("count", "Paragraphs", type="number", default=2, minimum=1, maximum=10),
                PluginParameter("intro", "Opening sentence", type="textarea"),
            ]
        if content_type == IMAGE:
            return [
                PluginParameter("bars", "Bars", type="number", default=6, minimum=1, maximum=len(PRODUCTS)),
                PluginParameter("color", "Color", type="select", default="teal",
                                options=[(key, key.capitalize()) for key in COLORS]),
                PluginParameter("width", "Width (cm)", type="number", default=12, minimum=1, maximum=30),
            ]
        if content_type == TABLE:
            return [
                PluginParameter("rows", "Products", type="number", default=4, minimum=1, maximum=len(PRODUCTS)),
                PluginParameter("total", "Total row", type="checkbox", default=True),
                PluginParameter("caption", "Caption", default="Sales by product"),
            ]
        return []

    def compile_heading(self, values):
        day = date.fromisoformat(values["day"]).strftime("%d/%m/%Y") if values["day"] else None
        return self.heading(f"{values['title']} – {day}" if day else values["title"], int(values["level"] or 1))

    def compile_paragraph(self, values):
        paragraphs = [SAMPLE_TEXT] * int(values["count"] or 1)
        if values["intro"]:
            paragraphs.insert(0, values["intro"])
        return self.paragraph("\n\n".join(paragraphs))

    def compile_image(self, values):
        heights = [_sales(index) for index in range(int(values["bars"] or 1))]
        color = COLORS.get(values["color"] or "teal")
        if color is None:
            raise PluginError(f"Unknown color {values['color']}")
        return self.image(_bar_chart(heights, color), "chart.png", values["width"], "center")

    def compile_table(self, values):
        rows = [["Product", "Units", "Revenue (€)"]]
        products = PRODUCTS[:int(values["rows"] or 1)]
        rows += [[name, _sales(index), _sales(index) * 25] for index, name in enumerate(products)]
        if values["total"]:
            rows.append(["Total", sum(row[1] for row in rows[1:]), sum(row[2] for row in rows[1:])])
        return self.table(rows, header=True, caption=values["caption"] or "")


def _sales(index):
    """Deterministic sample value for the product at index."""
    return 40 + (index * 37) % 90


def _bar_chart(heights, color, bar_width=40, gap=12, height=200):
    """PNG of a bar chart (RGB, white background), written with the standard library only."""
    width = gap + len(heights) * (bar_width + gap)
    top = max(heights)
    rows = []
    for y in range(height):
        row = bytearray(b"\x00")  # PNG filter type of the row: none
        for x in range(width):
            index, offset = divmod(x - gap, bar_width + gap)
            inside = x >= gap and offset < bar_width and index < len(heights)
            filled = inside and height - y <= heights[index] * (height - 10) / top
            row += bytes(color) if filled else b"\xff\xff\xff"
        rows.append(bytes(row))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b"")
