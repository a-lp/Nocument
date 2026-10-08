<script>
  import { confirmAction } from "../../confirm.js";
  import BackButton from "../../components/BackButton.svelte";
  import { onMount } from "svelte";
  import { apiFetch } from "../../api.js";
  import { language, t } from "../../i18n.js";
  import ContentModal from "../../components/builder/ContentModal.svelte";
  import ContentSheet from "../../components/content/ContentSheet.svelte";
  import ImportContentsModal from "../../components/content/ImportContentsModal.svelte";
  import SidebarResizer from "../../components/SidebarResizer.svelte";
  import ExploreContents from "./ExploreContents.svelte";
  import ContentPalette from "../../components/content/ContentPalette.svelte";
  import { SAVED_CONTENT } from "../../components/content/dragTypes.js";

  // Creation and editing of a ContentBlock: name, description and contents (headings, paragraphs, images, tables)
  // laid out on an A4 sheet, created by hand or imported from a Word document, and saved with /api/content-blocks.
  // blockId: saved block to open (page /content/edit/<id>), null for a new block.
  export let blockId = null;
  export let navigate = null;

  // Width (px) of the sidebar, resizable.
  let sidebarWidth = 300;
  let title = "";
  let description = "";
  // Word file the content open in the sheet comes from (null if created by hand).
  let source = null;
  // Contents in the JSON format of the ContentBlocks, each with its hexadecimal "id".
  let contents = [];
  // Styles offered in the form: those of the default template, or of the imported Word document.
  let styles = null;
  let stylesError = "";
  // An open or already saved block is updated (PUT) with its ID (blockId), a new one is created (POST).
  let isLoadingBlock = Boolean(blockId);
  let loadError = "";
  let isDirty = false;
  let isSaving = false;
  let saveMessage = "";
  let saveError = "";
  let importInput;
  let isImporting = false;
  let importMessages = [];
  let importError = "";
  // Imported document waiting for the choice of the contents: { fileName, title, groups, styles, warnings }.
  let pendingImport = null;
  let isSavingImport = false;
  let importSaveError = "";
  // Open form: { index, type } for a new content, { index, editing: true } for an edit.
  let modal = null;
  // Choice of the saved blocks to add at position index: { index } while it is open, otherwise null.
  let picker = null;
  let pickMessage = "";

  onMount(async () => {
    if (blockId) {
      loadBlock();
    }
    try {
      const response = await apiFetch("/api/content-blocks/styles");
      if (!response.ok) {
        throw new Error();
      }
      styles = await response.json();
    } catch {
      stylesError = $t("addContent.stylesError");
    }
  });

  // Opens the saved block given by blockId.
  async function loadBlock() {
    try {
      const response = await apiFetch(`/api/content-blocks/${blockId}`);
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(response.status === 404 ? $t("addContent.notFound") : data?.error || $t("addContent.openError"));
      }
      title = data.title;
      description = data.description;
      source = data.source;
      contents = data.contents;
    } catch (error) {
      loadError = error.message;
    } finally {
      isLoadingBlock = false;
    }
  }

  // New 32-digit hexadecimal ID (like the backend ones); getRandomValues also works outside HTTPS.
  function newContentId() {
    return Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  // Marks that there are unsaved changes.
  function markDirty() {
    isDirty = true;
    saveMessage = "";
  }

  // Opens the form for a new content at position index (type null = chosen in the form), or the choice among the
  // saved blocks for the "Saved content" type.
  function openInsert(index, type) {
    if (type === SAVED_CONTENT) {
      picker = { index };
    } else if (styles) {
      modal = { index, type: type ?? "heading" };
    }
  }

  // From the form ("Saved content" tab) goes to the choice among the saved blocks, at the same position.
  function switchToPicker() {
    picker = { index: modal.index };
    modal = null;
  }

  // Copies the elements of the chosen blocks to the insertion position, with new IDs (the blocks stay unchanged).
  function insertSavedBlocks(blocks) {
    const copies = blocks.flatMap((block) => block.contents.map((content) => ({ ...content, id: newContentId() })));
    contents = [...contents.slice(0, picker.index), ...copies, ...contents.slice(picker.index)];
    pickMessage = $t("addContent.picked", { count: copies.length, blocks: blocks.map((block) => block.title || block.id).join(", ") });
    picker = null;
    markDirty();
  }

  // Opens the edit form of the content at position index.
  function openEdit(index) {
    if (styles) {
      modal = { index, editing: true };
    }
  }

  // Suggested level for a new heading: right below a heading the next level, otherwise the last heading's one.
  function suggestedLevel(index) {
    const previous = contents.slice(0, index).reverse();
    const lastHeading = previous.find((content) => content.type === "heading");
    if (!lastHeading) {
      return 1;
    }
    return previous[0] === lastHeading ? Math.min(9, lastHeading.level + 1) : lastHeading.level;
  }

  // Saves the form content: replaces the edited one (keeping its ID) or inserts it at the chosen position.
  function submitContent(content) {
    if (modal.editing) {
      contents = contents.map((item, index) => (index === modal.index ? { ...content, id: item.id } : item));
    } else {
      contents = [...contents.slice(0, modal.index), { ...content, id: newContentId() }, ...contents.slice(modal.index)];
    }
    modal = null;
    markDirty();
  }

  // Deletes the content at position index, after confirmation.
  async function deleteContent(index) {
    if (!(await confirmAction($t("addContent.confirmDelete"), { title: $t("confirm.titles.deleteFromSheet"), action: $t("confirm.actions.delete"), danger: true }))) {
      return;
    }
    contents = contents.filter((_, position) => position !== index);
    modal = null;
    markDirty();
  }

  // Moves the content from from to the insertion position to (computed before the removal).
  function moveContent(from, to) {
    const target = to > from ? to - 1 : to;
    if (target === from) {
      return;
    }
    const moved = [...contents];
    const [content] = moved.splice(from, 1);
    moved.splice(target, 0, content);
    contents = moved;
    markDirty();
  }

  // Extracts the contents of a Word document, grouped by heading, and opens the modal to choose which to import.
  async function importDocument(event) {
    const [file] = event.target.files;
    event.target.value = "";
    if (!file) {
      return;
    }
    isImporting = true;
    importError = "";
    importMessages = [];
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await apiFetch("/api/content-blocks/import", { method: "POST", body: formData });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("addContent.importError"));
      }
      if (!data.groups.length) {
        throw new Error($t("addContent.nothingToImport"));
      }
      importSaveError = "";
      pendingImport = { fileName: file.name, ...data };
    } catch (error) {
      importError = error.message;
    } finally {
      isImporting = false;
    }
  }

  // Saves each chosen group as a separate block; those already saved are not repeated after an error.
  async function saveImportedBlocks(blocks) {
    isSavingImport = true;
    importSaveError = "";
    const saved = [];
    try {
      for (const block of blocks) {
        const response = await apiFetch("/api/content-blocks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(block)
        });
        const data = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(`"${block.title}": ${data?.error || $t("addContent.saveError")}`);
        }
        saved.push(data.title);
      }
      importMessages = [$t("addContent.imported", { count: saved.length, file: pendingImport.fileName, titles: saved.join(", ") }), ...pendingImport.warnings];
      pendingImport = null;
    } catch (error) {
      const done = saved.length ? ` ${$t("addContent.alreadyImported", { titles: saved.join(", ") })}` : "";
      importSaveError = `${error.message}${done}`;
    } finally {
      isSavingImport = false;
    }
  }

  // Opens the only chosen group in the sheet, with the document styles, to edit it before saving it.
  async function openImportedBlock(block) {
    if ((isDirty || contents.length) && !(await confirmAction($t("addContent.confirmReplace"), { title: $t("confirm.titles.replaceSheet"), action: $t("confirm.actions.replace"), danger: true }))) {
      return;
    }
    title = block.title;
    description = block.description;
    source = block.source;
    contents = block.contents;
    styles = pendingImport.styles;
    blockId = null;
    importMessages = pendingImport.warnings;
    pendingImport = null;
    markDirty();
  }

  // Saves the block: creates it at the first save, then updates it.
  async function save() {
    saveError = "";
    saveMessage = "";
    if (!title.trim()) {
      saveError = $t("addContent.nameRequired");
      return;
    }
    isSaving = true;
    try {
      const response = await apiFetch(blockId ? `/api/content-blocks/${blockId}` : "/api/content-blocks", {
        method: blockId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim(), description: description.trim(), source, contents })
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("addContent.saveError"));
      }
      blockId = data.id;
      contents = data.contents;
      isDirty = false;
      saveMessage = $t("addContent.savedAt", { time: new Date().toLocaleTimeString($language, { hour: "2-digit", minute: "2-digit" }) });
    } catch (error) {
      saveError = error.message;
    } finally {
      isSaving = false;
    }
  }

  // Starts again with an empty content (asks for confirmation if there are unsaved changes).
  async function startNew() {
    if (isDirty && !(await confirmAction($t("addContent.confirmDiscard"), { title: $t("confirm.titles.discardChanges"), action: $t("confirm.actions.discard"), danger: true }))) {
      return;
    }
    // From an open block it goes to the page of a new block, which starts from scratch.
    if (navigate && window.location.pathname !== "/content/new") {
      navigate("/content/new");
      return;
    }
    title = "";
    description = "";
    source = null;
    contents = [];
    blockId = null;
    isDirty = false;
    saveMessage = "";
    saveError = "";
    importMessages = [];
    importError = "";
  }
</script>

<div class="content-page" style={`--sidebar-width: ${sidebarWidth}px`}>
  <aside class="context-sidebar content-sidebar" aria-label={$t("addContent.sidebarLabel")}>
    <div class="context-sidebar-heading">
      <div class="sidebar-title">
        <BackButton onDark />
        <div>
          <p>{$t("nav.content")}</p>
          <h2>{blockId ? $t("addContent.editTitle") : $t("addContent.newTitle")}</h2>
        </div>
      </div>
      <button class="close-document-button" type="button" disabled={isSaving} onclick={startNew}>{$t("addContent.new")}</button>
    </div>

    <label class="content-field" for="content-title">
      {$t("addContent.name")}
      <input id="content-title" type="text" bind:value={title} oninput={markDirty} placeholder={$t("addContent.namePlaceholder")} />
    </label>
    <label class="content-field" for="content-description">
      {$t("addContent.description")}
      <textarea id="content-description" rows="3" bind:value={description} oninput={markDirty} placeholder={$t("addContent.descriptionPlaceholder")}></textarea>
    </label>

    <ContentPalette
      hint={$t("addContent.paletteHint")}
      disabled={!styles}
      onSelect={(type) => openInsert(contents.length, type)}
    />
    {#if stylesError}<p class="compile-error" role="alert">{stylesError}</p>{/if}

    <div class="content-sidebar-actions">
      <input bind:this={importInput} type="file" accept=".docx,.dotx" onchange={importDocument} hidden />
      <button class="secondary-button content-import-button" type="button" disabled={isImporting || isSaving} onclick={() => importInput?.click()}>
        {isImporting ? $t("import.importing") : $t("addContent.importFromWord")}
      </button>
      {#each importMessages as message}<p class="content-status">{message}</p>{/each}
      {#if pickMessage}<p class="content-status">{pickMessage}</p>{/if}
      {#if importError}<p class="compile-error" role="alert">{importError}</p>{/if}
      <button class="compile-button" type="button" disabled={isSaving || isLoadingBlock || Boolean(loadError)} onclick={save}>
        {isSaving ? $t("common.saving") : blockId ? $t("contentModal.saveChanges") : $t("addContent.save")}
      </button>
      {#if saveError}<p class="compile-error" role="alert">{saveError}</p>{/if}
      {#if saveMessage}<p class="content-status" role="status">{saveMessage}</p>{/if}
      {#if isDirty && blockId}<p class="content-status">{$t("addContent.unsaved")}</p>{/if}
    </div>
  </aside>
  <SidebarResizer bind:width={sidebarWidth} min={220} max={520} storageKey="content-editor" />

  <section class="content-sheet-area" aria-label={$t("sheet.label")}>
    {#if isLoadingBlock}
      <p class="explore-summary" role="status">{$t("addContent.opening")}</p>
    {:else if loadError}
      <div class="explore-empty">
        <p class="compile-error" role="alert">{loadError}</p>
        {#if navigate}<button class="secondary-button" type="button" onclick={() => navigate("/content/explore")}>{$t("addContent.backToExplore")}</button>{/if}
      </div>
    {:else}
      <ContentSheet
        {contents}
        disabled={!styles || isSaving}
        onInsert={openInsert}
        onMove={moveContent}
        onEdit={openEdit}
        onDelete={deleteContent}
      />
    {/if}
  </section>
</div>

{#if picker}
  <!-- Full screen choice with the Explore contents page: the sheet stays as it is underneath, without changing page. -->
  <div class="picker-overlay" role="dialog" aria-modal="true" aria-label={$t("addContent.pickLabel")}>
    <ExploreContents pickMode excludeId={blockId} onPick={insertSavedBlocks} onCancel={() => (picker = null)} />
  </div>
{/if}

{#if pendingImport}
  <ImportContentsModal
    fileName={pendingImport.fileName}
    documentTitle={pendingImport.title}
    groups={pendingImport.groups}
    warnings={pendingImport.warnings}
    isSaving={isSavingImport}
    errorMessage={importSaveError}
    onImport={saveImportedBlocks}
    onOpen={openImportedBlock}
    onClose={() => (pendingImport = null)}
  />
{/if}

{#if modal && styles}
  <!-- key: every opening recreates the form with the values of the chosen content. -->
  {#key modal}
    <ContentModal
      {styles}
      context="block"
      initial={modal.editing ? contents[modal.index] : null}
      initialType={modal.type ?? "heading"}
      suggestedLevel={suggestedLevel(modal.index)}
      onSubmit={submitContent}
      onPickSaved={modal.editing ? null : switchToPicker}
      onDelete={() => deleteContent(modal.index)}
      onClose={() => (modal = null)}
    />
  {/key}
{/if}
