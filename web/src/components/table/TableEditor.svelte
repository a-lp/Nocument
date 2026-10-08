<script>
  import { apiFetch } from "../../api.js";
  import { t } from "../../i18n.js";
  import {
    DEFAULT_COLUMN_WIDTH, MAX_COLUMN_WIDTH, MIN_COLUMN_WIDTH, createColumns, createRows, createColumn, sortRowIndexes, swap
  } from "./tableModel.js";
  import TableCell from "./TableCell.svelte";

  // Grid to edit a table (model in tableModel.js), the same everywhere a table is written (Builder, content blocks,
  // Compiler): rows and columns, CSV import, columns to include or exclude, reordering of columns and rows, sorting
  // on several columns and cells with formatting and links (TableCell).
  // header: the first row of the table is the header, written in the column names (editable); headerLabel and hint
  // replace the texts of the checkbox and of the hint (e.g. in the Compiler, where the names are not inserted).
  // resizable: the columns can be widened or narrowed (border of the header, arrows, double click to reset);
  // onColumnResize() is called at every change of a width.
  export let columns;
  export let rows;
  export let sort = [];
  export let header = false;
  export let maxRows = 200;
  export let maxColumns = 20;
  export let headerLabel = null;
  export let hint = null;
  export let resizable = false;
  export let onColumnResize = () => {};

  // Width (px) of the column of the row actions, when the columns have a width.
  const ROW_ACTIONS_WIDTH = 104;

  let csvInput;
  let csvRows = null;
  let csvError = "";
  let csvNotice = "";
  let isImportingCsv = false;

  $: keptColumnCount = columns.filter((column) => column.keep).length;
  $: sortedRowIndexes = sortRowIndexes(rows, columns, sort);
  // With the header the table may have no data rows.
  $: minRows = header ? 0 : 1;
  $: tableWidth = ROW_ACTIONS_WIDTH + columns.reduce((total, column) => total + (column.width ?? DEFAULT_COLUMN_WIDTH), 0);

  // Resizes the grid keeping the values already entered.
  function resize(rowCount, columnCount) {
    rowCount = Math.min(maxRows, Math.max(minRows, Number(rowCount) || 0));
    columnCount = Math.min(maxColumns, Math.max(1, Number(columnCount) || 1));
    rows = Array.from({ length: rowCount }, (_, rowIndex) =>
      Array.from({ length: columnCount }, (_, columnIndex) => rows[rowIndex]?.[columnIndex] ?? "")
    );
    columns = [...columns.slice(0, columnCount), ...createColumns(Math.max(0, columnCount - columns.length), columns.length)];
    sort = sort.filter((rule) => columns.some((column) => column.id === rule.columnId));
  }

  // Reads the chosen CSV through the backend and loads its rows into the grid.
  async function importCsv(event) {
    const [file] = event.target.files;
    event.target.value = "";
    if (!file) {
      return;
    }
    isImportingCsv = true;
    csvError = "";
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await apiFetch("/api/parse-csv", { method: "POST", body: formData });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("errors.csvUnreadable"));
      }
      csvRows = data.rows;
      header = data.has_header;
      applyCsv();
    } catch (error) {
      csvError = error.message;
    } finally {
      isImportingCsv = false;
    }
  }

  // Fills the grid with the imported CSV; with the header the first row gives the column names.
  function applyCsv() {
    const width = Math.min(maxColumns, csvRows[0].length);
    const [first, ...body] = csvRows.map((row) => row.slice(0, width));
    const data = header ? body : [first, ...body];
    rows = data.slice(0, maxRows);
    if (!header && !rows.length) {
      rows = createRows(1, width);
    }
    columns = header ? first.map((name, index) => createColumn(name.trim() || $t("table.columnName", { number: index + 1 }))) : createColumns(width);
    sort = [];
    csvNotice = csvRows[0].length > maxColumns || data.length > maxRows
      ? $t("table.csvTrimmed", { rows: maxRows, columns: maxColumns })
      : "";
  }

  // Includes or excludes all the columns.
  function setAllColumns(keep) {
    columns = columns.map((column) => ({ ...column, keep }));
  }

  // Moves column index by offset positions (-1 left, +1 right).
  function moveColumn(index, offset) {
    const target = index + offset;
    if (target >= 0 && target < columns.length) {
      columns = swap(columns, index, target);
      rows = rows.map((row) => swap(row, index, target));
    }
  }

  // Moves row index by offset positions (-1 up, +1 down).
  function moveRow(index, offset) {
    const target = index + offset;
    if (target >= 0 && target < rows.length) {
      rows = swap(rows, index, target);
    }
  }

  // Deletes row index (without header at least one stays).
  function removeRow(index) {
    rows = rows.length > minRows ? rows.filter((_, rowIndex) => rowIndex !== index) : createRows(1, columns.length);
  }

  // Sets the width (px) of column columnId within the limits.
  function setColumnWidth(columnId, width) {
    width = Math.round(Math.min(MAX_COLUMN_WIDTH, Math.max(MIN_COLUMN_WIDTH, width)));
    columns = columns.map((column) => (column.id === columnId ? { ...column, width } : column));
    onColumnResize();
  }

  // Starts resizing a column by dragging the right border of its header.
  function startColumnResize(event, column) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = column.width ?? DEFAULT_COLUMN_WIDTH;
    const resize = (moveEvent) => setColumnWidth(column.id, startWidth + moveEvent.clientX - startX);
    window.addEventListener("pointermove", resize);
    window.addEventListener("pointerup", () => window.removeEventListener("pointermove", resize), { once: true });
  }

  // Resizes the column with the left/right arrows.
  function resizeColumnWithKeyboard(event, column) {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      setColumnWidth(column.id, (column.width ?? DEFAULT_COLUMN_WIDTH) + (event.key === "ArrowLeft" ? -20 : 20));
    }
  }

  // Cycles the sorting of the column: none -> ascending -> descending -> none.
  // A newly sorted column is appended after the others, with a lower priority.
  function toggleSort(columnId) {
    const rule = sort.find((item) => item.columnId === columnId);
    if (!rule) {
      sort = [...sort, { columnId, direction: "asc" }];
    } else if (rule.direction === "asc") {
      sort = sort.map((item) => (item === rule ? { ...item, direction: "desc" } : item));
    } else {
      sort = sort.filter((item) => item !== rule);
    }
  }
</script>

<div class="table-editor-tool">
  <div class="builder-table-options">
    <label>{$t("table.dataRows")}<input type="number" min={minRows} max={maxRows} value={rows.length} oninput={(event) => resize(event.target.value, columns.length)} /></label>
    <label>{$t("table.columns")}<input type="number" min="1" max={maxColumns} value={columns.length} oninput={(event) => resize(rows.length, event.target.value)} /></label>
  </div>
  <div class="csv-import">
    <input bind:this={csvInput} type="file" accept=".csv,text/csv" onchange={importCsv} hidden />
    <button class="secondary-button" type="button" disabled={isImportingCsv} onclick={() => csvInput?.click()}>
      {isImportingCsv ? $t("table.importingCsv") : $t("table.importCsv")}
    </button>
    <label class="csv-header-toggle">
      <input type="checkbox" checked={header} onchange={(event) => { header = event.target.checked; if (csvRows) applyCsv(); }} />
      {headerLabel ?? $t("table.firstRowHeader")}
    </label>
  </div>
  {#if csvError}<p class="compile-error" role="alert">{csvError}</p>{/if}
  {#if csvNotice}<p class="table-warning" role="status">{csvNotice}</p>{/if}
  <span class="table-hint">
    {#if hint}{hint}{:else}{$t("table.hint")}{#if header}{" "}{$t("table.headerHint")}{/if}{/if}
  </span>
  <!-- Notes of the page using the editor (e.g. the Compiler's column check), above the grid. -->
  <slot />
  {#if !keptColumnCount}<p class="compile-error" role="alert">{$t("table.selectOneColumn")}</p>{/if}
  <div class="column-selection">
    <span>{$t("table.selectedColumns", { selected: keptColumnCount, total: columns.length })}</span>
    <button class="secondary-button" type="button" disabled={keptColumnCount === columns.length} onclick={() => setAllColumns(true)}>{$t("table.selectAll")}</button>
    <button class="secondary-button" type="button" disabled={!keptColumnCount} onclick={() => setAllColumns(false)}>{$t("table.deselectAll")}</button>
  </div>

  <div class="table-editor">
    <table class="builder-table-grid" class:resizable style={resizable ? `width: ${tableWidth}px` : undefined}>
      {#if resizable}
        <colgroup>
          <col style={`width: ${ROW_ACTIONS_WIDTH}px`} />
          {#each columns as column (column.id)}
            <col style={`width: ${column.width ?? DEFAULT_COLUMN_WIDTH}px`} />
          {/each}
        </colgroup>
      {/if}
      <thead>
        <tr>
          <th class="row-actions"></th>
          {#each columns as column, columnIndex (column.id)}
            {@const sortIndex = sort.findIndex((rule) => rule.columnId === column.id)}
            {@const direction = sort[sortIndex]?.direction}
            <th class:excluded={!column.keep} aria-sort={direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none"}>
              <div class="column-header">
                <input type="checkbox" bind:checked={columns[columnIndex].keep} aria-label={$t("table.includeColumn", { column: column.name })} title={$t("table.includeColumnHint")} />
                <button class="column-sort" class:sorted={direction} type="button" title={$t("table.sortHint", { column: column.name })} onclick={() => toggleSort(column.id)}>
                  <span class="column-name">{column.name}</span>
                  {#if direction}
                    <span class="sort-indicator">{direction === "asc" ? "▲" : "▼"}{#if sort.length > 1}<sup>{sortIndex + 1}</sup>{/if}</span>
                  {/if}
                </button>
                <button class="icon-button" type="button" disabled={columnIndex === 0} aria-label={$t("table.moveLeft", { column: column.name })} onclick={() => moveColumn(columnIndex, -1)}>←</button>
                <button class="icon-button" type="button" disabled={columnIndex === columns.length - 1} aria-label={$t("table.moveRight", { column: column.name })} onclick={() => moveColumn(columnIndex, 1)}>→</button>
              </div>
              {#if resizable}
                <button
                  class="column-resize-handle"
                  type="button"
                  aria-label={$t("table.resizeColumn", { column: column.name, width: column.width ?? DEFAULT_COLUMN_WIDTH })}
                  title={$t("sidebar.resizeHint")}
                  onpointerdown={(event) => startColumnResize(event, column)}
                  onkeydown={(event) => resizeColumnWithKeyboard(event, column)}
                  ondblclick={() => setColumnWidth(column.id, DEFAULT_COLUMN_WIDTH)}
                ></button>
              {/if}
            </th>
          {/each}
        </tr>
        {#if header}
          <tr class="header-row">
            <td class="row-actions table-row-label">{$t("table.header")}</td>
            {#each columns as column, columnIndex (column.id)}
              <td class:excluded={!column.keep}>
                <input type="text" bind:value={columns[columnIndex].name} aria-label={$t("table.columnHeader", { number: columnIndex + 1 })} />
              </td>
            {/each}
          </tr>
        {/if}
      </thead>
      <tbody>
        {#each sortedRowIndexes as rowIndex, position (rowIndex)}
          <tr>
            <td class="row-actions">
              <!-- With an active sort the row order is computed: moving rows by hand is disabled. -->
              <button class="icon-button" type="button" disabled={sort.length > 0 || position === 0} title={sort.length ? $t("table.removeSortToMove") : undefined} aria-label={$t("table.moveRowUp", { number: position + 1 })} onclick={() => moveRow(rowIndex, -1)}>↑</button>
              <button class="icon-button" type="button" disabled={sort.length > 0 || position === rows.length - 1} title={sort.length ? $t("table.removeSortToMove") : undefined} aria-label={$t("table.moveRowDown", { number: position + 1 })} onclick={() => moveRow(rowIndex, 1)}>↓</button>
              <button class="icon-button remove-row" type="button" aria-label={$t("table.deleteRow", { number: position + 1 })} onclick={() => removeRow(rowIndex)}>×</button>
            </td>
            {#each rows[rowIndex] as _cell, columnIndex}
              <td class:excluded={!columns[columnIndex]?.keep}>
                <TableCell bind:value={rows[rowIndex][columnIndex]} label={$t("table.cell", { row: position + 1, column: columns[columnIndex]?.name })} />
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
