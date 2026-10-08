<script>
  import { t } from "../../i18n.js";
  import { portal } from "../../portal.js";
  import { valueFromHtml, valueHtml } from "../../richText.js";
  import RichTextEditor from "../builder/RichTextEditor.svelte";

  // Visual editor of a table cell (opened from TableCell): formatting and hyperlinks. value: plain text or { html };
  // onSave(value) receives plain text again if the result has no formatting (see richText.js).
  export let value;
  export let label = "";
  export let onSave;
  export let onClose;

  let html = valueHtml(value);

  function save() {
    onSave(valueFromHtml(html));
  }

  function handleKeydown(event) {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
    }
  }
</script>

<!-- Under <body>, not inside the form of the content modal containing the table. -->
<div use:portal class="keyword-modal-backdrop cell-editor-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && onClose()} onkeydown={handleKeydown}>
  <div class="keyword-modal cell-editor" role="dialog" aria-modal="true" aria-labelledby="cell-editor-title">
    <button class="close-modal" type="button" aria-label={$t("common.close")} onclick={onClose}>×</button>
    <h2 id="cell-editor-title">{$t("table.cellEditorTitle")}</h2>
    {#if label}<span class="modal-intro">{label}</span>{/if}
    <RichTextEditor {html} label={label || $t("table.cellEditorTitle")} onChange={(value) => (html = value)} />
    <div class="cell-editor-actions">
      <button class="secondary-button" type="button" onclick={onClose}>{$t("common.cancel")}</button>
      <button type="button" onclick={save}>{$t("table.cellEditorSave")}</button>
    </div>
  </div>
</div>
