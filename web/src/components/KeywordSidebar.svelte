<script>
  import BackButton from "./BackButton.svelte";
  import NavIcon from "./NavIcon.svelte";
  import { t } from "../i18n.js";
  import FileTypeIcon from "./FileTypeIcon.svelte";

  // Compiler sidebar: keyword list with the content assigned to each one, compile and save buttons.
  // contentLabels: content type -> label shown next to a keyword with a content.

  export let keywords = [];
  export let keywordValues = {};
  export let contentLabels = {};
  export let canCompile = false;
  export let isCompiling = false;
  export let compileError = "";
  export let canSave = false;
  export let canClose = false;
  export let onAddKeyword = () => {};
  export let onCompile = () => {};
  export let onSavePdf = () => {};
  export let onSaveWord = () => {};
  export let onClose = () => {};
  // Open in Builder: sends the document to the Builder (see documentTransfer.js).
  export let canOpenInBuilder = false;
  export let openInBuilderHint = "";
  export let onOpenInBuilder = () => {};
  export let onFocusKeyword = () => {};
  export let onFocusKeywordInPdf = () => {};
  export let onRemoveKeyword = () => {};

  let keywordInput;

  // Validates the new keyword (not empty, not a duplicate) and passes it to the parent with onAddKeyword.
  function addKeyword(event) {
    event.preventDefault();
    const keyword = keywordInput?.value.trim();
    if (!keyword || keywords.some((item) => item.toLowerCase() === keyword.toLowerCase())) {
      return;
    }

    onAddKeyword(keyword);
    keywordInput.value = "";
  }
</script>

<aside class="context-sidebar" aria-label={$t("keywords.sidebarLabel")}>
  <div class="context-sidebar-heading">
    <div class="sidebar-title">
      <BackButton onDark />
      <div>
        <p>{$t("keywords.eyebrow")}</p>
        <h2>{$t("keywords.title")}</h2>
      </div>
    </div>
    {#if canClose}
      <button class="close-document-button" type="button" title={$t("keywords.closeHint")} onclick={onClose}>
        {$t("common.newDocument")}
      </button>
    {/if}
  </div>
  <button class="compile-button" type="button" disabled={!canCompile || isCompiling} onclick={onCompile}>
    {isCompiling ? $t("keywords.compiling") : $t("keywords.compile")}
  </button>
  <div class="save-buttons">
    <button class="save-button save-pdf" type="button" disabled={!canSave || isCompiling} onclick={onSavePdf}>
      <FileTypeIcon type="pdf" />{$t("common.savePdf")}
    </button>
    <button class="save-button save-word" type="button" disabled={!canSave || isCompiling} onclick={onSaveWord}>
      <FileTypeIcon type="word" />{$t("common.saveWord")}
    </button>
  </div>
  <button class="preview-button" type="button" disabled={!canOpenInBuilder} title={openInBuilderHint} onclick={onOpenInBuilder}>
    <NavIcon name="builder" className="button-icon" />{$t("transfer.toBuilder")}
  </button>
  {#if compileError}
    <p class="compile-error" role="alert">{compileError}</p>
  {/if}
  <form class="keyword-form" onsubmit={addKeyword}>
    <input bind:this={keywordInput} type="text" placeholder={$t("keywords.newPlaceholder")} aria-label={$t("keywords.newLabel")} />
    <button class="add-keyword-button" type="submit">{$t("keywords.add")}</button>
  </form>
  {#if keywords.length}
    <ul class="keyword-list">
      {#each keywords as keyword}
        <li>
          <button class="keyword-item" type="button" onclick={() => onFocusKeyword(keyword)}>
            {keyword}
            {#if keywordValues[keyword]}
              <span class="keyword-type">{contentLabels[keywordValues[keyword].type]}</span>
            {/if}
          </button>
          <button
            class="focus-keyword"
            type="button"
            aria-label={$t("keywords.goTo", { keyword })}
            title={$t("keywords.goTo", { keyword })}
            onclick={() => onFocusKeywordInPdf(keyword)}
          >
            ◎
          </button>
          <button class="remove-keyword" type="button" aria-label={$t("keywords.remove", { keyword })} onclick={() => onRemoveKeyword(keyword)}>×</button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="empty-keywords">{$t("keywords.empty")}</p>
  {/if}
</aside>
