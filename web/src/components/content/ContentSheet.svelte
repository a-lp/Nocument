<script>
  import { sanitizeHtml } from "../../htmlSanitizer.js";
  import { isRichValue } from "../../richText.js";
  import { t } from "../../i18n.js";
  import { MOVE_CONTENT, NEW_CONTENT } from "./dragTypes.js";

  // A4 sheet with the contents of a block, in order. Contents are added by dragging them from the sidebar or with
  // the "+" button between two contents; contents are moved by dragging them and edited by clicking them.
  // contents: contents in the JSON format of the ContentBlocks (see content_from_dict).
  export let contents = [];
  export let disabled = false;
  // readonly: preview only (e.g. in the import modal), without additions, moves and edits;
  // compact: without the A4 sheet size, for preview boxes.
  export let readonly = false;
  export let compact = false;
  // onInsert(index, type): new content at position index (type null = to choose in the form).
  export let onInsert = () => {};
  // onMove(from, to): moves the content from from to the insertion position to (0..contents.length).
  export let onMove = () => {};
  export let onEdit = () => {};
  export let onDelete = () => {};

  const ALIGNMENTS = { left: "left", center: "center", right: "right", justify: "justify" };

  let sheet;
  // Insertion position highlighted while dragging (null if nothing is dragged over the sheet).
  let dropIndex = null;
  let draggingIndex = null;

  // True if the drag carries a content (new or to move) and not, for example, a file.
  function isContentDrag(event) {
    const types = event.dataTransfer?.types ?? [];
    return types.includes(NEW_CONTENT) || types.includes(MOVE_CONTENT);
  }

  // Insertion position nearest to the pointer: before the first content whose middle is below the pointer.
  function dropIndexAt(clientY) {
    const items = [...sheet.querySelectorAll("[data-content-index]")];
    const next = items.find((item) => {
      const rect = item.getBoundingClientRect();
      return clientY < rect.top + rect.height / 2;
    });
    return next ? Number(next.dataset.contentIndex) : contents.length;
  }

  // Shows where the dragged content will be inserted.
  function handleDragOver(event) {
    if (disabled || !isContentDrag(event)) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = event.dataTransfer.types.includes(MOVE_CONTENT) ? "move" : "copy";
    dropIndex = dropIndexAt(event.clientY);
  }

  // Removes the indicator when the pointer leaves the sheet (not when moving over an inner element).
  function handleDragLeave(event) {
    if (!sheet.contains(event.relatedTarget)) {
      dropIndex = null;
    }
  }

  // Inserts the new content or moves the dragged one to the given position.
  function handleDrop(event) {
    if (disabled || !isContentDrag(event)) {
      return;
    }
    event.preventDefault();
    const index = dropIndexAt(event.clientY);
    dropIndex = null;
    const type = event.dataTransfer.getData(NEW_CONTENT);
    const from = event.dataTransfer.getData(MOVE_CONTENT);
    if (type) {
      onInsert(index, type);
    } else if (from !== "") {
      onMove(Number(from), index);
    }
  }

  // Starts moving a content of the sheet.
  function handleItemDragStart(event, index) {
    event.dataTransfer.setData(MOVE_CONTENT, String(index));
    event.dataTransfer.effectAllowed = "move";
    draggingIndex = index;
  }

  // End of a drag (also a cancelled one).
  function handleDragEnd() {
    draggingIndex = null;
    dropIndex = null;
  }

  // Opens the editing when the content is clicked, except for clicks on the action buttons.
  function handleItemClick(event, index) {
    if (!disabled && !event.target.closest("button")) {
      onEdit(index);
    }
  }

  // Opens the editing with Enter or space on the focused content.
  function handleItemKeydown(event, index) {
    if (!disabled && (event.key === "Enter" || event.key === " ") && event.target === event.currentTarget) {
      event.preventDefault();
      onEdit(index);
    }
  }

  // Direct formatting of headings and paragraphs rendered in CSS, for a preview close to the document.
  function formattingStyle(formatting = {}) {
    return [
      formatting.font && `font-family: "${formatting.font}"`,
      formatting.size && `font-size: ${formatting.size}pt`,
      formatting.color && `color: ${formatting.color}`,
      formatting.alignment && `text-align: ${ALIGNMENTS[formatting.alignment]}`,
      formatting.bold === true && "font-weight: 700",
      formatting.bold === false && "font-weight: 400",
      formatting.italic === true && "font-style: italic",
      formatting.italic === false && "font-style: normal",
      formatting.underline === true && "text-decoration: underline"
    ].filter(Boolean).join("; ");
  }

  // Table rows with the same number of cells (merged cells read from Word have fewer).
  function tableRows(rows) {
    const columns = Math.max(...rows.map((row) => row.length));
    return rows.map((row) => [...row, ...Array(columns - row.length).fill("")]);
  }
</script>

{#snippet contentPreview(content)}
  {#if content.type === "heading"}
    <div class={`sheet-heading level-${Math.min(content.level, 4)}`} style={formattingStyle(content.formatting)}>{content.text}</div>
  {:else if content.type === "paragraph"}
    <div class="sheet-paragraph" style={formattingStyle(content.formatting)}>{@html sanitizeHtml(content.html)}</div>
  {:else if content.type === "image"}
    <div class="sheet-image" style={content.alignment ? `text-align: ${ALIGNMENTS[content.alignment]}` : ""}>
      <img
        src={`data:${content.content_type || "image/png"};base64,${content.data}`}
        alt={content.filename}
        style={content.width ? `width: ${content.width}cm` : ""}
        draggable="false"
      />
    </div>
  {:else if content.type === "table"}
    <figure class="sheet-table" style={content.alignment ? `text-align: ${ALIGNMENTS[content.alignment]}` : ""}>
      {#if content.caption && content.caption_position === "above"}<figcaption>{content.caption}</figcaption>{/if}
      <table>
        <tbody>
          {#each tableRows(content.rows) as row, rowIndex}
            <tr class:header-row={content.header && rowIndex === 0}>
              {#each row as cell}<td>{#if isRichValue(cell)}{@html sanitizeHtml(cell.html)}{:else}{cell}{/if}</td>{/each}
            </tr>
          {/each}
        </tbody>
      </table>
      {#if content.caption && content.caption_position !== "above"}<figcaption>{content.caption}</figcaption>{/if}
    </figure>
  {/if}
{/snippet}

{#snippet insertZone(index)}
  <div class="insert-zone sheet-insert-zone" class:drop-target={dropIndex === index}>
    <button
      class="insert-button"
      type="button"
      title={$t("sheet.addHere")}
      aria-label={$t("sheet.addHere")}
      {disabled}
      onclick={() => onInsert(index, null)}
    >+</button>
  </div>
{/snippet}

<div
  bind:this={sheet}
  class="a4-sheet"
  class:dragging-over={dropIndex !== null}
  class:compact
  class:readonly
  role="list"
  aria-label={$t("sheet.label")}
  ondragover={readonly ? undefined : handleDragOver}
  ondragleave={readonly ? undefined : handleDragLeave}
  ondrop={readonly ? undefined : handleDrop}
>
  {#if readonly}
    {#each contents as content, index (content.id)}
      <div class={`sheet-content sheet-${content.type}`} role="listitem">
        {@render contentPreview(content)}
      </div>
    {/each}
  {:else if !contents.length}
    <div class="sheet-empty" class:drop-target={dropIndex === 0}>
      <button class="insert-button sheet-empty-button" type="button" aria-label={$t("sheet.addFirst")} {disabled} onclick={() => onInsert(0, null)}>+</button>
      <span>{$t("sheet.empty")}</span>
    </div>
  {:else}
    {@render insertZone(0)}
    {#each contents as content, index (content.id)}
      <div
        class={`sheet-content sheet-${content.type}`}
        class:dragging={draggingIndex === index}
        data-content-index={index}
        role="listitem"
        tabindex="0"
        draggable={!disabled}
        aria-label={$t("sheet.itemLabel", { type: $t(`contentTypes.${content.type}`), number: index + 1 })}
        ondragstart={(event) => handleItemDragStart(event, index)}
        ondragend={handleDragEnd}
        onclick={(event) => handleItemClick(event, index)}
        onkeydown={(event) => handleItemKeydown(event, index)}
      >
        <div class="structure-actions sheet-actions">
          <span class="structure-style">{$t(`contentTypes.${content.type}`)}{content.style ? ` · ${content.style}` : ""}</span>
          <span class="sheet-drag-handle" title={$t("sheet.dragToMove")} aria-hidden="true">⠿</span>
          <button class="structure-action" type="button" title={$t("common.edit")} aria-label={$t("common.edit")} {disabled} onclick={() => onEdit(index)}>✎</button>
          <button class="structure-action delete" type="button" title={$t("common.delete")} aria-label={$t("common.delete")} {disabled} onclick={() => onDelete(index)}>🗑</button>
        </div>

        {@render contentPreview(content)}
      </div>
      {@render insertZone(index + 1)}
    {/each}
  {/if}
</div>
