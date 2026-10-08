// Model of a table being edited (see TableEditor.svelte):
// - columns: [{ id, name, keep, width }]: headers; columns with keep = false do not end up in the table; width (px)
//   is the width of the column in the grid, used where the proportions matter (the Compiler);
// - rows: data rows in their base order, aligned with columns; each cell is plain text or { html } (richText.js);
// - sort: [{ columnId, direction: "asc" | "desc" }] by priority (a view over rows, which it does not change).
import { get } from "svelte/store";
import { language, tr } from "../../i18n.js";
import { valueText } from "../../richText.js";

let nextColumnId = 0;
// Width (px) of a new column of the grid and the limits of a resize.
export const DEFAULT_COLUMN_WIDTH = 160;
export const MIN_COLUMN_WIDTH = 80;
export const MAX_COLUMN_WIDTH = 800;

// Creates count included columns, named "Column N" (in the language of the web app) from start + 1.
export function createColumns(count, start = 0) {
  return Array.from({ length: count }, (_, index) => createColumn(tr("table.columnName", { number: start + index + 1 })));
}

// Creates an included column with the given name.
export function createColumn(name) {
  return { id: nextColumnId++, name, keep: true, width: DEFAULT_COLUMN_WIDTH };
}

// Copy of saved columns (e.g. a session restored): new ids, so they do not clash with the ones created since, and
// the default width where it is missing. Returns the columns and the id of each old column (to update sort rules).
export function restoreColumns(saved) {
  const ids = new Map();
  const columns = saved.map((column) => {
    const restored = { ...createColumn(column.name), keep: column.keep !== false, width: column.width ?? DEFAULT_COLUMN_WIDTH };
    ids.set(column.id, restored.id);
    return restored;
  });
  return { columns, ids };
}

// Creates rows empty rows of columns cells.
export function createRows(rows, columns) {
  return Array.from({ length: rows }, () => Array(columns).fill(""));
}

// Model of an existing table (rows of cells): with header the first row gives the column names (as plain text).
export function tableFromRows(rows, header) {
  const columns = Math.max(1, ...rows.map((row) => row.length));
  const padded = rows.map((row) => [...row, ...Array(columns - row.length).fill("")]);
  const [first = Array(columns).fill(""), ...body] = padded;
  return header
    ? { columns: first.map((name) => createColumn(valueText(name))), rows: body }
    : { columns: createColumns(columns), rows: padded };
}

// Row indexes in the order of sort; ties keep the base order (Array.sort is stable).
export function sortRowIndexes(rows, columns, sort) {
  const indexes = rows.map((_, index) => index);
  const rules = sort
    .map((rule) => ({ ...rule, index: columns.findIndex((column) => column.id === rule.columnId) }))
    .filter((rule) => rule.index !== -1);
  if (!rules.length) {
    return indexes;
  }
  // "Natural" comparison in the language of the web app: 9 comes before 10, upper and lower case are equal.
  const collator = new Intl.Collator(get(language), { numeric: true, sensitivity: "base" });
  return indexes.sort((first, second) => {
    for (const rule of rules) {
      const result = collator.compare(valueText(rows[first][rule.index]), valueText(rows[second][rule.index]));
      if (result) {
        return rule.direction === "asc" ? result : -result;
      }
    }
    return 0;
  });
}

// Final rows of the table: only the included columns, sorted rows and, with header, the names as the first row.
export function tableRows(columns, rows, sort, header) {
  const kept = columns.map((column, index) => (column.keep ? index : -1)).filter((index) => index !== -1);
  const body = sortRowIndexes(rows, columns, sort).map((rowIndex) => kept.map((index) => rows[rowIndex][index] ?? ""));
  return header ? [kept.map((index) => columns[index].name), ...body] : body;
}

// Returns a copy of items with the elements first and second swapped.
export function swap(items, first, second) {
  const copy = [...items];
  [copy[first], copy[second]] = [copy[second], copy[first]];
  return copy;
}
