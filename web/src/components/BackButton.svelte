<script>
  import { t } from "../i18n.js";
  import { canGoBack, goBack } from "../history.js";

  // Arrow returning to the page opened before (the browser's back), shown only when there is one in the web app.
  // onDark: colors for the dark secondary sidebars.
  export let onDark = false;
</script>

{#if $canGoBack}
  <button class="back-button" class:on-dark={onDark} type="button" title={$t("common.back")} aria-label={$t("common.back")} onclick={goBack}>
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 18l-6-6 6-6" /></svg>
  </button>
{/if}
