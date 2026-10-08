<script>
  import { confirmAction } from "../../confirm.js";
  import BackButton from "../../components/BackButton.svelte";
  import { onDestroy, onMount } from "svelte";
  import { apiFetch } from "../../api.js";
  import { t } from "../../i18n.js";
  import { loadSession } from "../../sessionStore.js";
  import { openTemplateInBuilder, saveTemplate } from "../../templates.js";
  import SidebarResizer from "../../components/SidebarResizer.svelte";
  import TemplateModal from "../../components/templates/TemplateModal.svelte";

  // Saved document templates, with the same layout as Explore contents: search and filters in the sidebar, the
  // templates as a grid of cards (name and description) with the button creating a new document from the template
  // in the Builder. Templates are imported here (Import template) or saved from a document of the Builder.
  export let navigate;

  const PAGE_SIZE = 24;
  // Wait after the last key before searching, so there is no request at every letter.
  const SEARCH_DELAY_MS = 300;
  const ORIGINS = ["builder", "import"];

  let sidebarWidth = 300;
  let searchText = "";
  // Chosen origins; with no choice all the templates are shown.
  let selectedOrigins = [];
  let items = [];
  let total = 0;
  let isLoading = false;
  let errorMessage = "";
  let deletingId = "";
  let isImporting = false;
  // Confirmation of the last import, "" otherwise.
  let notice = "";
  let searchTimer;
  let noticeTimer;
  // Identifies the last search: answers of earlier searches arriving later are ignored.
  let requestToken = 0;

  $: hasFilters = Boolean(searchText.trim() || selectedOrigins.length);

  onMount(() => search());

  onDestroy(() => {
    clearTimeout(searchTimer);
    clearTimeout(noticeTimer);
  });

  function queryParams(skip) {
    const params = new URLSearchParams({ skip: String(skip), limit: String(PAGE_SIZE) });
    if (searchText.trim()) {
      params.set("search", searchText.trim());
    }
    for (const origin of selectedOrigins) {
      params.append("origin", origin);
    }
    return params;
  }

  // Searches the templates with the current filters; with append it adds the next page to those already shown.
  async function search(append = false) {
    clearTimeout(searchTimer);
    const token = ++requestToken;
    isLoading = true;
    errorMessage = "";
    try {
      const response = await apiFetch(`/api/templates?${queryParams(append ? items.length : 0)}`);
      const data = await response.json().catch(() => null);
      if (token !== requestToken) {
        return;
      }
      if (!response.ok) {
        throw new Error(data?.error || $t("templates.loadError"));
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

  function scheduleSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => search(), SEARCH_DELAY_MS);
  }

  function toggleOrigin(origin, checked) {
    selectedOrigins = checked ? [...selectedOrigins, origin] : selectedOrigins.filter((item) => item !== origin);
    search();
  }

  function resetFilters() {
    searchText = "";
    selectedOrigins = [];
    search();
  }

  // Opens the template in the Builder: with edit to edit the template itself, otherwise as a new document created
  // from it. The document open there (kept in its session) is replaced, after confirmation.
  async function openInBuilder(template, edit = false) {
    let session = null;
    try {
      session = await loadSession("builder");
    } catch {
      // Without the session nothing is replaced.
    }
    if (session?.file && !(await confirmAction($t(edit ? "templates.confirmReplaceEdit" : "templates.confirmReplace", { name: session.fileName }), { title: $t("confirm.titles.replaceDocument"), action: $t("confirm.actions.replace") }))) {
      return;
    }
    openTemplateInBuilder(template, { edit });
    navigate("/documents/builder");
  }

  async function deleteTemplate(template) {
    if (!(await confirmAction($t("templates.confirmDelete", { name: template.name }), { title: $t("confirm.titles.deleteTemplate"), action: $t("confirm.actions.delete"), danger: true }))) {
      return;
    }
    deletingId = template.id;
    errorMessage = "";
    try {
      const response = await apiFetch(`/api/templates/${template.id}`, { method: "DELETE" });
      // 404: it was already deleted (e.g. from another tab), so it is removed from the list anyway.
      if (!response.ok && response.status !== 404) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.error || $t("templates.deleteError"));
      }
      items = items.filter((item) => item.id !== template.id);
      total = Math.max(0, total - 1);
    } catch (error) {
      errorMessage = error.message;
    } finally {
      deletingId = "";
    }
  }

  async function importTemplate({ name, description, version, file }) {
    await saveTemplate({ file, fileName: file.name, name, description, version, origin: "import" });
    isImporting = false;
    showNotice($t("templates.imported", { name }));
    search();
  }

  function showNotice(message) {
    notice = message;
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => (notice = ""), 4000);
  }

  // Version and origin, shown as the tooltip of the card.
  function details(template) {
    const origin = $t(`templates.origins.${template.origin}`);
    return template.version ? $t("templates.versionAndOrigin", { version: template.version, origin }) : origin;
  }
</script>

<div class="content-page" style={`--sidebar-width: ${sidebarWidth}px`}>
  <aside class="context-sidebar content-sidebar" aria-label={$t("templates.filtersLabel")}>
    <div class="sidebar-title">
      <BackButton onDark />
      <div>
        <p>{$t("nav.documents")}</p>
        <h2>{$t("nav.templates")}</h2>
      </div>
    </div>

    <button class="template-import-button" type="button" onclick={() => (isImporting = true)}>+ {$t("templates.import")}</button>

    <label class="content-field" for="template-search">
      {$t("templates.search")}
      <input id="template-search" type="search" bind:value={searchText} oninput={scheduleSearch} placeholder={$t("templates.searchPlaceholder")} />
    </label>
    <fieldset class="content-field source-filter">
      <legend>{$t("templates.origin")}</legend>
      <span class="palette-hint">{$t("templates.originHint")}</span>
      {#each ORIGINS as origin (origin)}
        <label class="source-option">
          <input type="checkbox" checked={selectedOrigins.includes(origin)} onchange={(event) => toggleOrigin(origin, event.target.checked)} />
          <span>{$t(`templates.origins.${origin}`)}</span>
        </label>
      {/each}
    </fieldset>
    <button class="close-document-button" type="button" disabled={!hasFilters} onclick={resetFilters}>{$t("templates.resetFilters")}</button>
  </aside>
  <SidebarResizer bind:width={sidebarWidth} min={220} max={520} storageKey="templates" label={$t("templates.resizeFilters")} />

  <section class="content-sheet-area explore-results templates-results" aria-label={$t("nav.templates")} aria-busy={isLoading}>
    <div class="explore-summary" role="status">
      {#if isLoading && !items.length}
        {$t("templates.searching")}
      {:else}
        {hasFilters ? $t("templates.countFiltered", { count: total }) : $t("templates.count", { count: total })}
      {/if}
    </div>
    {#if notice}<p class="settings-saved template-notice" role="status">{notice}</p>{/if}
    {#if errorMessage}<p class="compile-error" role="alert">{errorMessage}</p>{/if}

    {#if !isLoading && !errorMessage && !items.length}
      <p class="explore-empty">{hasFilters ? $t("templates.noMatch") : $t("templates.empty")}</p>
    {/if}

    <ul class="template-grid">
      {#each items as template (template.id)}
        <li class="template-card" title={details(template)}>
          <h3>{template.name}</h3>
          {#if template.description}<p>{template.description}</p>{/if}
          <div class="template-card-actions">
            <button type="button" aria-label={$t("templates.createFrom", { name: template.name })} onclick={() => openInBuilder(template)}>
              {$t("templates.create")}
            </button>
            <button class="secondary-button" type="button" aria-label={$t("templates.editLabel", { name: template.name })} onclick={() => openInBuilder(template, true)}>
              {$t("common.edit")}
            </button>
            <button
              class="icon-button template-card-delete"
              type="button"
              title={$t("common.delete")}
              aria-label={$t("templates.deleteLabel", { name: template.name })}
              disabled={deletingId === template.id}
              onclick={() => deleteTemplate(template)}
            >🗑</button>
          </div>
        </li>
      {/each}
    </ul>

    {#if items.length < total}
      <button class="secondary-button explore-more" type="button" disabled={isLoading} onclick={() => search(true)}>
        {isLoading ? $t("templates.loading") : $t("templates.showMore", { count: total - items.length })}
      </button>
    {/if}
  </section>
</div>

{#if isImporting}
  <TemplateModal
    title={$t("templates.modal.importTitle")}
    intro={$t("templates.modal.importIntro")}
    submitLabel={$t("templates.modal.importButton")}
    withFile
    onSubmit={importTemplate}
    onClose={() => (isImporting = false)}
  />
{/if}
