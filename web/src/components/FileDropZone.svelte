<script>
  import { t } from "../i18n.js";
  import BackButton from "./BackButton.svelte";

  // Upload screen for a file: button to choose it and drag-and-drop over the whole area.
  // buttonLabel and invalidMessage default to generic texts ("Choose file", "Unsupported file format.").
  export let eyebrow = "";
  export let title = "";
  export let description = "";
  export let buttonLabel = null;
  // Accepted extensions (lowercase, with the dot) and value of the picker's accept attribute.
  export let extensions = [];
  export let accept = "";
  export let invalidMessage = null;
  // Error of the parent (e.g. failed upload), shown together with the validation one.
  export let errorMessage = "";
  export let fileName = "";
  export let onFile = () => {};

  let fileInput;
  let isDragging = false;
  let validationError = "";

  // Validates the extension and passes the file to the parent.
  function selectFile(file) {
    if (!extensions.some((extension) => file.name.toLowerCase().endsWith(extension))) {
      validationError = invalidMessage ?? $t("upload.invalidFormat");
      return;
    }
    validationError = "";
    onFile(file);
  }

  // Handles the file chosen with the picker.
  function handleFileChange(event) {
    const [file] = event.target.files;
    event.target.value = "";
    if (file) {
      selectFile(file);
    }
  }

  // Highlights the area while a file is dragged over it.
  function handleDragOver(event) {
    if (!event.dataTransfer?.types.includes("Files")) {
      return;
    }
    // Without preventDefault the browser does not allow the drop (and would open the file).
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    isDragging = true;
  }

  // Removes the highlight only when the pointer really leaves the area (not when moving over an inner element).
  function handleDragLeave(event) {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      isDragging = false;
    }
  }

  // Uploads the first file dropped on the area.
  function handleDrop(event) {
    event.preventDefault();
    isDragging = false;
    const [file] = event.dataTransfer?.files ?? [];
    if (file) {
      selectFile(file);
    }
  }
</script>

<div
  class="upload-empty-state"
  class:dragging={isDragging}
  role="region"
  aria-label={$t("upload.dropArea", { title })}
  ondragenter={handleDragOver}
  ondragover={handleDragOver}
  ondragleave={handleDragLeave}
  ondrop={handleDrop}
>
  <div class="page-back"><BackButton /></div>
  <div class="page-heading">
    <p>{eyebrow}</p>
    <h1>{title}</h1>
    <span>{description}</span>
  </div>

  <section class="upload-panel" aria-label={title}>
    <input bind:this={fileInput} type="file" {accept} onchange={handleFileChange} hidden />
    <button type="button" onclick={() => fileInput?.click()}>{buttonLabel ?? $t("upload.chooseFile")}</button>
    <!-- Other ways to start, next to the upload button (e.g. an empty document in the Builder). -->
    <slot />
    {#if fileName}
      <span class="file-name">{fileName}</span>
    {/if}
  </section>
  {#if validationError || errorMessage}
    <p class="error" role="alert">{validationError || errorMessage}</p>
  {/if}
</div>
