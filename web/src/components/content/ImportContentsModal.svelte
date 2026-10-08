<script>
  import { t } from "../../i18n.js";
  import ContentSheet from "./ContentSheet.svelte";

  // Modal showing the contents extracted from a Word document, grouped by heading (see import_contents), each in a
  // scrollable box: the user picks those to import and edits their names.
  // fileName: name of the file; documentTitle: name without extension; groups: [{ title, contents }].
  export let fileName;
  export let documentTitle;
  export let groups;
  export let warnings = [];
  export let isSaving = false;
  export let errorMessage = "";
  // With a single chosen group, onOpen(block) opens it in the content creation page, to edit it before saving it;
  // with several, onImport(blocks) saves them as separate blocks ([{ title, description, source, contents }]).
  export let onImport = () => {};
  export let onOpen = () => {};
  export let onClose = () => {};

  // Suggested name: the section heading; for the content before the first heading, the file name.
  let items = groups.map((group) => ({
    group,
    selected: true,
    title: group.title ?? (groups.length === 1 ? documentTitle : $t("import.introductionName", { document: documentTitle }))
  }));

  $: selectedItems = items.filter((item) => item.selected);

  // Summary of the content types of a group (e.g. "1 heading, 4 paragraphs").
  function describe(contents) {
    const counts = {};
    for (const content of contents) {
      counts[content.type] = (counts[content.type] ?? 0) + 1;
    }
    return Object.entries(counts).map(([type, count]) => $t(`contentCounts.${type}`, { count })).join(", ");
  }

  // Selects or deselects all the groups.
  function selectAll(selected) {
    items = items.map((item) => ({ ...item, selected }));
  }

  // Blocks to create with the chosen groups.
  function selectedBlocks() {
    return selectedItems.map((item) => ({
      title: item.title.trim() || documentTitle,
      description: $t("import.description", { file: fileName }),
      source: fileName,
      contents: item.group.contents
    }));
  }
</script>

<div class="keyword-modal-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && !isSaving && onClose()}>
  <div class="keyword-modal wide import-modal" role="dialog" aria-modal="true" aria-labelledby="import-modal-title">
    <button class="close-modal" type="button" aria-label={$t("common.close")} disabled={isSaving} onclick={onClose}>×</button>
    <p>{$t("nav.content")}</p>
    <h2 id="import-modal-title">{$t("import.title", { file: fileName })}</h2>
    <span class="modal-intro">{$t("import.intro")}</span>
    {#each warnings as warning}<p class="table-warning" role="status">{warning}</p>{/each}

    <div class="column-selection">
      <span>{$t("import.selected", { selected: selectedItems.length, total: items.length })}</span>
      <button class="secondary-button" type="button" disabled={selectedItems.length === items.length} onclick={() => selectAll(true)}>{$t("import.selectAll")}</button>
      <button class="secondary-button" type="button" disabled={!selectedItems.length} onclick={() => selectAll(false)}>{$t("import.deselectAll")}</button>
    </div>

    <ul class="import-groups">
      {#each items as item, index}
        <li class="import-group" class:unselected={!item.selected}>
          <div class="import-group-header">
            <input type="checkbox" bind:checked={items[index].selected} aria-label={$t("import.importItem", { title: item.title })} />
            <input class="import-group-title" type="text" bind:value={items[index].title} aria-label={$t("import.contentName")} disabled={!item.selected} />
            <span class="import-group-summary">{describe(item.group.contents)}</span>
          </div>
          <div class="import-group-preview" tabindex="0" role="region" aria-label={$t("import.preview", { title: item.title })}>
            <ContentSheet contents={item.group.contents} readonly compact />
          </div>
        </li>
      {/each}
    </ul>

    {#if errorMessage}<p class="compile-error" role="alert">{errorMessage}</p>{/if}
    <div class="content-actions">
      {#if selectedItems.length === 1}
        <button class="insert-content-button" type="button" disabled={isSaving} onclick={() => onOpen(selectedBlocks()[0])}>{$t("import.openInEditor")}</button>
      {:else}
        <button class="insert-content-button" type="button" disabled={isSaving || !selectedItems.length} onclick={() => onImport(selectedBlocks())}>
          {isSaving ? $t("import.importing") : $t("import.importCount", { count: selectedItems.length })}
        </button>
      {/if}
    </div>
  </div>
</div>
