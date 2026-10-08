<script>
  import { onMount } from "svelte";
  import { apiFetch } from "../../api.js";
  import { t } from "../../i18n.js";
  import { sanitizeDocumentHtml } from "../../htmlSanitizer.js";

  // README of a plugin package (Markdown), rendered as HTML and sanitized; the Markdown renderer is loaded only here.
  export let plugin;

  let html = "";
  let errorMessage = "";
  let isLoading = true;

  onMount(async () => {
    try {
      const response = await apiFetch(`/api/plugins/${encodeURIComponent(plugin.id)}/readme`);
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.error || $t("plugins.readmeError"));
      }
      const [{ marked }, markdown] = await Promise.all([import("marked"), response.text()]);
      html = sanitizeDocumentHtml(await marked.parse(markdown, { gfm: true }));
    } catch (error) {
      errorMessage = error.message;
    } finally {
      isLoading = false;
    }
  });
</script>

{#if isLoading}
  <p class="plugin-help" role="status">{$t("plugins.readmeLoading")}</p>
{:else if errorMessage}
  <p class="compile-error" role="alert">{errorMessage}</p>
{:else}
  <article class="plugin-readme">{@html html}</article>
{/if}
