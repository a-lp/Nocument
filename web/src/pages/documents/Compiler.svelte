<script>
  import { confirmAction } from "../../confirm.js";
  import mammoth from "mammoth/mammoth.browser";
  import * as pdfjsLib from "pdfjs-dist";
  import PdfWorker from "../../pdfWorker.js?worker";
  import { onDestroy, onMount, tick } from "svelte";
  import { apiFetch } from "../../api.js";
  import { language, t, tr } from "../../i18n.js";
  import { clearSession, loadSession, saveSession } from "../../sessionStore.js";
  import FileDropZone from "../../components/FileDropZone.svelte";
  import KeywordSidebar from "../../components/KeywordSidebar.svelte";
  import RichTextEditor from "../../components/builder/RichTextEditor.svelte";
  import { valueFromHtml, valueHtml, valueText } from "../../richText.js";
  import ImageEditor from "../../components/content/ImageEditor.svelte";
  import PluginPanel from "../../components/plugins/PluginPanel.svelte";
  import TableEditor from "../../components/table/TableEditor.svelte";
  import { createColumns, createRows, restoreColumns, tableFromRows, tableRows } from "../../components/table/tableModel.js";
  import { takeTransferredDocument, transferDocument } from "../../documentTransfer.js";

  // navigate: goes to another page of the web app (Open in Builder).
  export let navigate = null;

  // The worker is started by Vite with the polyfills pdf.js needs (see pdfWorker.js), once for the whole app.
  pdfjsLib.GlobalWorkerOptions.workerPort ??= new PdfWorker();

  let editor;
  let pdfViewer;
  let selectedFile = null;
  // Word document compiled by the last compilation (null until compiled).
  let compiledDocx = null;
  let documentHtml = "";
  // PDF shown in the preview (original or compiled) and its object URL.
  let pdfBlob = null;
  let pdfUrl = "";
  let pdfPages = [];
  let pdfTextItems = [];
  let errorMessage = "";
  let compileError = "";
  let isLoading = false;
  let isCompiling = false;
  let keywords = [];
  // Content chosen for each keyword: { type: "text" | "image" | "table", value }; an image also has its width
  // (cm), a table its grid (table) and the relative widths of its columns (columnWidths).
  let keywordValues = {};
  let keywordFocusIndexes = {};
  let activePdfMarker = null;
  let activeKeyword = "";
  let contentType = "text";
  // The modal uses the same editors as the Builder and the content blocks (RichTextEditor, ImageEditor,
  // TableEditor) and the plugins compatible with the type (PluginPanel).
  // HTML of the visual editor of a text keyword; saved as plain text or { html } (see richText.js).
  let textContent = "";
  // Increased when a plugin replaces the text: the editor only reads its html when it is created.
  let textVersion = 0;
  // Image: bytes in base64, MIME type, file name and width in cm (null = native size reduced to the page).
  let imageData = "";
  let imageMimeType = "";
  let imageFilename = "";
  let imageWidth = null;
  // Table grid (see tableModel.js): rows in their base order, columns (keep = false: not inserted) and sorting.
  let tableData = createRows(1, 2);
  let tableColumns = createColumns(2);
  let tableSort = [];
  // The first row of an imported CSV gives the column names (not inserted in the document).
  let tableHeader = false;
  // If true, the proportions of the column widths are applied to the document table.
  let applyColumnWidths = false;
  // Becomes true at the first resize of a column in the open modal.
  let columnsResized = false;
  // Columns of the document table containing the active keyword (null if it is not in a table).
  let documentColumns = null;
  let sidebarWidth = 20;
  // Becomes true after the restore attempt: before it nothing is saved, so the session is not overwritten.
  let sessionReady = false;
  let isRestoring = false;
  let saveTimer;

  // Content type -> compiler class in the backend ("class" field of /api/compile).
  const COMPILER_CLASSES = { text: "KeywordCompiler", image: "ImageCompiler", table: "TableCompiler" };
  const DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  // Key of the Compiler session in sessionStore.js ("analyzer", its name before the rename: old sessions are kept).
  const SESSION_KEY = "analyzer";

  // Labels of the content types, shown next to the keywords in the sidebar.
  $: contentLabels = { text: $t("compiler.text"), image: $t("contentTypes.image"), table: $t("contentTypes.table") };
  $: keptColumnCount = tableColumns.filter((column) => column.keep).length;
  // The proportions only apply if the kept columns match the cells of the row in the document.
  $: canApplyColumnWidths = Boolean(documentColumns) && keptColumnCount === documentColumns;
  // The keyword sidebar only appears with a document loaded.
  $: hasDocument = Boolean(documentHtml);
  // Saves the session at every change of the work on the document.
  $: if (sessionReady) scheduleSessionSave(selectedFile, pdfBlob, compiledDocx, keywords, keywordValues, sidebarWidth);

  // Loads the .docx: asks the backend for the PDF and the keywords found and shows it.
  async function loadFile(file) {
    errorMessage = "";
    isLoading = true;
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await apiFetch("/api/render-pdf", { method: "POST", body: formData });
      if (!response.ok) {
        throw new Error("PDF rendering failed");
      }
      // The backend returns the PDF together with the keywords found in the document.
      const data = await response.json();
      await showDocument({
        file,
        pdf: base64ToBlob(data.pdf, "application/pdf"),
        compiledDocx: null,
        keywords: data.keywords ?? [],
        keywordValues: {}
      });
    } catch (error) {
      console.error("Cannot show the document", error);
      resetDocument();
      errorMessage = $t("compiler.loadError");
    } finally {
      isLoading = false;
    }
  }

  // Shows a document (just loaded or restored from the session): converts it to HTML for highlights and tables,
  // draws the PDF and restores keywords and contents.
  async function showDocument(session) {
    const result = await mammoth.convertToHtml({ arrayBuffer: await session.file.arrayBuffer() });
    selectedFile = session.file;
    compiledDocx = session.compiledDocx;
    keywords = session.keywords;
    keywordValues = session.keywordValues;
    keywordFocusIndexes = {};
    activePdfMarker = null;
    compileError = "";
    documentHtml = result.value;
    setPdf(session.pdf);
    // The document view (and the PDF container) only appears when loading is over.
    isLoading = false;
    isRestoring = false;
    await tick();
    await renderPdf(session.pdf);
    highlightKeywords();
  }

  // Sets the preview PDF, releasing the previous object URL.
  function setPdf(blob) {
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
    }
    pdfBlob = blob;
    pdfUrl = blob ? URL.createObjectURL(blob) : "";
  }

  // Empties the Compiler, going back to the upload screen.
  function resetDocument() {
    selectedFile = null;
    compiledDocx = null;
    documentHtml = "";
    setPdf(null);
    pdfPages = [];
    pdfTextItems = [];
    keywords = [];
    keywordValues = {};
    keywordFocusIndexes = {};
    activePdfMarker = null;
    compileError = "";
    errorMessage = "";
    closeKeywordPanel();
  }

  // Leaves the current document (after confirmation) and clears the saved session.
  async function closeDocument() {
    if (!(await confirmAction($t("compiler.confirmClose"), { title: $t("confirm.titles.closeDocument"), action: $t("confirm.actions.close"), danger: true }))) {
      return;
    }
    clearTimeout(saveTimer);
    resetDocument();
    try {
      await clearSession(SESSION_KEY);
    } catch (error) {
      console.warn("Cannot clear the saved session", error);
    }
  }

  // Opens the document in the Builder: the compiled one if it has been compiled, otherwise the original (after
  // confirmation if the Builder has another document open).
  function openInBuilder() {
    if (navigate && selectedFile) {
      transferDocument("builder", compiledDocx ?? selectedFile, selectedFile.name, navigate);
    }
  }

  // Saves the session after a short pause, so close changes produce a single save.
  function scheduleSessionSave() {
    clearTimeout(saveTimer);
    if (!selectedFile || !pdfBlob) {
      return;
    }
    saveTimer = setTimeout(async () => {
      try {
        await saveSession(SESSION_KEY, {
          file: selectedFile,
          fileName: selectedFile.name,
          pdf: pdfBlob,
          compiledDocx,
          keywords,
          keywordValues,
          sidebarWidth
        });
      } catch (error) {
        // E.g. private browsing or no space left: the Compiler still works, without session.
        console.warn("Cannot save the session", error);
      }
    }, 400);
  }

  // When the page loads it restores the last saved session, if any; a document sent from the Builder (Open in
  // Compiler) is opened instead, and replaces the session.
  onMount(async () => {
    const transferred = takeTransferredDocument("compiler");
    if (transferred) {
      sessionReady = true;
      await loadFile(transferred);
      return;
    }
    try {
      const session = await loadSession(SESSION_KEY);
      if (session?.file && session.pdf) {
        isRestoring = true;
        sidebarWidth = session.sidebarWidth ?? sidebarWidth;
        await showDocument({
          ...session,
          // IndexedDB can return a Blob without name: the File is recreated with the original name.
          file: new File([session.file], session.fileName, { type: DOCX_MIME_TYPE })
        });
      }
    } catch (error) {
      console.warn("Cannot restore the session", error);
      resetDocument();
      // A session that cannot be restored would fail at every reload: it is deleted.
      await clearSession(SESSION_KEY).catch(() => {});
    } finally {
      isRestoring = false;
      sessionReady = true;
    }
  });

  // Releases the PDF URL when leaving the page.
  onDestroy(() => {
    clearTimeout(saveTimer);
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
    }
  });

  // Starts resizing the sidebar by dragging the handle.
  function startSidebarResize(event) {
    event.preventDefault();
    window.addEventListener("pointermove", resizeSidebar);
    window.addEventListener("pointerup", stopSidebarResize, { once: true });
  }

  // Updates the sidebar width (15%-50%) following the pointer.
  function resizeSidebar(event) {
    const page = event.currentTarget?.querySelector?.(".word-page") || document.querySelector(".word-page");
    if (!page) {
      return;
    }

    const percentage = ((event.clientX - page.getBoundingClientRect().left) / page.offsetWidth) * 100;
    sidebarWidth = Math.min(50, Math.max(15, percentage));
  }

  // Ends the sidebar resize.
  function stopSidebarResize() {
    window.removeEventListener("pointermove", resizeSidebar);
  }

  // Resizes the sidebar with the left/right arrows.
  function resizeSidebarWithKeyboard(event) {
    if (event.key === "ArrowLeft") {
      sidebarWidth = Math.max(15, sidebarWidth - 2);
    }
    if (event.key === "ArrowRight") {
      sidebarWidth = Math.min(50, sidebarWidth + 2);
    }
  }

  // Escapes the special characters to use value in a RegExp.
  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Draws each PDF page in a canvas and saves the page text for the highlights.
  async function renderPdf(blob) {
    const pdf = await pdfjsLib.getDocument({ data: await blob.arrayBuffer() }).promise;
    pdfPages = Array.from({ length: pdf.numPages }, (_, index) => ({
      number: index + 1,
      viewport: null,
      highlights: []
    }));
    pdfTextItems = [];
    pdfViewer.replaceChildren();
    const canvases = pdfPages.map((page) => {
      const pageElement = document.createElement("div");
      pageElement.className = "pdf-page";
      const canvas = document.createElement("canvas");
      canvas.setAttribute("aria-label", tr("compiler.page", { number: page.number }));
      pageElement.append(canvas);
      pdfViewer.append(pageElement);
      return canvas;
    });

    for (let index = 0; index < pdf.numPages; index += 1) {
      const page = await pdf.getPage(index + 1);
      const viewport = page.getViewport({ scale: 1.5 });
      const canvas = canvases[index];
      const context = canvas.getContext("2d");
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await page.render({ canvasContext: context, viewport }).promise;
      const textContent = await page.getTextContent();
      pdfTextItems[index] = textContent.items;
      pdfPages[index] = { ...pdfPages[index], viewport };
    }

    pdfPages = [...pdfPages];
    updatePdfHighlights();
  }

  // Removes the keyword highlights from the document HTML.
  function clearKeywordHighlights() {
    editor?.querySelectorAll("mark.keyword-highlight").forEach((mark) => {
      mark.replaceWith(document.createTextNode(mark.textContent));
    });
  }

  // Sends document and assigned contents to /api/compile and shows the compiled PDF.
  // A compilation asked while another one runs: it starts when that one ends, with the latest contents.
  let compileAgain = false;

  // Compiles the document with the assigned contents and shows the resulting PDF. In the Compiler the preview follows
  // every change of the contents (saveContent, removeContent compile at once), unlike the Builder, which makes its
  // PDF only when asked.
  async function compileDocument() {
    if (!selectedFile) {
      return;
    }
    if (isCompiling) {
      compileAgain = true;
      return;
    }

    isCompiling = true;
    compileError = "";
    try {
      const payload = {
        file: { name: selectedFile.name, content: await readFileAsBase64(selectedFile) },
        // Only keywords with an assigned content can be compiled.
        keywords: keywords
          .filter((keyword) => keywordValues[keyword])
          .map((keyword) => {
            const { type, value, columnWidths } = keywordValues[keyword];
            let compilerValue = value;
            if (type === "image") {
              const data = dataUrlToBase64(value);
              compilerValue = keywordValues[keyword].width ? { data, width: keywordValues[keyword].width } : data;
            } else if (type === "table" && columnWidths) {
              compilerValue = { rows: value, column_widths: columnWidths };
            }
            return { keyword, class: COMPILER_CLASSES[type], value: compilerValue };
          })
      };
      const response = await apiFetch("/api/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.error || $t("errors.compileFailed"));
      }

      // The backend returns both the compiled PDF and the compiled Word document.
      const data = await response.json();
      const compiledPdf = base64ToBlob(data.pdf, "application/pdf");
      compiledDocx = base64ToBlob(data.docx, DOCX_MIME_TYPE);
      setPdf(compiledPdf);
      await renderPdf(compiledPdf);
      // Highlights of the keywords still without content.
      highlightKeywords();
    } catch (error) {
      compileError = error.message;
    } finally {
      isCompiling = false;
      if (compileAgain) {
        compileAgain = false;
        compileDocument();
      }
    }
  }

  // Downloads the PDF shown in the preview (the compiled one, if already compiled).
  function savePdf() {
    if (pdfUrl) {
      downloadUrl(pdfUrl, `${baseFileName()}.pdf`);
    }
  }

  // Downloads the compiled Word document or, before compiling, the uploaded one.
  function saveWord() {
    const blob = compiledDocx ?? selectedFile;
    if (!blob) {
      return;
    }
    const url = URL.createObjectURL(blob);
    downloadUrl(url, `${baseFileName()}.docx`);
    // Deferred revoke: some browsers (e.g. Firefox) start the download asynchronously.
    setTimeout(() => URL.revokeObjectURL(url));
  }

  // Name of the uploaded document without extension.
  function baseFileName() {
    return selectedFile?.name.replace(/\.docx$/i, "") || "document";
  }

  // Starts the download of url with the name fileName.
  function downloadUrl(url, fileName) {
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.click();
  }

  // Reads a file and returns its content in base64.
  function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(dataUrlToBase64(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  }

  // Extracts the base64 part from a data URL.
  function dataUrlToBase64(dataUrl) {
    return dataUrl.slice(dataUrl.indexOf(",") + 1);
  }

  // Converts a base64 string into a Blob of the given type.
  function base64ToBlob(base64, type) {
    const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
    return new Blob([bytes], { type });
  }

  // Highlights the keywords in the document HTML and in the PDF; with keywordToScroll it goes to its occurrence in the PDF.
  async function highlightKeywords(keywordToScroll = "") {
    if (!editor) {
      return;
    }

    clearKeywordHighlights();
    if (!keywords.length) {
      updatePdfHighlights();
      return;
    }

    const textNodes = [];
    const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.parentElement?.closest("mark")) {
        continue;
      }
      textNodes.push(node);
    }

    textNodes.forEach((textNode) => {
      const matches = [];
      keywords.forEach((keyword) => {
        const expression = new RegExp(escapeRegExp(keyword), "gi");
        let match;
        while ((match = expression.exec(textNode.textContent))) {
          matches.push({ start: match.index, end: match.index + match[0].length, keyword });
        }
      });

      if (!matches.length) {
        return;
      }

      matches.sort((first, second) => first.start - second.start || second.end - first.end);
      const fragment = document.createDocumentFragment();
      let cursor = 0;
      matches.forEach(({ start, end, keyword }) => {
        if (start < cursor) {
          return;
        }
        fragment.append(document.createTextNode(textNode.textContent.slice(cursor, start)));
        const mark = document.createElement("mark");
        mark.className = "keyword-highlight";
        mark.dataset.keyword = keyword;
        mark.textContent = textNode.textContent.slice(start, end);
        fragment.append(mark);
        cursor = end;
      });
      fragment.append(document.createTextNode(textNode.textContent.slice(cursor)));
      textNode.replaceWith(fragment);
    });

    updatePdfHighlights(keywordToScroll);
  }

  // Recomputes the position of the keywords in the PDF pages and draws their highlights.
  async function updatePdfHighlights(keywordToScroll = "") {
    const occurrenceCounters = {};
    pdfPages = pdfPages.map((page, pageIndex) => {
      const viewport = page.viewport;
      if (!viewport) {
        return page;
      }

      const highlights = [];
      (pdfTextItems[pageIndex] || []).forEach((item) => {
        if (!item.str) {
          return;
        }

        keywords.forEach((keyword) => {
          const expression = new RegExp(escapeRegExp(keyword), "gi");
          let match;
          while ((match = expression.exec(item.str))) {
            const fontHeight = Math.abs(item.transform[3]) || item.height || 10;
            const startPoint = [
              item.transform[4] + (item.width * match.index) / item.str.length,
              item.transform[5] - fontHeight * 0.78
            ];
            const endPoint = [
              item.transform[4] + (item.width * (match.index + match[0].length)) / item.str.length,
              item.transform[5] - fontHeight * 0.08
            ];
            pdfjsLib.Util.applyTransform(startPoint, viewport.transform);
            pdfjsLib.Util.applyTransform(endPoint, viewport.transform);
            const [left, top] = startPoint;
            const [right, bottom] = endPoint;
            highlights.push({
              keyword,
              occurrence: occurrenceCounters[keyword.toLowerCase()] || 0,
              left: Math.min(left, right) / viewport.width * 100,
              top: Math.min(top, bottom) / viewport.height * 100,
              width: Math.abs(right - left) / viewport.width * 100,
              height: 0.5
            });
            occurrenceCounters[keyword.toLowerCase()] = (occurrenceCounters[keyword.toLowerCase()] || 0) + 1;
          }
        });
      });

      return { ...page, highlights };
    });

    pdfPages.forEach((page, pageIndex) => {
      const pageElement = pdfViewer?.querySelectorAll(".pdf-page")[pageIndex];
      if (!pageElement) {
        return;
      }
      pageElement.querySelectorAll(".pdf-highlight").forEach((element) => element.remove());
      page.highlights.forEach((highlight) => {
        const element = document.createElement("span");
        element.className = "pdf-highlight";
        element.dataset.pdfKeyword = highlight.keyword;
        element.dataset.pdfOccurrence = String(highlight.occurrence);
        if (
          activePdfMarker?.keyword.toLowerCase() === highlight.keyword.toLowerCase()
          && activePdfMarker.occurrence === highlight.occurrence
        ) {
          element.classList.add("active");
        }
        element.style.left = `${highlight.left}%`;
        element.style.top = `${highlight.top}%`;
        element.style.width = `${highlight.width}%`;
        element.style.height = `${highlight.height}%`;
        pageElement.append(element);
      });
    });

    if (keywordToScroll) {
      await tick();
      focusKeywordInPdf(keywordToScroll);
    }
  }

  // Highlights and scrolls to the next occurrence of keyword in the PDF (cyclic).
  function focusKeywordInPdf(keyword) {
    const normalizedKeyword = keyword.toLowerCase();
    const occurrences = pdfPages.flatMap((page) => page.highlights)
      .filter((highlight) => highlight.keyword.toLowerCase() === normalizedKeyword);
    if (!occurrences.length) {
      return;
    }

    const nextIndex = ((keywordFocusIndexes[normalizedKeyword] ?? -1) + 1) % occurrences.length;
    keywordFocusIndexes = { ...keywordFocusIndexes, [normalizedKeyword]: nextIndex };
    const occurrence = occurrences[nextIndex];
    activePdfMarker = { keyword: occurrence.keyword, occurrence: occurrence.occurrence };
    pdfViewer?.querySelectorAll(".pdf-highlight").forEach((element) => {
      element.classList.toggle(
        "active",
        element.dataset.pdfKeyword.toLowerCase() === normalizedKeyword
        && Number(element.dataset.pdfOccurrence) === occurrence.occurrence
      );
    });
    pdfViewer?.querySelector(
      `[data-pdf-keyword="${CSS.escape(occurrence.keyword)}"][data-pdf-occurrence="${occurrence.occurrence}"]`
    )?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // Adds a keyword entered by hand and highlights it.
  function addKeyword(keyword) {
    keywords = [...keywords, keyword];
    highlightKeywords(keyword);
  }

  // Removes a keyword with its assigned content and its highlights.
  function removeKeyword(keyword) {
    keywords = keywords.filter((item) => item !== keyword);
    const { [keyword]: _removed, ...remainingValues } = keywordValues;
    keywordValues = remainingValues;
    clearKeywordHighlights();
    highlightKeywords();
  }

  // Opens the keyword modal, filled in with the content already saved.
  function focusKeyword(keyword) {
    activeKeyword = keyword;
    const saved = keywordValues[keyword];
    contentType = saved?.type ?? "text";
    textContent = saved?.type === "text" ? valueHtml(saved.value) : "";
    textVersion += 1;
    const image = saved?.type === "image" ? splitDataUrl(saved.value) : null;
    imageData = image?.data ?? "";
    imageMimeType = image?.mimeType ?? "";
    imageFilename = image ? $t("contentTypes.image") : "";
    imageWidth = saved?.type === "image" ? saved.width ?? null : null;
    documentColumns = detectTableColumns(keyword);
    // The save also keeps the excluded columns, so they can be brought back.
    const savedTable = saved?.type === "table"
      ? saved.table ?? { data: saved.value, columns: createColumns(saved.value[0]?.length ?? 1) }
      : null;
    if (savedTable) {
      const { columns, ids } = restoreColumns(savedTable.columns);
      tableColumns = columns;
      tableData = savedTable.data.map((row) => [...row]);
      tableSort = (savedTable.sort ?? []).filter((rule) => ids.has(rule.columnId)).map((rule) => ({ ...rule, columnId: ids.get(rule.columnId) }));
      tableHeader = Boolean(savedTable.header);
    } else {
      tableColumns = createColumns(documentColumns ?? 2);
      tableData = createRows(1, documentColumns ?? 2);
      tableSort = [];
      tableHeader = false;
    }
    applyColumnWidths = savedTable?.applyColumnWidths ?? false;
    columnsResized = Boolean(savedTable);
    highlightKeywords(keyword);
  }

  // Closes the keyword modal.
  function closeKeywordPanel() {
    activeKeyword = "";
    imageData = "";
  }

  // Base64 and MIME type of a data URL (the images are saved as data URLs in the session).
  function splitDataUrl(dataUrl) {
    const match = /^data:([^;,]*)(;base64)?,(.*)$/.exec(dataUrl ?? "");
    return match ? { mimeType: match[1], data: match[3] } : null;
  }

  // The first resize of a column turns on applying the proportions to the document, if possible.
  function handleColumnResize() {
    if (!columnsResized && canApplyColumnWidths) {
      applyColumnWidths = true;
    }
    columnsResized = true;
  }

  // Puts the content created by a plugin in the editor of the type (paragraph -> text, image, table); the user can
  // still change it before saving. Styles, captions and the like do not apply to a keyword.
  function applyPluginContent(content) {
    if (content.type === "paragraph") {
      textContent = content.html;
      textVersion += 1;
    } else if (content.type === "image") {
      imageData = content.data;
      imageMimeType = content.content_type;
      imageFilename = content.filename;
      imageWidth = content.width ?? null;
    } else if (content.type === "table") {
      const table = tableFromRows(content.rows, content.header);
      tableColumns = table.columns;
      tableData = table.rows.length ? table.rows : createRows(1, table.columns.length);
      tableSort = [];
      tableHeader = content.header;
    }
  }

  // Returns the number of columns of the document table containing keyword, or null.
  function detectTableColumns(keyword) {
    // If the keyword is in a document table, the same number of columns is suggested.
    const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.textContent.toLowerCase().includes(keyword.toLowerCase())) {
        return node.parentElement.closest("td, th")?.parentElement.children.length ?? null;
      }
    }
    return null;
  }

  // Saves the modal content for the active keyword.
  function saveContent(event) {
    event.preventDefault();
    if (!activeKeyword) {
      return;
    }

    let value;
    if (contentType === "text" && valueText(valueFromHtml(textContent)).trim()) {
      // Plain text while it has no formatting or links, as before; otherwise { html } for the KeywordCompiler.
      value = valueFromHtml(textContent);
    } else if (contentType === "image" && imageData) {
      value = `data:${imageMimeType || "image/png"};base64,${imageData}`;
    } else if (contentType === "table" && keptColumnCount) {
      // Only the data rows: the column names are not inserted (the document table has its own header).
      value = tableRows(tableColumns, tableData, tableSort, false);
    } else {
      return;
    }

    const table = contentType === "table"
      ? {
          data: tableData.map((row) => [...row]),
          columns: tableColumns.map((column) => ({ ...column })),
          sort: tableSort.map((rule) => ({ ...rule })),
          header: tableHeader,
          applyColumnWidths
        }
      : undefined;
    // Relative widths of the kept columns, in the order they end up in the document.
    const columnWidths = contentType === "table" && applyColumnWidths && canApplyColumnWidths
      ? tableColumns.filter((column) => column.keep).map((column) => column.width)
      : undefined;
    const width = contentType === "image" ? imageWidth : undefined;
    keywordValues = { ...keywordValues, [activeKeyword]: { type: contentType, value, width, table, columnWidths } };
    closeKeywordPanel();
    // The preview shows the keyword replaced at once.
    compileDocument();
  }

  // Removes the content assigned to the active keyword.
  function removeContent() {
    const { [activeKeyword]: _removed, ...remainingValues } = keywordValues;
    keywordValues = remainingValues;
    closeKeywordPanel();
    compileDocument();
  }
</script>

<div class="word-page" class:no-sidebar={!hasDocument} style={`--sidebar-width: ${sidebarWidth}%`}>
  {#if hasDocument}
    <KeywordSidebar
      {keywords}
      {keywordValues}
      {contentLabels}
      canCompile={Boolean(selectedFile) && !isLoading}
      {isCompiling}
      {compileError}
      onAddKeyword={addKeyword}
      onCompile={compileDocument}
      canSave={Boolean(pdfUrl) && !isLoading}
      onSavePdf={savePdf}
      onSaveWord={saveWord}
      canClose={Boolean(selectedFile) && !isLoading && !isCompiling}
      onClose={closeDocument}
      canOpenInBuilder={Boolean(selectedFile) && Boolean(navigate) && !isLoading && !isCompiling}
      openInBuilderHint={compiledDocx ? $t("transfer.toBuilderCompiledHint") : $t("transfer.toBuilderHint")}
      onOpenInBuilder={openInBuilder}
      onFocusKeyword={focusKeyword}
      onFocusKeywordInPdf={focusKeywordInPdf}
      onRemoveKeyword={removeKeyword}
    />

    <button
      class="resize-handle"
      type="button"
      aria-label={$t("compiler.resizeSidebar")}
      title={$t("compiler.resizeHint")}
      onpointerdown={startSidebarResize}
      onkeydown={resizeSidebarWithKeyboard}
    ></button>
  {/if}

  <div class="word-content" style={`--width: ${100 - sidebarWidth}%`}>
    {#if isRestoring}
      <p class="status">{$t("builder.restoring")}</p>
    {:else if isLoading}
      <p class="status">{$t("compiler.loading")}</p>
    {:else if documentHtml}
      <div class="editor-layout">
        <section class="editor-column" aria-label={$t("compiler.wordDocument")}>
          <div bind:this={editor} class="document-source" aria-hidden="true">
            {@html documentHtml}
          </div>
          <div bind:this={pdfViewer} class="pdf-viewer" aria-label={$t("builder.previewOf", { name: selectedFile?.name || $t("compiler.wordDocument") })}></div>
        </section>
      </div>
    {:else}
      <FileDropZone
        eyebrow={$t("nav.compiler")}
        title={$t("compiler.uploadTitle")}
        description={$t("compiler.uploadDescription")}
        buttonLabel={$t("compiler.uploadButton")}
        extensions={[".docx"]}
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        invalidMessage={$t("compiler.invalidFile")}
        {errorMessage}
        fileName={selectedFile?.name ?? ""}
        onFile={loadFile}
      />
    {/if}
  </div>
</div>

{#if activeKeyword}
  <div class="keyword-modal-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && closeKeywordPanel()}>
    <!-- Same frame as the Builder's content modal (ContentModal), for the same editors. -->
    <div class="keyword-modal wide builder-modal" role="dialog" aria-modal="true" aria-labelledby="keyword-modal-title">
      <button class="close-modal" type="button" aria-label={$t("common.close")} onclick={closeKeywordPanel}>×</button>
      <p>{$t("compiler.keyword")}</p>
      <h2 id="keyword-modal-title">{activeKeyword}</h2>
      <span class="modal-intro">{$t("compiler.modalIntro")}</span>

      <div class="content-type-list" role="tablist" aria-label={$t("contentModal.contentType")}>
        <button class:active={contentType === "text"} type="button" role="tab" aria-selected={contentType === "text"} onclick={() => (contentType = "text")}>{$t("compiler.text")}</button>
        <button class:active={contentType === "image"} type="button" role="tab" aria-selected={contentType === "image"} onclick={() => (contentType = "image")}>{$t("contentTypes.image")}</button>
        <button class:active={contentType === "table"} type="button" role="tab" aria-selected={contentType === "table"} onclick={() => (contentType = "table")}>{$t("contentTypes.table")}</button>
      </div>

      <!-- Data from the plugins compatible with the chosen type, put in the editor below (as in the Builder). -->
      <PluginPanel contentType={contentType === "text" ? "paragraph" : contentType} onContent={applyPluginContent} />

      <form class="content-form" onsubmit={saveContent}>
        {#if contentType === "text"}
          <span class="field-label">{$t("compiler.textToInsert")}</span>
          <!-- key: another keyword (or a plugin's text) starts the editor again with its own text. -->
          {#key `${activeKeyword}:${textVersion}`}
            <RichTextEditor html={textContent} label={$t("compiler.textToInsert")} onChange={(html) => (textContent = html)} />
          {/key}
        {:else if contentType === "image"}
          <!-- The alignment is the one of the keyword's paragraph, which also holds other text. -->
          <ImageEditor
            bind:data={imageData}
            bind:mimeType={imageMimeType}
            bind:filename={imageFilename}
            bind:width={imageWidth}
            showAlignment={false}
            idPrefix="keyword-image"
          />
        {:else}
          <TableEditor
            bind:columns={tableColumns}
            bind:rows={tableData}
            bind:sort={tableSort}
            bind:header={tableHeader}
            maxRows={500}
            headerLabel={$t("compiler.csvHeader")}
            hint={$t("compiler.tableHint")}
            resizable
            onColumnResize={handleColumnResize}
          >
            {#if documentColumns && keptColumnCount !== documentColumns}
              <p class="table-warning" role="status">
                {$t("compiler.columnsMismatch", { columns: documentColumns, selected: keptColumnCount })}
              </p>
            {/if}
            <label class="apply-widths-toggle" title={canApplyColumnWidths ? undefined : $t("compiler.applyWidthsDisabled")}>
              <input type="checkbox" bind:checked={applyColumnWidths} disabled={!canApplyColumnWidths} />
              {$t("compiler.applyWidths")}
            </label>
          </TableEditor>
        {/if}
        <div class="content-actions">
          {#if keywordValues[activeKeyword]}
            <button class="remove-content-button" type="button" onclick={removeContent}>{$t("compiler.removeContent")}</button>
          {/if}
          <button class="insert-content-button" type="submit">{$t("compiler.saveContent")}</button>
        </div>
      </form>
    </div>
  </div>
{/if}
