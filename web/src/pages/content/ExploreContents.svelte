<script>
  import { confirmAction } from "../../confirm.js";
  import BackButton from "../../components/BackButton.svelte";
  import { onDestroy, onMount } from "svelte";
  import { apiFetch } from "../../api.js";
  import { language, t } from "../../i18n.js";
  import ContentSheet from "../../components/content/ContentSheet.svelte";
  import SidebarResizer from "../../components/SidebarResizer.svelte";

  // Exploration of the saved ContentBlocks: filters in the sidebar (title, description, import file) and, in the
  // main section, the blocks with title, ID, description, the Edit and Delete buttons and a scrollable box with the
  // contents. Edit opens the block in the Add new content page (/content/edit/<id>).
  // pickMode: choice of the blocks to add to the Add new content sheet: the cards are selected (in order) and the
  // fixed Add and Cancel buttons call onPick(chosen blocks) and onCancel; excludeId is a block not to offer
  // (the one open in the sheet).
  export let navigate = null;
  export let pickMode = false;
  export let excludeId = null;
  export let onPick = () => {};
  export let onCancel = () => {};

  const PAGE_SIZE = 20;
  // Wait after the last key before searching, so there is no request at every letter.
  const SEARCH_DELAY_MS = 300;

  // Width (px) of the filter sidebar, resizable (the same also in the choice of contents).
  let sidebarWidth = 300;
  let titleFilter = "";
  let descriptionFilter = "";
  // Chosen origins: import files and/or blocks created by hand; with no choice all are shown.
  let selectedSources = [];
  let manualSelected = false;
  let sources = [];
  let deletingId = "";
  // Blocks chosen in pickMode, in selection order (they stay chosen when the filters change).
  let pickedBlocks = [];
  let items = [];
  let total = 0;
  let isLoading = false;
  let errorMessage = "";
  let copiedId = "";
  let searchTimer;
  // Identifies the last search: answers of earlier searches arriving later are ignored.
  let requestToken = 0;

  $: visibleItems = items.filter((block) => block.id !== excludeId);
  $: pickedIds = new Set(pickedBlocks.map((block) => block.id));
  $: hasFilters = Boolean(titleFilter.trim() || descriptionFilter.trim() || selectedSources.length || manualSelected);

  onMount(() => {
    loadSources();
    search();
  });

  onDestroy(() => clearTimeout(searchTimer));

  // Loads the import files for the filter.
  async function loadSources() {
    try {
      const response = await apiFetch("/api/content-blocks/sources");
      if (response.ok) {
        sources = (await response.json()).sources;
      }
    } catch {
      // Without the file list the filter still offers "Created by hand".
    }
  }

  // Search parameters with the current filters.
  function queryParams(skip) {
    const params = new URLSearchParams({ full: "true", skip: String(skip), limit: String(PAGE_SIZE) });
    if (titleFilter.trim()) {
      params.set("title", titleFilter.trim());
    }
    if (descriptionFilter.trim()) {
      params.set("description", descriptionFilter.trim());
    }
    for (const source of selectedSources) {
      params.append("source", source);
    }
    if (manualSelected) {
      params.set("manual", "true");
    }
    return params;
  }

  // Searches the blocks with the current filters; with append it adds the next page to those already shown.
  async function search(append = false) {
    clearTimeout(searchTimer);
    const token = ++requestToken;
    isLoading = true;
    errorMessage = "";
    try {
      const response = await apiFetch(`/api/content-blocks?${queryParams(append ? items.length : 0)}`);
      const data = await response.json().catch(() => null);
      if (token !== requestToken) {
        return;
      }
      if (!response.ok) {
        throw new Error(data?.error || $t("explore.loadError"));
      }
      items = append ? [...items, ...data.items] : data.items;
      total = data.total;
    } catch (error) {
      if (token === requestToken) {
        errorMessage = error.message;
      }
    } finally {
      if (token === requestToken) {
        isLoading = false;
      }
    }
  }

  // Repeats the search shortly after the last key pressed in a text field.
  function scheduleSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => search(), SEARCH_DELAY_MS);
  }

  // Clears the filters and shows all the blocks.
  function resetFilters() {
    titleFilter = "";
    descriptionFilter = "";
    selectedSources = [];
    manualSelected = false;
    search();
  }

  // Adds or removes an import file from the filters and repeats the search.
  function toggleSource(source, checked) {
    selectedSources = checked ? [...selectedSources, source] : selectedSources.filter((item) => item !== source);
    search();
  }

  // Deletes a block from the database, after confirmation, and removes it from the list.
  async function deleteBlock(block) {
    if (!(await confirmAction($t("explore.confirmDelete", { title: block.title || block.id }), { title: $t("confirm.titles.deleteContent"), action: $t("confirm.actions.delete"), danger: true }))) {
      return;
    }
    deletingId = block.id;
    errorMessage = "";
    try {
      const response = await apiFetch(`/api/content-blocks/${block.id}`, { method: "DELETE" });
      // 404: it was already deleted (e.g. from another tab), so it is removed from the list anyway.
      if (!response.ok && response.status !== 404) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.error || $t("explore.deleteError"));
      }
      items = items.filter((item) => item.id !== block.id);
      total = Math.max(0, total - 1);
      // The source file may have no blocks left: the filters are updated.
      loadSources();
    } catch (error) {
      errorMessage = error.message;
    } finally {
      deletingId = "";
    }
  }

  // Copies the ID of a block to the clipboard (if the browser allows it) and signals it for a moment.
  async function copyId(id) {
    try {
      await navigator.clipboard.writeText(id);
      copiedId = id;
      setTimeout(() => {
        if (copiedId === id) {
          copiedId = "";
        }
      }, 1500);
    } catch {
      // Outside HTTPS the clipboard may be unavailable: the ID can still be selected.
    }
  }

  // Chooses or removes a block in pickMode.
  function togglePick(block) {
    pickedBlocks = pickedIds.has(block.id)
      ? pickedBlocks.filter((picked) => picked.id !== block.id)
      : [...pickedBlocks, block];
  }

  // In pickMode a click on the card chooses it, except clicks on controls and on the scrollable preview.
  function handleCardClick(event, block) {
    if (pickMode && !event.target.closest("button, input, a, .explore-card-preview")) {
      togglePick(block);
    }
  }

  // Esc cancels the choice.
  function handleKeydown(event) {
    if (pickMode && event.key === "Escape") {
      onCancel();
    }
  }

  // Date and time in the format of the web app's language.
  function formatDate(value) {
    return new Date(value).toLocaleString($language, { dateStyle: "short", timeStyle: "short" });
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="content-page" class:picking={pickMode} style={`--sidebar-width: ${sidebarWidth}px`}>
  <aside class="context-sidebar content-sidebar" aria-label={$t("explore.filtersLabel")}>
    <div class="sidebar-title">
      <!-- Not while choosing contents: the choice is closed with Cancel, not by leaving the page. -->
      {#if !pickMode}<BackButton onDark />{/if}
      <div>
        <p>{$t("nav.content")}</p>
        <h2>{pickMode ? $t("explore.pickTitle") : $t("nav.exploreContents")}</h2>
        {#if pickMode}
          <span class="palette-hint">{$t("explore.pickHint")}</span>
        {/if}
      </div>
    </div>

    <label class="content-field" for="filter-title">
      {$t("explore.title")}
      <input id="filter-title" type="search" bind:value={titleFilter} oninput={scheduleSearch} placeholder={$t("explore.titlePlaceholder")} />
    </label>
    <label class="content-field" for="filter-description">
      {$t("addContent.description")}
      <input id="filter-description" type="search" bind:value={descriptionFilter} oninput={scheduleSearch} placeholder={$t("explore.descriptionPlaceholder")} />
    </label>
    <fieldset class="content-field source-filter">
      <legend>{$t("explore.importFiles")}</legend>
      <span class="palette-hint">{$t("explore.importFilesHint")}</span>
      <label class="source-option">
        <input type="checkbox" bind:checked={manualSelected} onchange={() => search()} />
        <span>{$t("explore.createdByHand")}</span>
      </label>
      {#each sources as source (source)}
        <label class="source-option" title={source}>
          <input type="checkbox" checked={selectedSources.includes(source)} onchange={(event) => toggleSource(source, event.target.checked)} />
          <span>{source}</span>
        </label>
      {/each}
    </fieldset>
    <button class="close-document-button" type="button" disabled={!hasFilters} onclick={resetFilters}>{$t("explore.resetFilters")}</button>
  </aside>
  <SidebarResizer bind:width={sidebarWidth} min={220} max={520} storageKey="content-explore" label={$t("explore.resizeFilters")} />

  <section class="content-sheet-area explore-results" aria-label={$t("palette.title")} aria-busy={isLoading}>
    <div class="explore-summary" role="status">
      {#if isLoading && !items.length}
        {$t("explore.searching")}
      {:else}
        {hasFilters ? $t("explore.countFiltered", { count: total }) : $t("explore.count", { count: total })}
      {/if}
    </div>
    {#if errorMessage}<p class="compile-error" role="alert">{errorMessage}</p>{/if}

    {#if !isLoading && !errorMessage && !items.length}
      <p class="explore-empty">{hasFilters ? $t("explore.noMatch") : $t("explore.empty")}</p>
    {/if}

    <ul class="explore-list">
      {#each visibleItems as block (block.id)}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
        <li class="explore-card" class:pickable={pickMode} class:picked={pickedIds.has(block.id)} onclick={(event) => handleCardClick(event, block)}>
          <header class="explore-card-header">
            {#if pickMode}
              <label class="explore-card-pick">
                <input type="checkbox" checked={pickedIds.has(block.id)} onchange={() => togglePick(block)} />
                <span class="explore-card-title">{block.title || $t("explore.untitled")}</span>
                {#if pickedIds.has(block.id)}<span class="pick-order">{pickedBlocks.findIndex((picked) => picked.id === block.id) + 1}</span>{/if}
              </label>
            {:else}
              <h3>{block.title || $t("explore.untitled")}</h3>
            {/if}
            <div class="explore-card-id">
              <span>ID</span>
              <code>{block.id}</code>
              <button class="icon-button" type="button" title={$t("explore.copyId")} aria-label={$t("explore.copyIdOf", { title: block.title })} onclick={() => copyId(block.id)}>
                {copiedId === block.id ? "✓" : "⧉"}
              </button>
            </div>
            {#if !pickMode}
              <div class="explore-card-actions">
                <button class="secondary-button" type="button" onclick={() => navigate(`/content/edit/${block.id}`)}>{$t("common.edit")}</button>
                <button class="remove-content-button" type="button" disabled={deletingId === block.id} onclick={() => deleteBlock(block)}>
                  {deletingId === block.id ? $t("explore.deleting") : $t("common.delete")}
                </button>
              </div>
            {/if}
            {#if block.description}<p class="explore-card-description">{block.description}</p>{/if}
            <p class="explore-card-meta">
              {block.source ? $t("import.description", { file: block.source }) : $t("explore.createdByHandSingle")} · {$t("explore.elements", { count: block.contents.length })} · {$t("explore.modifiedOn", { date: formatDate(block.updated_at) })}
            </p>
          </header>
          <div class="import-group-preview explore-card-preview" tabindex="0" role="region" aria-label={$t("explore.contentsOf", { title: block.title })}>
            {#if block.contents.length}
              <ContentSheet contents={block.contents} readonly compact />
            {:else}
              <p class="explore-empty">{$t("explore.noElements")}</p>
            {/if}
          </div>
        </li>
      {/each}
    </ul>

    {#if items.length < total}
      <button class="secondary-button explore-more" type="button" disabled={isLoading} onclick={() => search(true)}>
        {isLoading ? $t("explore.loading") : $t("explore.showMore", { count: total - items.length })}
      </button>
    {/if}
  </section>
</div>

{#if pickMode}
  <!-- Fixed buttons at the bottom right, above everything: they do not depend on the page layout. -->
  <div class="picker-actions">
    <button class="picker-cancel" type="button" onclick={onCancel}>{$t("common.cancel")}</button>
    <button class="picker-add" type="button" disabled={!pickedBlocks.length} onclick={() => onPick(pickedBlocks)}>
      {$t("explore.add")}{pickedBlocks.length ? ` (${pickedBlocks.length})` : ""}
    </button>
  </div>
{/if}
