<script>
  import { t } from "../../i18n.js";
  import { sanitizeHtml } from "../../htmlSanitizer.js";
  import { isRichValue } from "../../richText.js";
  import CellEditorModal from "./CellEditorModal.svelte";

  // Cell of a table grid (TableEditor, Compiler): plain text is typed in the field; the mark in the bottom right
  // corner opens the visual editor (formatting, hyperlinks). A cell with rich text shows its preview, which opens
  // the editor too. value is bound: plain text or { html } (see richText.js).
  export let value = "";
  export let label = "";

  let editing = false;
</script>

<div class="table-cell" class:rich={isRichValue(value)}>
  {#if isRichValue(value)}
    <button class="table-cell-preview" type="button" title={$t("table.editCellHint")} aria-label={$t("table.editCell", { cell: label })} onclick={() => (editing = true)}>
      <!-- The preview only shows the text: its links are not followed from here. -->
      <span class="table-cell-html" inert>{@html sanitizeHtml(value.html)}</span>
    </button>
  {:else}
    <input type="text" bind:value aria-label={label} />
  {/if}
  <button class="table-cell-expand" type="button" title={$t("table.editCellHint")} aria-label={$t("table.editCell", { cell: label })} onclick={() => (editing = true)}>
    <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M11 5 5 11M11 8.5 8.5 11" /></svg>
  </button>
</div>

{#if editing}
  <CellEditorModal
    {value}
    {label}
    onSave={(edited) => {
      value = edited;
      editing = false;
    }}
    onClose={() => (editing = false)}
  />
{/if}
