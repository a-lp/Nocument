<script>
  import { confirmAction } from "../../confirm.js";
  import BackButton from "../../components/BackButton.svelte";
  import { onDestroy, onMount, tick } from "svelte";
  import { apiFetch } from "../../api.js";
  import { t } from "../../i18n.js";
  import { clearSession, loadSession, saveSession } from "../../sessionStore.js";
  import FileDropZone from "../../components/FileDropZone.svelte";
  import FileTypeIcon from "../../components/FileTypeIcon.svelte";
  import NavIcon from "../../components/NavIcon.svelte";
  import SidebarResizer from "../../components/SidebarResizer.svelte";
  import ContentModal from "../../components/builder/ContentModal.svelte";
  import ContentPalette from "../../components/content/ContentPalette.svelte";
  import { SAVED_CONTENT } from "../../components/content/dragTypes.js";
  import ExploreContents from "../content/ExploreContents.svelte";
  import BuilderGraph from "../../components/builder/graph/BuilderGraph.svelte";
  import { descendantCount, inLayoutTable, itemKey } from "../../components/builder/graph/graphLayout.js";
  import TocPanel from "../../components/builder/TocPanel.svelte";
  import TemplateModal from "../../components/templates/TemplateModal.svelte";
  import { saveTemplate, takePendingTemplate, templateInfo, updateTemplate } from "../../templates.js";
  import { takeTransferredDocument, transferDocument } from "../../documentTransfer.js";

  // navigate: goes to another page of the web app (e.g. Templates, to start from a template).
  export let navigate = null;

  const DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  // Key of the Builder session in sessionStore.js: it only holds the last .docx returned by the backend.
  const SESSION_KEY = "builder";

  // Document being built: every change replaces it with the version returned by the backend, at once (changes only
  // edit the Word file, nothing slow happens).
  let documentName = "";
  let docxBlob = null;
  // Finished document, made only when it is asked for (Preview PDF, Save PDF, Save Word, Open in Compiler): the Word
  // file with its tables of contents updated by LibreOffice and, once asked, its PDF. Kept until the next change of
  // the document: { source (the docxBlob it comes from), docx, pdf (null until asked) }, or null.
  let finished = null;
  // Preparation of the finished document in progress: "pdf" (with the PDF) or "docx".
  let finishing = "";
  $: isRenderingPdf = Boolean(finishing);
  let structure = [];
  let styles = null;
  let isLoading = false;
  // Width (px) of the table of contents sidebar, resizable.
  let sidebarWidth = 280;
  let isRestoring = false;
  let errorMessage = "";
  // Key (itemKey) of the heading chosen in the table of contents.
  let activeHeadingId = null;
  let graph;
  // URL (blob) of the PDF shown in the preview; "" when the preview is closed.
  let previewUrl = "";
  // Open modal: { after, suggestedLevel, type } for an insertion, { item } for an edit; otherwise null.
  let insertion = null;
  // Choice of the saved contents to insert after block after: { after } while it is open, otherwise null.
  let picker = null;
  // Warnings of the last change of the document (e.g. styles replaced in a saved content).
  let notices = [];
  // Elements selected for multiple deletion (itemKey keys).
  let selectedKeys = new Set();

  $: selectedItems = blocks.map(({ item }) => item).filter((item) => selectedKeys.has(itemKey(item)));
  let editing = null;
  // Document change request in progress (insertion, edit or deletion).
  let isSaving = false;
  let modalError = "";
  // Error of an action started from the graph (without modal).
  let actionError = "";
  // Modal saving the document as a template.
  let isSavingTemplate = false;
  // Template being edited ({ id, name, description, version }, kept in the session): Save template updates it.
  // null for an ordinary document.
  let editedTemplate = null;
  // Confirmation of the last saved template, "" otherwise.
  let templateNotice = "";
  let templateNoticeTimer;

  // Structure blocks in document order, with depth and level of the section containing them.
  $: blocks = flattenStructure(structure);
  // Table of contents entries: only headings with text, with the ids of the headings containing them (to collapse them).
  $: tocEntries = buildTocEntries(structure);

  // Flattens the structure tree keeping the depth of each element.
  function flattenStructure(items, depth = 0, sectionLevel = 0, output = []) {
    for (const item of items) {
      output.push({ item, depth, sectionLevel });
      if (item.type === "heading") {
        flattenStructure(item.children, depth + 1, item.level, output);
      }
    }
    return output;
  }

  // Extracts the headings from the structure tree for the table of contents.
  function buildTocEntries(items, parentIds = [], output = []) {
    for (const item of items) {
      if (item.type !== "heading") {
        continue;
      }
      const hasText = Boolean(item.text.trim());
      // Key and not id: the headings of a layout table share the table's id.
      const key = itemKey(item);
      if (hasText) {
        output.push({
          id: key,
          text: item.text.trim(),
          depth: parentIds.length,
          parentIds,
          hasChildren: item.children.some((child) => child.type === "heading" && child.text.trim())
        });
      }
      // The children of a heading without text stay at the heading's level.
      buildTocEntries(item.children, hasText ? [...parentIds, key] : parentIds, output);
    }
    return output;
  }

  // Opens the chosen document or template in the Builder; returns true if it was opened. template: the template
  // being edited, when the file is its document restored from the session.
  function openFile(file, template = null) {
    const formData = new FormData();
    formData.append("file", file);
    return openWith(() => apiFetch("/api/builder/open", { method: "POST", body: formData }), template);
  }

  // Creates an empty document (default Word template).
  function createEmptyDocument() {
    return openWith(() => apiFetch("/api/builder/new", { method: "POST" }));
  }

  // Opens a saved template: with edit to edit the template itself, otherwise as a new document created from it.
  function openTemplate(template, edit) {
    return openWith(
      () => apiFetch(`/api/builder/template/${encodeURIComponent(template.id)}`, { method: "POST" }),
      edit ? templateInfo(template) : null
    );
  }

  // Opens the document returned by request (a call to a Builder route); returns true if it was opened.
  // template: the template the document is the editing of, null for an ordinary document.
  async function openWith(request, template = null) {
    errorMessage = "";
    isLoading = true;
    try {
      const response = await request();
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("builder.openError"));
      }
      editedTemplate = template;
      applyResponse(data);
      return true;
    } catch (error) {
      errorMessage = error.message;
      return false;
    } finally {
      isLoading = false;
    }
  }

  // When the page loads it reopens the last document of the session: the backend regenerates its structure,
  // styles, table of contents and PDF, as for a document just uploaded. Coming from the Templates page, it creates
  // the document from the chosen template instead (which then replaces the session).
  onMount(async () => {
    const pending = takePendingTemplate();
    if (pending) {
      await openTemplate(pending.template, pending.edit);
      return;
    }
    // Document sent from the Compiler (Open in Builder).
    const transferred = takeTransferredDocument("builder");
    if (transferred) {
      await openFile(transferred);
      return;
    }
    let session;
    try {
      session = await loadSession(SESSION_KEY);
    } catch (error) {
      console.warn("Cannot read the Builder session", error);
    }
    if (!session?.file) {
      return;
    }
    isRestoring = true;
    // IndexedDB can return a Blob without name: the File is recreated with the original name.
    const restored = await openFile(new File([session.file], session.fileName, { type: DOCX_MIME_TYPE }), session.template ?? null);
    isRestoring = false;
    if (!restored) {
      // A session that cannot be reopened would fail at every reload: it is deleted.
      errorMessage = $t("builder.restoreError", { error: errorMessage });
      await clearSession(SESSION_KEY).catch(() => {});
    }
  });

  onDestroy(() => clearTimeout(templateNoticeTimer));

  // Saves the last document returned by the backend in the session.
  async function saveBuilderSession() {
    try {
      await saveSession(SESSION_KEY, { file: docxBlob, fileName: documentName, template: editedTemplate });
    } catch (error) {
      // E.g. private browsing or no space left: the Builder still works, without session.
      console.warn("Cannot save the Builder session", error);
    }
  }

  // Updates document, structure and styles with the backend response; the PDF of the previous version is dropped.
  function applyResponse(data) {
    documentName = data.name;
    docxBlob = base64ToBlob(data.docx, DOCX_MIME_TYPE);
    finished = null;
    structure = data.structure;
    styles = data.styles;
    notices = data.warnings ?? [];
    // After a change the block ids change: the selection is no longer valid either.
    activeHeadingId = null;
    selectedKeys = new Set();
    saveBuilderSession();
  }

  // Opens the insertion modal after the element with anchor after (null = beginning of the document), with the
  // content type preselected; the "Saved content" type opens the choice among the saved blocks instead.
  function openInsertion(after, suggestedLevel, type = "heading") {
    modalError = "";
    actionError = "";
    editing = null;
    if (type === SAVED_CONTENT) {
      picker = { after };
    } else {
      insertion = { after, suggestedLevel, type };
    }
  }

  // Insertion at the end of the document (click on a type in the sidebar): after the last block of the structure.
  function insertAtEnd(type) {
    const last = blocks[blocks.length - 1];
    const level = !last ? 1 : last.item.type === "heading" ? Math.min(9, last.item.level + 1) : Math.max(1, last.sectionLevel);
    openInsertion(last?.item.anchor ?? null, level, type);
  }

  // From the form ("Saved content" tab) goes to the choice among the saved blocks, at the same position.
  function switchToPicker() {
    picker = { after: insertion.after };
    closeModal();
  }

  // Inserts the elements of the chosen blocks in the document, in order, at the chosen spot.
  async function insertSavedBlocks(chosen) {
    const { after } = picker;
    picker = null;
    actionError = await editDocument("insert", { after, contents: chosen.flatMap((block) => block.contents) });
  }

  // Opens the edit modal of a structure element.
  function openEditing(item) {
    modalError = "";
    actionError = "";
    insertion = null;
    editing = { item };
  }

  // Closes the insertion or edit modal.
  function closeModal() {
    insertion = null;
    editing = null;
  }

  // Sends a document change to the backend (path: insert, update, move or delete) and shows the updated document.
  // Returns the error message, or "" if it succeeded.
  async function editDocument(path, body) {
    isSaving = true;
    try {
      const response = await apiFetch(`/api/builder/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file: { name: documentName, content: await blobToBase64(docxBlob) }, ...body })
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("errors.updateFailed"));
      }
      applyResponse(data);
      return "";
    } catch (error) {
      return error.message;
    } finally {
      isSaving = false;
    }
  }

  // Saves the modal content: insertion at the chosen spot or replacement of the edited element.
  async function submitContent(content) {
    modalError = insertion
      ? await editDocument("insert", { after: insertion.after, content })
      : await editDocument("update", { target: targetOf(editing.item), content });
    if (!modalError) {
      closeModal();
    }
  }

  // Deletes an element after confirmation; from the edit modal the error appears in the modal.
  async function deleteItem(item) {
    if (!(await confirmAction(deleteConfirmation(item), { title: $t("confirm.titles.deleteFromDocument"), action: $t("confirm.actions.delete"), danger: true }))) {
      return;
    }
    const error = await editDocument("delete", { target: targetOf(item) });
    if (editing) {
      modalError = error;
      if (!error) {
        closeModal();
      }
    } else {
      actionError = error;
    }
  }

  // Moves the element after block after, with the blocks moving with it (range, see moveRange in graphLayout.js: a
  // heading with its whole section, a content with the contents that follow it up to the next heading): drag from a
  // graph node to another, whose incoming link is replaced. When more than one element moves (or a layout table) it
  // asks for confirmation.
  async function moveItem(item, range, after) {
    const count = descendantCount(item);
    if (inLayoutTable(item)) {
      if (!(await confirmAction(count ? $t("builder.confirmMoveLayoutSection", { heading: item.text }) : $t("builder.confirmMoveLayout"), { title: $t("confirm.titles.moveElements"), action: $t("confirm.actions.move") }))) {
        return;
      }
    } else if (item.type === "heading") {
      if (count && !(await confirmAction($t("builder.confirmMoveSection", { heading: item.text, count }), { title: $t("confirm.titles.moveElements"), action: $t("confirm.actions.move") }))) {
        return;
      }
    } else if (range.count > 1 && !(await confirmAction($t("builder.confirmMoveChain", { count: range.count - 1 }), { title: $t("confirm.titles.moveElements"), action: $t("confirm.actions.move") }))) {
      return;
    }
    actionError = await editDocument("move", { target: { id: range.id, anchor: range.anchor }, after });
  }

  // Selects or deselects a structure element.
  function toggleSelect(item) {
    const key = itemKey(item);
    selectedKeys = new Set(selectedKeys);
    if (selectedKeys.has(key)) {
      selectedKeys.delete(key);
    } else {
      selectedKeys.add(key);
    }
  }

  // Selects all the structure elements, or none.
  function selectAll(selected) {
    selectedKeys = new Set(selected ? blocks.map(({ item }) => itemKey(item)) : []);
  }

  // Deletes the selected elements together, after confirmation.
  async function deleteSelected() {
    const count = selectedItems.length;
    const headings = selectedItems.filter((item) => item.type === "heading").length;
    const message = $t("builder.confirmDeleteSelected", { count }) + (headings ? ` ${$t("builder.deletedHeadingsNote")}` : "");
    if (!(await confirmAction(message, { title: $t("confirm.titles.deleteFromDocument"), action: $t("confirm.actions.delete"), danger: true }))) {
      return;
    }
    actionError = await editDocument("delete", { targets: selectedItems.map(targetOf) });
  }

  // Document blocks taken by the element (see SectionAnalyzer); for an element of a layout table also its position
  // in the table, so only that element is edited or deleted.
  function targetOf(item) {
    return { id: item.id, anchor: item.anchor, layout: item.layout ?? null };
  }

  // Confirmation message of the deletion, explaining what happens to the rest of the document.
  function deleteConfirmation(item) {
    if (item.type === "heading") {
      return $t("builder.confirmDeleteHeading", { heading: item.text });
    }
    if (item.type === "table") {
      return item.caption ? $t("builder.confirmDeleteTableCaption") : $t("builder.confirmDeleteTable");
    }
    if (item.type === "image" || item.has_image) {
      return $t("builder.confirmDeleteParagraphImages");
    }
    return $t("builder.confirmDeleteParagraph");
  }

  // Goes to the heading in the graph, expanding the sections containing it.
  async function goToHeading(id) {
    activeHeadingId = id;
    await tick();
    graph?.focusHeading(id);
  }

  // Finished version of the current document (see finished): the one already made or, otherwise, a new one asked
  // to the backend (/api/builder/export), with the PDF if withPdf. Returns null if it failed (error in actionError).
  async function finishedDocument(withPdf) {
    const source = docxBlob;
    if (finished?.source === source && (finished.pdf || !withPdf)) {
      return finished;
    }
    finishing = withPdf ? "pdf" : "docx";
    actionError = "";
    try {
      const response = await apiFetch("/api/builder/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file: { name: documentName, content: await blobToBase64(source) }, pdf: withPdf })
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("errors.builderPdfConversion"));
      }
      const result = {
        source,
        docx: base64ToBlob(data.docx, DOCX_MIME_TYPE),
        pdf: data.pdf ? base64ToBlob(data.pdf, "application/pdf") : null
      };
      // Kept only if the document has not changed (or been closed) in the meantime.
      if (docxBlob === source) {
        finished = result;
      }
      return result;
    } catch (error) {
      actionError = error.message;
      return null;
    } finally {
      finishing = "";
    }
  }

  // Downloads the PDF of the current document, making it if needed.
  async function savePdf() {
    const result = await finishedDocument(true);
    if (result) {
      download(result.pdf, documentName.replace(/\.docx$/i, ".pdf"));
    }
  }

  // Downloads the Word file of the current document, with its tables of contents updated.
  async function saveWord() {
    const result = await finishedDocument(false);
    if (result) {
      download(result.docx, documentName);
    }
  }

  // Opens the preview of the PDF of the current document, with the browser's PDF viewer, making it if needed.
  async function openPreview() {
    const result = await finishedDocument(true);
    if (result) {
      previewUrl = URL.createObjectURL(result.pdf);
    }
  }

  function closePreview() {
    URL.revokeObjectURL(previewUrl);
    previewUrl = "";
  }

  function handleWindowKeydown(event) {
    if (previewUrl && event.key === "Escape") {
      closePreview();
    }
  }

  // Closes the document (after confirmation), clears the session and goes back to the upload screen.
  async function closeDocument() {
    if (!(await confirmAction($t("builder.confirmClose"), { title: $t("confirm.titles.closeDocument"), action: $t("confirm.actions.close"), danger: true }))) {
      return;
    }
    clearSession(SESSION_KEY).catch((error) => console.warn("Cannot clear the Builder session", error));
    editedTemplate = null;
    documentName = "";
    docxBlob = null;
    finished = null;
    structure = [];
    styles = null;
    activeHeadingId = null;
    closeModal();
    if (previewUrl) {
      closePreview();
    }
  }

  // Saves the current document as a new template, with the information given in the modal. While editing a
  // template, the Builder then goes on editing the new one.
  async function saveAsTemplate({ name, description, version }) {
    const saved = await saveTemplate({ file: docxBlob, fileName: documentName, name, description, version, origin: "builder" });
    if (editedTemplate) {
      editedTemplate = templateInfo(saved);
      saveBuilderSession();
    }
    templateSaved($t("builder.templateSaved", { name }));
  }

  // Saves the changes of the template being edited: its information and the document as it is now.
  async function saveEditedTemplate({ name, description, version }) {
    const saved = await updateTemplate(editedTemplate.id, { file: docxBlob, fileName: documentName, name, description, version });
    editedTemplate = templateInfo(saved);
    saveBuilderSession();
    templateSaved($t("builder.templateUpdated", { name }));
  }

  function templateSaved(message) {
    isSavingTemplate = false;
    templateNotice = message;
    clearTimeout(templateNoticeTimer);
    templateNoticeTimer = setTimeout(() => (templateNotice = ""), 4000);
  }

  // Opens the document, as it is now, in the Compiler to fill in its keywords (after confirmation if the Compiler
  // has another document open).
  // The finished document goes to the Compiler (with its tables of contents updated, as when saving it).
  async function openInCompiler() {
    if (!navigate) {
      return;
    }
    const result = await finishedDocument(false);
    if (result) {
      transferDocument("compiler", result.docx, documentName, navigate);
    }
  }

  // Downloads the blob with the given name.
  function download(blob, fileName) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.click();
    // Deferred revoke: some browsers (e.g. Firefox) start the download asynchronously.
    setTimeout(() => URL.revokeObjectURL(url));
  }

  // Reads a blob and returns its content in base64.
  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.slice(reader.result.indexOf(",") + 1));
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(blob);
    });
  }

  // Converts a base64 string into a Blob of the given type.
  function base64ToBlob(base64, type) {
    const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
    return new Blob([bytes], { type });
  }
</script>

<svelte:window onkeydown={handleWindowKeydown} />

{#if docxBlob}
  <div class="builder-page" style={`--sidebar-width: ${sidebarWidth}px`}>
    <aside class="context-sidebar builder-sidebar" aria-label={$t("builder.sidebarLabel")}>
      <div class="context-sidebar-heading">
        <div class="sidebar-title">
          <BackButton onDark />
          <div>
            <p>{$t("nav.builder")}</p>
            <h2 title={documentName}>{documentName}</h2>
            {#if editedTemplate}
              <span class="template-editing-badge" title={editedTemplate.name}>{$t("builder.editingTemplate", { name: editedTemplate.name })}</span>
            {/if}
          </div>
        </div>
        <button class="close-document-button" type="button" disabled={isSaving} onclick={closeDocument}>{$t("common.newDocument")}</button>
      </div>
      <div class="save-buttons">
        <button class="save-button save-pdf" type="button" disabled={isSaving || isRenderingPdf} onclick={savePdf}>
          <FileTypeIcon type="pdf" />{$t("common.savePdf")}
        </button>
        <button class="save-button save-word" type="button" disabled={isSaving || isRenderingPdf} onclick={saveWord}>
          <FileTypeIcon type="word" />{$t("common.saveWord")}
        </button>
      </div>
      <!-- The PDF is created on request, from the document after the last change has been applied. -->
      <button class="preview-button" type="button" disabled={isSaving || isRenderingPdf} onclick={openPreview}>
        <FileTypeIcon type="pdf" />{$t("builder.previewPdf")}
      </button>
      <!-- The template keeps the document as it is now, with all its nodes. While editing a template it is updated. -->
      <button class="preview-button" class:template-save-button={editedTemplate} type="button" disabled={isSaving} onclick={() => (isSavingTemplate = true)}>
        <NavIcon name="templates" className="button-icon" />{editedTemplate ? $t("builder.saveEditedTemplate") : $t("builder.saveTemplate")}
      </button>
      <button class="preview-button" type="button" disabled={isSaving || isRenderingPdf || !navigate} title={$t("transfer.toCompilerHint")} onclick={openInCompiler}>
        <NavIcon name="compiler" className="button-icon" />{$t("transfer.toCompiler")}
      </button>
      <div class="builder-palette">
        <ContentPalette
          hint={$t("builder.paletteHint")}
          disabled={isSaving || !styles}
          disableSaved={isSaving}
          onSelect={insertAtEnd}
        />
      </div>
      <p class="toc-title">{$t("builder.toc")}</p>
      <TocPanel entries={tocEntries} activeId={activeHeadingId} selectedIds={selectedKeys} onSelect={goToHeading} />
    </aside>
    <SidebarResizer bind:width={sidebarWidth} min={200} max={520} storageKey="builder" label={$t("builder.resizeToc")} />

    <section class="builder-graph-section" aria-label={$t("builder.contentsLabel")}>
      <!-- Status, selection and errors stay above the graph, at the top left. -->
      <div class="builder-graph-overlay">
        {#if isSaving}<p class="builder-status" role="status">{$t("builder.updating")}</p>{/if}
        {#if finishing}<p class="builder-status" role="status">{finishing === "pdf" ? $t("builder.renderingPdf") : $t("builder.preparingDocument")}</p>{/if}
        {#if templateNotice}<p class="builder-status" role="status">{templateNotice}</p>{/if}
        {#if selectedItems.length}
          <div class="selection-toolbar" role="toolbar" aria-label={$t("builder.selectionLabel")}>
            <span>{$t("builder.selected", { count: selectedItems.length })}</span>
            <small class="selection-hint">{$t("builder.selectionHint")}</small>
            <button class="secondary-button" type="button" disabled={isSaving || selectedItems.length === blocks.length} onclick={() => selectAll(true)}>{$t("builder.selectAll")}</button>
            <button class="secondary-button" type="button" disabled={isSaving} onclick={() => selectAll(false)}>{$t("builder.deselectAll")}</button>
            <button class="selection-delete" type="button" disabled={isSaving} onclick={deleteSelected}>{$t("common.delete")}</button>
          </div>
        {/if}
        {#if actionError}<p class="compile-error builder-action-error" role="alert">{actionError}</p>{/if}
        {#each notices as notice}<p class="table-warning builder-action-error" role="status">{notice}</p>{/each}
      </div>
      <BuilderGraph
        bind:this={graph}
        {structure}
        activeId={activeHeadingId}
        {selectedKeys}
        disabled={isSaving}
        stylesReady={Boolean(styles)}
        onInsert={openInsertion}
        onEdit={openEditing}
        onDelete={deleteItem}
        onToggleSelect={toggleSelect}
        onAppend={insertAtEnd}
        onMove={moveItem}
      />
    </section>
  </div>

  {#if (insertion || editing) && styles}
    <!-- key: another element to edit recreates the modal with its values. -->
    {#key editing?.item ?? insertion}
      <ContentModal
        {styles}
        suggestedLevel={insertion?.suggestedLevel ?? 1}
        initial={editing?.item ?? null}
        initialType={insertion?.type ?? "heading"}
        onPickSaved={insertion ? switchToPicker : null}
        {isSaving}
        errorMessage={modalError}
        onSubmit={submitContent}
        onDelete={() => deleteItem(editing.item)}
        onClose={closeModal}
      />
    {/key}
  {/if}
  {#if previewUrl}
    <div class="keyword-modal-backdrop pdf-preview-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && closePreview()}>
      <div class="pdf-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="pdf-preview-title">
        <div class="pdf-preview-header">
          <h2 id="pdf-preview-title">{documentName.replace(/\.docx$/i, ".pdf")}</h2>
          <button class="save-button save-pdf" type="button" onclick={savePdf}>
            <FileTypeIcon type="pdf" />{$t("common.savePdf")}
          </button>
          <button class="pdf-preview-close" type="button" aria-label={$t("builder.closePreview")} title={$t("builder.closePreviewHint")} onclick={closePreview}>×</button>
        </div>
        <iframe src={previewUrl} title={$t("builder.previewOf", { name: documentName })}></iframe>
      </div>
    </div>
  {/if}
  {#if isSavingTemplate && editedTemplate}
    <TemplateModal
      title={$t("templates.modal.editTitle")}
      intro={$t("templates.modal.editIntro")}
      submitLabel={$t("templates.modal.saveChanges")}
      initialName={editedTemplate.name}
      initialDescription={editedTemplate.description}
      initialVersion={editedTemplate.version}
      onSubmit={saveEditedTemplate}
      onSubmitNew={saveAsTemplate}
      newLabel={$t("templates.modal.saveAsNew")}
      onClose={() => (isSavingTemplate = false)}
    />
  {:else if isSavingTemplate}
    <TemplateModal
      title={$t("templates.modal.saveTitle")}
      intro={$t("templates.modal.saveIntro")}
      submitLabel={$t("templates.modal.saveButton")}
      initialName={documentName.replace(/\.docx$/i, "")}
      onSubmit={saveAsTemplate}
      onClose={() => (isSavingTemplate = false)}
    />
  {/if}
  {#if picker}
    <!-- Full screen choice with the Explore contents page, above the Builder. -->
    <div class="picker-overlay" role="dialog" aria-modal="true" aria-label={$t("builder.pickLabel")}>
      <ExploreContents pickMode onPick={insertSavedBlocks} onCancel={() => (picker = null)} />
    </div>
  {/if}
{:else if isLoading}
  <p class="status">{isRestoring ? $t("builder.restoring") : $t("builder.opening")}</p>
{:else}
  <FileDropZone
    eyebrow={$t("nav.builder")}
    title={$t("builder.uploadTitle")}
    description={$t("builder.uploadDescription")}
    buttonLabel={$t("builder.uploadButton")}
    extensions={[".docx", ".dotx"]}
    accept=".docx,.dotx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.wordprocessingml.template"
    invalidMessage={$t("builder.invalidFile")}
    {errorMessage}
    onFile={openFile}
  >
    <button class="secondary-button" type="button" onclick={createEmptyDocument}>{$t("builder.createEmpty")}</button>
    {#if navigate}
      <button class="secondary-button" type="button" onclick={() => navigate("/documents/templates")}>{$t("builder.fromTemplate")}</button>
    {/if}
  </FileDropZone>
{/if}
