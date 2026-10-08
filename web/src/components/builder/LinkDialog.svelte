<script>
  import { onMount } from "svelte";
  import { t } from "../../i18n.js";
  import { portal } from "../../portal.js";
  import { isSafeLink, normalizeLink } from "../../richText.js";

  // Address (and, without selected text, the text to show) of a hyperlink of the visual editor.
  // url: current address ("" for a new link); withText: also asks for the text; canRemove: the cursor is on a link.
  // onApply({ url, text }) with the address completed (https://, mailto:); onRemove(); onClose().
  export let url = "";
  export let withText = false;
  export let canRemove = false;
  export let onApply;
  export let onRemove = () => {};
  export let onClose;

  let address = url;
  let text = "";
  let error = "";
  let addressInput;

  onMount(() => addressInput?.focus());

  function submit(event) {
    event.preventDefault();
    const href = normalizeLink(address);
    if (!isSafeLink(href)) {
      error = $t("editor.linkInvalid");
      addressInput?.focus();
      return;
    }
    onApply({ url: href, text: text.trim() });
  }

  function handleKeydown(event) {
    if (event.key === "Escape") {
      // Only this dialog closes, not the modal containing the editor.
      event.stopPropagation();
      onClose();
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<!-- Under <body>: the editor is often inside a form (content modal), and forms cannot be nested. -->
<div use:portal class="keyword-modal-backdrop link-dialog-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && onClose()} onkeydown={handleKeydown}>
  <div class="link-dialog-frame" role="dialog" aria-modal="true" aria-labelledby="link-dialog-title">
    <form class="link-dialog" onsubmit={submit}>
      <h2 id="link-dialog-title">{canRemove ? $t("editor.editLink") : $t("editor.insertLink")}</h2>
      <label>
        {$t("editor.linkAddress")}
        <input bind:this={addressInput} type="text" inputmode="url" bind:value={address} placeholder="https://" spellcheck="false" />
      </label>
      {#if withText}
        <label>
          {$t("editor.linkText")}
          <input type="text" bind:value={text} placeholder={$t("editor.linkTextPlaceholder")} />
        </label>
      {/if}
      {#if error}<p class="compile-error" role="alert">{error}</p>{/if}
      <div class="link-dialog-actions">
        {#if canRemove}
          <button class="remove-content-button" type="button" onclick={onRemove}>{$t("editor.removeLink")}</button>
        {/if}
        <button class="secondary-button" type="button" onclick={onClose}>{$t("common.cancel")}</button>
        <button type="submit">{canRemove ? $t("editor.updateLink") : $t("editor.insertLinkButton")}</button>
      </div>
    </form>
  </div>
</div>
