from copy import deepcopy
import csv
from io import StringIO

from docx.oxml.ns import qn
from docx.shared import Twips
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from .compiler_interface import ICompiler
from .docx_utils import isolate_keyword_runs
from ..i18n import t

# Separators recognized in CSV files (Excel in Italian and other locales exports with ";").
CSV_DELIMITERS = ",;\t|"


class TableCompiler(ICompiler):
    """
    Fills a table starting from the row containing the keyword.
    The row is the template: it is filled with the first data row and duplicated (with the same formatting)
    for the next ones. With no data rows, the template row is removed.
    """

    def __init__(self, rows: list[list[str | dict]], column_widths: list[float] | None = None):
        """
        rows: data rows; each row is the list of the cell values, from left to right: plain text, or {"html": ...}
              for rich text with hyperlinks (see builder.rich_text).
        column_widths: relative widths of the template row's cells (e.g. [1, 3, 1]); the total width of the table
        does not change, only the proportions are redistributed.
        """
        self.rows = rows
        self.column_widths = column_widths

    @classmethod
    def from_csv(cls, content: bytes, has_header: bool = True, columns: list[int] | None = None) -> "TableCompiler":
        """
        Creates the compiler from the rows of a CSV.
        has_header: drops the first row (headers); columns: indexes of the columns to keep, in the wanted order.
        """
        rows, _ = cls.read_csv(content)
        if has_header:
            rows = rows[1:]
        if columns is not None:
            rows = [[row[index] for index in columns] for row in rows]
        return cls(rows)

    @staticmethod
    def read_csv(content: bytes) -> tuple[list[list[str]], bool]:
        """
        Reads a CSV (UTF-8, also with BOM, or Windows-1252) detecting the separator.
        Returns the non-empty rows, all with the same number of cells, and whether the first row looks like a header.
        """
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("cp1252", errors="replace")

        sample = text[:64 * 1024]
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample, delimiters=CSV_DELIMITERS)
        except csv.Error:
            # A single column or a separator that cannot be detected.
            dialect = csv.excel
        try:
            has_header = sniffer.has_header(sample)
        except csv.Error:
            has_header = False

        rows = [row for row in csv.reader(StringIO(text), dialect) if any(cell.strip() for cell in row)]
        width = max((len(row) for row in rows), default=0)
        return [row + [""] * (width - len(row)) for row in rows], has_header

    def compile(self, keyword: str, paragraph: Paragraph) -> None:
        """Fills the table containing the paragraph; raises ValueError if the keyword is not in a cell."""
        # Local import: the builder package imports the compilers' helpers.
        from ..builder.rich_text import set_cell_value

        row_element = next(paragraph._p.iterancestors(qn("w:tr")), None)
        if row_element is None:
            raise ValueError(t("errors.keywordNotInTable", keyword=keyword))

        for run in isolate_keyword_runs(paragraph, keyword):
            run.text = ""

        table = Table(row_element.getparent(), paragraph._parent)
        if self.column_widths:
            # Before duplicating the template row, so the copies inherit the new widths.
            self._apply_column_widths(table, row_element, keyword)

        if not self.rows:
            row_element.getparent().remove(row_element)
            return

        template_element = deepcopy(row_element)
        current_element = row_element
        for index, values in enumerate(self.rows):
            if index > 0:
                new_element = deepcopy(template_element)
                current_element.addnext(new_element)
                current_element = new_element
            cells = [_Cell(cell_element, table) for cell_element in current_element.tc_lst]
            for cell, value in zip(cells, values):
                set_cell_value(cell, value)

    def _apply_column_widths(self, table: Table, template_row, keyword: str) -> None:
        """
        Redistributes the width of the columns covered by the template row according to self.column_widths,
        keeping the total width. Merged cells (gridSpan) get the sum of the columns they cover.
        """
        cells = template_row.tc_lst
        if len(cells) != len(self.column_widths):
            raise ValueError(t("errors.columnWidthsCount", keyword=keyword, cells=len(cells), widths=len(self.column_widths)))
        grid_columns = table._tbl.tblGrid.gridCol_lst
        old_widths = [column.w.twips if column.w is not None else None for column in grid_columns]
        if None in old_widths:
            # Without the grid widths the total width to keep is unknown.
            return

        spans = []
        start = template_row.grid_before
        for cell in cells:
            spans.append((start, start + cell.grid_span))
            start += cell.grid_span
        if start > len(old_widths):
            return

        new_widths = list(old_widths)
        covered_total = sum(old_widths[spans[0][0]:spans[-1][1]])
        weights_total = sum(self.column_widths)
        assigned = 0
        for index, ((first, last), weight) in enumerate(zip(spans, self.column_widths)):
            # The last cell takes the rest, so rounding does not change the total width.
            is_last_cell = index == len(spans) - 1
            cell_width = covered_total - assigned if is_last_cell else round(covered_total * weight / weights_total)
            assigned += cell_width
            # Inside a merged cell, the grid columns keep their proportions.
            span_total = sum(old_widths[first:last])
            distributed = 0
            for column in range(first, last):
                if column == last - 1:
                    width = cell_width - distributed
                elif span_total:
                    width = round(cell_width * old_widths[column] / span_total)
                else:
                    width = round(cell_width / (last - first))
                new_widths[column] = width
                distributed += width

        for column, width in zip(grid_columns, new_widths):
            column.w = Twips(width)
        for row in table._tbl.tr_lst:
            column = row.grid_before
            for cell in row.tc_lst:
                cell.width = Twips(sum(new_widths[column:column + cell.grid_span]))
                column += cell.grid_span
        # With automatic layout Word would recompute the widths from the content.
        table.autofit = False
