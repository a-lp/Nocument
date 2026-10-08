<script>
  import { t } from "../../i18n.js";
  import ImageEditor from "../content/ImageEditor.svelte";
  import PluginPanel from "../plugins/PluginPanel.svelte";
  import TableEditor from "../table/TableEditor.svelte";
  import { createColumns, createRows, tableFromRows, tableRows as buildTableRows } from "../table/tableModel.js";
  import FormattingFields from "./FormattingFields.svelte";
  import RichTextEditor from "./RichTextEditor.svelte";

  // Modal to insert (or edit) a heading, a paragraph, an image or a table: in the Builder document
  // (context "document") or in a content block (context "block").
  // styles: styles to offer (see StyleAnalyzer.to_dict); suggestedLevel: level offered for a new heading;
  // initial: element to edit (null for a new content), used to fill in the form;
  // initialType: type selected at first for a new content (e.g. dragged from the sidebar).
  export let styles;
  export let suggestedLevel = 1;
  export let initial = null;
  export let initialType = "heading";
  export let context = "document";
  // onPickSaved: if given, the "Saved content" tab closes the form and goes to the choice among the saved blocks.
  export let onPickSaved = null;
  export let isSaving = false;
  export let errorMessage = "";
  export let onSubmit = () => {};
  export let onDelete = () => {};
  export let onClose = () => {};

  const isEditing = Boolean(initial);
  const inDocument = context === "document";
  // Tab labels: translation keys contentTypes.<type>.
  const TABS = ["heading", "paragraph", "image", "table"];

  let contentType = initial?.type ?? initialType;
  let headingText = initial?.type === "heading" ? initial.text : "";
  // A heading on several lines (e.g. "QUARTERLY" line break "Report") is edited in a text area: a one-line field
  // would lose the line breaks.
  const multilineHeading = headingText.includes("\n");
  let headingStyle = initial?.type === "heading" ? initial.style : defaultHeadingStyle(suggestedLevel);
  let headingFormatting = { ...emptyFormatting(), ...(initial?.type === "heading" ? initial.formatting : {}) };
  let paragraphHtml = initial?.type === "paragraph" ? initial.html : "";
  let paragraphStyle = initial?.type === "paragraph" ? initial.style : (styles.defaults.paragraph ?? "");
  let paragraphFormatting = { ...emptyFormatting(), ...(initial?.type === "paragraph" ? initial.formatting : {}) };
  let tableHeader = initial?.type === "table" ? initial.header : true;
  // Grid model (see tableModel.js): with the header the first row is in the column names.
  const initialTable = initial?.type === "table"
    ? tableFromRows(initial.rows, initial.header)
    : { columns: createColumns(2), rows: createRows(1, 2) };
  let tableColumns = initialTable.columns;
  let tableData = initialTable.rows;
  let tableSort = [];
  let tableCaption = initial?.type === "table" ? initial.caption : "";
  let tableCaptionPosition = initial?.type === "table" ? initial.caption_position : "below";
  // When editing, a table without style stays without style ("" = unchanged).
  let tableStyle = initial?.type === "table" ? (initial.style ?? "") : (styles.defaults.table ?? "");
  let tableAlignment = initial?.type === "table" ? initial.alignment : null;
  // Image: bytes in base64 (as in the content JSON), MIME type for the preview, width in cm.
  let imageData = initial?.type === "image" ? initial.data : "";
  let imageMimeType = initial?.type === "image" ? initial.content_type : "";
  let imageFilename = initial?.type === "image" ? initial.filename : "";
  let imageWidth = initial?.type === "image" ? initial.width : null;
  let imageAlignment = initial?.type === "image" ? initial.alignment : null;
  // Translation key of the validation error, "" if the form is valid.
  let validationError = "";
  // Increased when a plugin replaces the paragraph text: the editor only reads its html when it is created.
  let paragraphVersion = 0;

  // The style of the edited element is among the options even if the document hides it.
  $: headingStyles = withCurrentStyle(styles.headings, initial?.type === "heading" ? { id: initial.style, name: initial.style, level: initial.level } : null);
  $: paragraphStyles = withCurrentStyle(styles.paragraphs, initial?.type === "paragraph" ? { id: initial.style, name: initial.style } : null);
  $: headingLevels = [...new Set(headingStyles.map((style) => style.level))].sort((first, second) => first - second);
  $: selectedHeading = headingStyles.find((style) => style.id === headingStyle);
  $: keptColumnCount = tableColumns.filter((column) => column.keep).length;
  // Changing the number of columns of a document table makes the backend recreate it (see WordTable.update).
  $: columnsChanged = inDocument && initial?.type === "table" && keptColumnCount !== Math.max(...initial.rows.map((row) => row.length));

  // Adds current to styles if it is missing.
  function withCurrentStyle(list, current) {
    return current?.id && !list.some((style) => style.id === current.id) ? [...list, current] : list;
  }

  // Empty formatting: everything from the style.
  function emptyFormatting() {
    return { font: "", size: null, color: null, alignment: null, bold: null, italic: null, underline: null };
  }

  // Default style for a heading of the given level (or of the nearest available level).
  function defaultHeadingStyle(level) {
    const defaults = styles.defaults.heading ?? {};
    return defaults[level] ?? defaults[1] ?? styles.headings[0]?.id ?? "";
  }

  // Puts the content created by a plugin (JSON of the contents, of the current type) in the form fields; the user
  // can still change them before inserting. Styles the document does not have are ignored.
  function applyPluginContent(content) {
    validationError = "";
    if (content.type === "heading") {
      headingText = content.text;
      const known = headingStyles.find((style) => style.id === content.style);
      headingStyle = known ? known.id : defaultHeadingStyle(content.level);
      headingFormatting = { ...emptyFormatting(), ...content.formatting };
    } else if (content.type === "paragraph") {
      paragraphHtml = content.html;
      if (paragraphStyles.some((style) => style.id === content.style)) {
        paragraphStyle = content.style;
      }
      paragraphFormatting = { ...emptyFormatting(), ...content.formatting };
      paragraphVersion += 1;
    } else if (content.type === "image") {
      imageData = content.data;
      imageMimeType = content.content_type;
      imageFilename = content.filename;
      imageWidth = content.width;
      imageAlignment = content.alignment;
    } else if (content.type === "table") {
      const table = tableFromRows(content.rows, content.header);
      tableColumns = table.columns;
      tableData = table.rows;
      tableSort = [];
      tableHeader = content.header;
      tableCaption = content.caption;
      tableCaptionPosition = content.caption_position;
      if (styles.tables.some((style) => style.id === content.style)) {
        tableStyle = content.style;
      }
      tableAlignment = content.alignment;
    }
  }

  // Removes the empty formatting fields, so the backend uses the style.
  function cleanFormatting(formatting) {
    return Object.fromEntries(Object.entries(formatting).filter(([, value]) => value !== null && value !== ""));
  }

  // Validates the form and passes the content to the parent in the format of /api/builder/insert.
  function submit(event) {
    event.preventDefault();
    validationError = "";
    let content;
    if (contentType === "heading") {
      if (!headingText.trim()) {
        validationError = "contentModal.errors.headingText";
        return;
      }
      content = {
        type: "heading",
        text: headingText.trim(),
        level: selectedHeading?.level ?? suggestedLevel,
        style: headingStyle || null,
        formatting: cleanFormatting(headingFormatting)
      };
    } else if (contentType === "paragraph") {
      if (!paragraphHtml) {
        validationError = "contentModal.errors.paragraphText";
        return;
      }
      content = { type: "paragraph", html: paragraphHtml, style: paragraphStyle || null, formatting: cleanFormatting(paragraphFormatting) };
    } else if (contentType === "image") {
      if (!imageData) {
        validationError = "contentModal.errors.image";
        return;
      }
      content = {
        type: "image",
        data: imageData,
        filename: imageFilename || "image",
        content_type: imageMimeType,
        width: imageWidth || null,
        alignment: imageAlignment
      };
    } else {
      if (!keptColumnCount) {
        validationError = "contentModal.errors.tableColumns";
        return;
      }
      const rows = buildTableRows(tableColumns, tableData, tableSort, tableHeader);
      if (!rows.length) {
        validationError = "contentModal.errors.tableRows";
        return;
      }
      content = {
        type: "table",
        rows,
        header: tableHeader,
        caption: tableCaption.trim(),
        caption_position: tableCaptionPosition,
        style: tableStyle || null,
        alignment: tableAlignment
      };
    }
    onSubmit(content);
  }
</script>

<div class="keyword-modal-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && !isSaving && onClose()}>
  <div class="keyword-modal wide builder-modal" role="dialog" aria-modal="true" aria-labelledby="builder-modal-title">
    <button class="close-modal" type="button" aria-label={$t("common.close")} disabled={isSaving} onclick={onClose}>×</button>
    <p>{inDocument ? $t("nav.builder") : $t("nav.content")}</p>
    <h2 id="builder-modal-title">{isEditing ? $t(`contentModal.editTitle.${contentType}`) : $t("contentModal.newTitle")}</h2>
    <span class="modal-intro">
      {#if !inDocument}
        {$t("contentModal.intro.block")}
      {:else if isEditing}
        {$t("contentModal.intro.edit")}
      {:else}
        {$t("contentModal.intro.insert")}
      {/if}
    </span>

    {#if !isEditing}
      <div class="content-type-list" role="tablist" aria-label={$t("contentModal.contentType")}>
        {#each TABS as tab (tab)}
          <button class:active={contentType === tab} type="button" role="tab" aria-selected={contentType === tab} onclick={() => (contentType = tab)}>{$t(`contentTypes.${tab}`)}</button>
        {/each}
        {#if onPickSaved}
          <button type="button" role="tab" aria-selected="false" title={$t("palette.hints.saved")} onclick={onPickSaved}>{$t("contentTypes.saved")}</button>
        {/if}
      </div>
    {/if}
    {#if initial?.has_fields}
      <p class="table-warning" role="status">{$t("contentModal.fieldsWarning")}</p>
    {/if}

    <!-- Data from the plugins compatible with the chosen type, put in the form fields below. -->
    <PluginPanel {contentType} disabled={isSaving} onContent={applyPluginContent} />

    <form class="content-form" onsubmit={submit}>
      {#if contentType === "heading"}
        <label for="heading-text">
          {$t("contentModal.headingText")}
          {#if multilineHeading}
            <textarea id="heading-text" rows="3" bind:value={headingText}></textarea>
          {:else}
            <input id="heading-text" type="text" bind:value={headingText} />
          {/if}
        </label>
        <label for="heading-style">
          {$t("contentModal.style")}
          <select id="heading-style" bind:value={headingStyle}>
            {#each headingLevels as level}
              <optgroup label={$t("contentModal.level", { level })}>
                {#each headingStyles.filter((style) => style.level === level) as style (style.id)}
                  <option value={style.id}>{style.name}{style.id === styles.defaults.heading?.[level] ? ` ${$t("contentModal.defaultStyle")}` : ""}</option>
                {/each}
              </optgroup>
            {/each}
          </select>
        </label>
        <FormattingFields bind:formatting={headingFormatting} idPrefix="heading" />
      {:else if contentType === "paragraph"}
        <label for="paragraph-style">
          {$t("contentModal.style")}
          <select id="paragraph-style" bind:value={paragraphStyle}>
            {#each paragraphStyles as style (style.id)}
              <option value={style.id}>{style.name}{style.id === styles.defaults.paragraph ? ` ${$t("contentModal.defaultStyle")}` : ""}</option>
            {/each}
          </select>
        </label>
        <span class="field-label">{$t("contentModal.text")}</span>
        {#key paragraphVersion}
          <RichTextEditor html={paragraphHtml} onChange={(html) => (paragraphHtml = html)} />
        {/key}
        <FormattingFields bind:formatting={paragraphFormatting} showEmphasis={false} idPrefix="paragraph" />
      {:else if contentType === "image"}
        <ImageEditor
          bind:data={imageData}
          bind:mimeType={imageMimeType}
          bind:filename={imageFilename}
          bind:width={imageWidth}
          bind:alignment={imageAlignment}
        />
      {:else}
        <div class="builder-table-options">
          <label for="table-style">
            {$t("contentModal.style")}
            <select id="table-style" bind:value={tableStyle}>
              {#if isEditing}<option value="">{inDocument ? $t("contentModal.unchanged") : $t("contentModal.noStyle")}</option>{/if}
              {#each styles.tables as style (style.id)}
                <option value={style.id}>{style.name}{style.id === styles.defaults.table ? ` ${$t("contentModal.defaultStyle")}` : ""}</option>
              {/each}
            </select>
          </label>
          <label for="table-alignment">
            {$t("formatting.alignment")}
            <select id="table-alignment" bind:value={tableAlignment}>
              <option value={null}>{$t("formatting.fromStyle")}</option>
              <option value="left">{$t("alignments.left")}</option>
              <option value="center">{$t("alignments.center")}</option>
              <option value="right">{$t("alignments.right")}</option>
            </select>
          </label>
        </div>
        {#if columnsChanged}
          <p class="table-warning" role="status">{$t("contentModal.columnsChanged")}</p>
        {/if}
        <TableEditor bind:columns={tableColumns} bind:rows={tableData} bind:sort={tableSort} bind:header={tableHeader} />
        <div class="builder-table-options">
          <label for="table-caption">{$t("contentModal.caption")}<input id="table-caption" type="text" bind:value={tableCaption} placeholder={$t("contentModal.captionPlaceholder")} /></label>
          <label for="table-caption-position">
            {$t("contentModal.captionPosition")}
            <select id="table-caption-position" bind:value={tableCaptionPosition}>
              <option value="above">{$t("contentModal.captionAbove")}</option>
              <option value="below">{$t("contentModal.captionBelow")}</option>
            </select>
          </label>
        </div>
      {/if}

      {#if validationError || errorMessage}
        <p class="compile-error" role="alert">{validationError ? $t(validationError) : errorMessage}</p>
      {/if}
      <div class="content-actions">
        {#if isEditing}
          <button class="remove-content-button" type="button" disabled={isSaving} onclick={onDelete}>{$t("common.delete")}</button>
        {/if}
        <button class="insert-content-button" type="submit" disabled={isSaving}>
          {isSaving ? $t("common.saving") : isEditing ? $t("contentModal.saveChanges") : $t("contentModal.insert")}
        </button>
      </div>
    </form>
  </div>
</div>
