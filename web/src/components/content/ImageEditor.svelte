<script>
  import { t } from "../../i18n.js";

  // Editor of an image, the same everywhere an image is chosen (Builder, content blocks, Compiler): file, preview,
  // width in cm and, with showAlignment, the alignment. All bound: data (bytes in base64), mimeType, filename,
  // width (cm, null = native size reduced to the page), alignment (null = the style's one). idPrefix keeps the ids
  // of the fields unique.
  export let data = "";
  export let mimeType = "";
  export let filename = "";
  export let width = null;
  export let alignment = null;
  export let showAlignment = true;
  export let idPrefix = "image";

  // Formats python-docx can insert in a document (see NewImage and ImageCompiler).
  const IMAGE_TYPES = "image/png,image/jpeg,image/gif,image/bmp,image/tiff";

  // Reads the chosen image: base64 for the JSON and MIME type for the preview.
  function handleChange(event) {
    const [file] = event.target.files;
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      data = reader.result.slice(reader.result.indexOf(",") + 1);
      mimeType = file.type;
      filename = file.name;
    };
    reader.readAsDataURL(file);
  }
</script>

<label for={`${idPrefix}-file`}>
  {data ? $t("contentModal.replaceImage") : $t("contentTypes.image")} {$t("contentModal.imageFormats")}
  <input id={`${idPrefix}-file`} type="file" accept={IMAGE_TYPES} onchange={handleChange} />
</label>
{#if data}
  <img class="image-preview" src={`data:${mimeType || "image/png"};base64,${data}`} alt={$t("contentModal.imagePreview", { name: filename })} />
{/if}
<div class="builder-table-options">
  <label for={`${idPrefix}-width`}>
    {$t("contentModal.imageWidth")}
    <input
      id={`${idPrefix}-width`}
      type="number"
      min="0.5"
      max="100"
      step="0.5"
      value={width ?? ""}
      placeholder={$t("contentModal.imageWidthPlaceholder")}
      oninput={(event) => (width = event.target.value === "" ? null : Number(event.target.value))}
    />
  </label>
  {#if showAlignment}
    <label for={`${idPrefix}-alignment`}>
      {$t("formatting.alignment")}
      <select id={`${idPrefix}-alignment`} bind:value={alignment}>
        <option value={null}>{$t("formatting.fromStyle")}</option>
        <option value="left">{$t("alignments.left")}</option>
        <option value="center">{$t("alignments.center")}</option>
        <option value="right">{$t("alignments.right")}</option>
      </select>
    </label>
  {/if}
</div>
