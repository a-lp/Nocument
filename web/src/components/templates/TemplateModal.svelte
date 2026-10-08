<script>
  import { onMount } from "svelte";
  import { t } from "../../i18n.js";

  // Information of a template to save: name (required), description and version and, with withFile (import), the
  // Word file. onSubmit({ name, description, version, file }) saves it and throws an Error with the message to show;
  // onClose closes the modal (Esc, ×, Cancel or a click outside). With onSubmitNew (editing a template) a second
  // button saves the same information as a new template instead (newLabel).
  export let title;
  export let intro = "";
  export let submitLabel;
  export let initialName = "";
  export let initialDescription = "";
  export let initialVersion = "1.0";
  export let withFile = false;
  export let onSubmit;
  export let onSubmitNew = null;
  export let newLabel = "";
  export let onClose;

  const MAX_NAME = 120;
  const MAX_DESCRIPTION = 1000;
  const MAX_VERSION = 40;
  const EXTENSIONS = [".docx", ".dotx"];

  let name = initialName;
  let description = initialDescription;
  let version = initialVersion;
  let file = null;
  let errorMessage = "";
  let isSaving = false;
  let nameInput;
  let fileInput;

  onMount(() => (withFile ? fileInput : nameInput)?.focus());

  // The name of the chosen file becomes the template name, if none was written yet.
  function handleFileChange(event) {
    const [chosen] = event.target.files;
    errorMessage = "";
    if (!chosen) {
      file = null;
      return;
    }
    if (!EXTENSIONS.some((extension) => chosen.name.toLowerCase().endsWith(extension))) {
      file = null;
      event.target.value = "";
      errorMessage = $t("templates.modal.fileRequired");
      return;
    }
    file = chosen;
    if (!name.trim()) {
      name = chosen.name.replace(/\.(docx|dotx)$/i, "");
    }
  }

  // Submit of the form: the button pressed chooses between onSubmit and onSubmitNew.
  async function submit(event) {
    event.preventDefault();
    const save = event.submitter?.dataset.action === "new" ? onSubmitNew : onSubmit;
    if (withFile && !file) {
      errorMessage = $t("templates.modal.fileRequired");
      return;
    }
    if (!name.trim()) {
      errorMessage = $t("errors.templateNameRequired");
      nameInput?.focus();
      return;
    }
    isSaving = true;
    errorMessage = "";
    try {
      await save({ name: name.trim(), description: description.trim(), version: version.trim(), file });
    } catch (error) {
      errorMessage = error.message;
    } finally {
      isSaving = false;
    }
  }

  function handleKeydown(event) {
    if (event.key === "Escape" && !isSaving) {
      onClose();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="keyword-modal-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && !isSaving && onClose()}>
  <div class="keyword-modal template-modal" role="dialog" aria-modal="true" aria-labelledby="template-modal-title">
    <button class="close-modal" type="button" aria-label={$t("common.close")} disabled={isSaving} onclick={onClose}>×</button>
    <p>{$t("nav.templates")}</p>
    <h2 id="template-modal-title">{title}</h2>
    {#if intro}<span class="modal-intro">{intro}</span>{/if}

    <form class="content-form" onsubmit={submit}>
      {#if withFile}
        <label>
          {$t("templates.modal.file")}
          <input bind:this={fileInput} type="file" accept=".docx,.dotx" disabled={isSaving} onchange={handleFileChange} />
        </label>
      {/if}
      <label>
        <span>{$t("templates.fields.name")} <span class="template-required" aria-hidden="true">*</span></span>
        <input bind:this={nameInput} type="text" bind:value={name} maxlength={MAX_NAME} required disabled={isSaving} placeholder={$t("templates.modal.namePlaceholder")} />
      </label>
      <label>
        {$t("templates.fields.description")}
        <textarea bind:value={description} rows="3" maxlength={MAX_DESCRIPTION} disabled={isSaving} placeholder={$t("templates.modal.descriptionPlaceholder")}></textarea>
      </label>
      <label>
        {$t("templates.fields.version")}
        <input type="text" bind:value={version} maxlength={MAX_VERSION} disabled={isSaving} placeholder={$t("templates.modal.versionPlaceholder")} />
      </label>
      {#if errorMessage}<p class="compile-error" role="alert">{errorMessage}</p>{/if}
      <div class="template-modal-actions">
        <button class="secondary-button" type="button" disabled={isSaving} onclick={onClose}>{$t("common.cancel")}</button>
        {#if onSubmitNew}
          <button class="secondary-button" type="submit" data-action="new" disabled={isSaving}>{newLabel}</button>
        {/if}
        <button type="submit" disabled={isSaving}>{isSaving ? $t("templates.modal.saving") : submitLabel}</button>
      </div>
    </form>
  </div>
</div>
