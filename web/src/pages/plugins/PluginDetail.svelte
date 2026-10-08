<script>
  import BackButton from "../../components/BackButton.svelte";
  import { onMount } from "svelte";
  import { apiFetch } from "../../api.js";
  import { t } from "../../i18n.js";
  import { compileWithPlugin, rememberValues, savedValues } from "../../plugins.js";
  import ContentSheet from "../../components/content/ContentSheet.svelte";
  import PluginForm from "../../components/plugins/PluginForm.svelte";
  import PluginReadme from "../../components/plugins/PluginReadme.svelte";
  import PluginUiHost from "../../components/plugins/PluginUiHost.svelte";

  // Page of a plugin, opened from the list of the installed plugins, with three tabs:
  // - Interface: the custom interface of its package (ui.svelte), compiled and shown here (PluginUiHost);
  // - Try it: for each content type it supports, the form of its parameters with a preview of the content;
  // - Guide: the README of its package.
  // Loose scripts (legacy plugins, without package) only have Try it.
  export let pluginId;
  export let navigate;

  // { id, name, description, version, file, compatibilities, parameters: { type: [...] } }; null while loading.
  let plugin = null;
  let errorMessage = "";
  let contentType = "";
  let values = {};
  let preview = null;
  let previewError = "";
  let isCompiling = false;
  // Tab shown: "ui", "try" or "readme" (the interface first, when the package has one).
  let tab = "try";

  onMount(load);

  async function load() {
    errorMessage = "";
    try {
      const response = await apiFetch(`/api/plugins/${encodeURIComponent(pluginId)}`);
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("plugins.loadError"));
      }
      plugin = data;
      tab = data.has_ui ? "ui" : "try";
      chooseType(data.compatibilities[0]);
    } catch (error) {
      errorMessage = error.message;
    }
  }

  // Shows the form of another content type, with the values last used (or the plugin's initial ones).
  function chooseType(type) {
    contentType = type;
    values = savedValues(plugin.id, type, plugin.parameters[type] ?? []);
    preview = null;
    previewError = "";
  }

  // Asks the plugin for the content and shows it.
  async function tryPlugin(event) {
    event.preventDefault();
    isCompiling = true;
    previewError = "";
    // Remembered also if the request fails (e.g. server not reachable), so they need not be written again.
    rememberValues(plugin.id, contentType, plugin.parameters[contentType] ?? [], values);
    try {
      preview = await compileWithPlugin(plugin.id, contentType, values, $t("plugins.compileError"));
    } catch (error) {
      preview = null;
      previewError = error.message;
    } finally {
      isCompiling = false;
    }
  }
</script>

<div class="page-heading">
  <div class="page-heading-top">
    <BackButton />
    <p>{$t("nav.plugins")}</p>
  </div>
  <h1>{plugin?.name ?? pluginId}</h1>
  {#if plugin}<span>{plugin.description}</span>{/if}
</div>

{#if errorMessage}
  <p class="compile-error" role="alert">{errorMessage}</p>
  <button class="secondary-button" type="button" onclick={() => navigate("/plugins")}>{$t("plugins.backToList")}</button>
{:else if !plugin}
  <p class="status">{$t("plugins.loadingList")}</p>
{:else}
  <p class="plugin-meta">
    {$t("plugins.meta", { id: plugin.id, version: plugin.version })} ·
    <code>{plugin.legacy ? plugin.file : `plugins/${plugin.file}/`}</code>
  </p>
  {#if plugin.legacy}<p class="table-warning" role="status">{$t("plugins.legacyHint")}</p>{/if}

  <div class="content-type-list plugin-tabs" role="tablist" aria-label={$t("plugins.sections")}>
    {#if plugin.has_ui}
      <button class:active={tab === "ui"} type="button" role="tab" aria-selected={tab === "ui"} onclick={() => (tab = "ui")}>{$t("plugins.tabs.ui")}</button>
    {/if}
    <button class:active={tab === "try"} type="button" role="tab" aria-selected={tab === "try"} onclick={() => (tab = "try")}>{$t("plugins.tabs.try")}</button>
    {#if plugin.has_readme}
      <button class:active={tab === "readme"} type="button" role="tab" aria-selected={tab === "readme"} onclick={() => (tab = "readme")}>{$t("plugins.tabs.readme")}</button>
    {/if}
  </div>

  {#if tab === "ui"}
    <section class="plugin-ui-section" aria-label={$t("plugins.tabs.ui")}>
      <PluginUiHost {plugin} />
    </section>
  {:else if tab === "readme"}
    <section aria-label={$t("plugins.tabs.readme")}>
      <PluginReadme {plugin} />
    </section>
  {:else}
  <section class="plugin-try" aria-labelledby="plugin-try-title">
    <h2 id="plugin-try-title">{$t("plugins.tryTitle")}</h2>
    <span class="plugin-help">{$t("plugins.tryHint")}</span>
    <div class="content-type-list" role="tablist" aria-label={$t("plugins.compatibilities")}>
      {#each plugin.compatibilities as type (type)}
        <button class:active={contentType === type} type="button" role="tab" aria-selected={contentType === type} onclick={() => chooseType(type)}>{$t(`contentTypes.${type}`)}</button>
      {/each}
    </div>
    <form class="content-form" onsubmit={tryPlugin}>
      {#key contentType}
        {#if plugin.parameters[contentType]?.length}
          <PluginForm parameters={plugin.parameters[contentType]} bind:values idPrefix="try" disabled={isCompiling} />
        {:else}
          <span class="plugin-help">{$t("plugins.noParameters")}</span>
        {/if}
      {/key}
      {#if previewError}<p class="compile-error" role="alert">{previewError}</p>{/if}
      <div class="content-actions">
        <button class="insert-content-button" type="submit" disabled={isCompiling}>{isCompiling ? $t("plugins.loading") : $t("plugins.try")}</button>
      </div>
    </form>
    {#if preview}
      <div class="import-group-preview plugin-preview" tabindex="0" role="region" aria-label={$t("plugins.preview")}>
        <ContentSheet contents={[preview]} readonly compact />
      </div>
    {/if}
  </section>
  {/if}
{/if}
