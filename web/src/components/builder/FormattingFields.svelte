<script>
  import { t } from "../../i18n.js";

  // Direct formatting applied over the style (see src/builder/formatting.py): empty fields use the style.
  // showEmphasis: shows bold, italic and underline (for paragraphs the visual editor handles them).
  export let formatting = {};
  export let showEmphasis = true;
  export let idPrefix = "formatting";

  const FONTS = ["Arial", "Calibri", "Cambria", "Courier New", "Georgia", "Helvetica", "Segoe UI", "Tahoma", "Times New Roman", "Verdana"];
  // Labels: translation keys editor.<name>.
  const EMPHASIS = ["bold", "italic", "underline"];

  // Converts the value of a three-state select ("", "true", "false") into null/true/false.
  function toFlag(value) {
    return value === "" ? null : value === "true";
  }
</script>

<fieldset class="formatting-fields">
  <legend>{$t("formatting.title")} <span>{$t("formatting.hint")}</span></legend>
  <label for={`${idPrefix}-font`}>
    {$t("formatting.font")}
    <input id={`${idPrefix}-font`} list={`${idPrefix}-fonts`} bind:value={formatting.font} placeholder={$t("formatting.fromStyle")} />
    <datalist id={`${idPrefix}-fonts`}>
      {#each FONTS as font}<option value={font}></option>{/each}
    </datalist>
  </label>
  <label for={`${idPrefix}-size`}>
    {$t("formatting.size")}
    <input
      id={`${idPrefix}-size`}
      type="number"
      min="1"
      max="400"
      step="0.5"
      value={formatting.size ?? ""}
      placeholder={$t("formatting.fromStyle")}
      oninput={(event) => (formatting.size = event.target.value === "" ? null : Number(event.target.value))}
    />
  </label>
  <label for={`${idPrefix}-color`}>
    {$t("formatting.color")}
    <span class="color-field">
      <input
        type="checkbox"
        checked={Boolean(formatting.color)}
        aria-label={$t("formatting.customColor")}
        onchange={(event) => (formatting.color = event.target.checked ? "#000000" : null)}
      />
      <input id={`${idPrefix}-color`} type="color" value={formatting.color ?? "#000000"} disabled={!formatting.color} oninput={(event) => (formatting.color = event.target.value)} />
    </span>
  </label>
  <label for={`${idPrefix}-alignment`}>
    {$t("formatting.alignment")}
    <select id={`${idPrefix}-alignment`} bind:value={formatting.alignment}>
      <option value={null}>{$t("formatting.fromStyle")}</option>
      <option value="left">{$t("alignments.left")}</option>
      <option value="center">{$t("alignments.center")}</option>
      <option value="right">{$t("alignments.right")}</option>
      <option value="justify">{$t("alignments.justify")}</option>
    </select>
  </label>
  {#if showEmphasis}
    {#each EMPHASIS as emphasis (emphasis)}
      <label for={`${idPrefix}-${emphasis}`}>
        {$t(`editor.${emphasis}`)}
        <select
          id={`${idPrefix}-${emphasis}`}
          value={formatting[emphasis] == null ? "" : String(formatting[emphasis])}
          onchange={(event) => (formatting[emphasis] = toFlag(event.target.value))}
        >
          <option value="">{$t("formatting.fromStyle")}</option>
          <option value="true">{$t("common.yes")}</option>
          <option value="false">{$t("common.no")}</option>
        </select>
      </label>
    {/each}
  {/if}
</fieldset>
