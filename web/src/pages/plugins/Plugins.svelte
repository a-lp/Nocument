<script>
  import { confirmAction } from "../../confirm.js";
  import BackButton from "../../components/BackButton.svelte";
  import { onMount } from "svelte";
  import { apiFetch } from "../../api.js";
  import { t } from "../../i18n.js";
  import { pluginState, refreshPlugins } from "../../plugins.js";

  // Installed plugins: name, id, version, file, description and compatibilities, with the buttons to open them and
  // to remove their file; below, the files of the plugins folder that could not be loaded, with the error.
  export let navigate;

  let removingFile = "";
  let errorMessage = "";
  let isRefreshing = false;

  onMount(refresh);

  async function refresh() {
    isRefreshing = true;
    await refreshPlugins();
    isRefreshing = false;
  }

  // Deletes a plugin file after confirmation (all the plugins defined in it are removed).
  async function removeFile(file, names) {
    if (!(await confirmAction($t("plugins.confirmRemove", { file, plugins: names }), { title: $t("confirm.titles.removePlugin"), action: $t("confirm.actions.remove"), danger: true }))) {
      return;
    }
    removingFile = file;
    errorMessage = "";
    try {
      const response = await apiFetch(`/api/plugins/files/${encodeURIComponent(file)}`, { method: "DELETE" });
      if (!response.ok && response.status !== 404) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.error || $t("plugins.removeError"));
      }
      await refreshPlugins();
    } catch (error) {
      errorMessage = error.message;
    } finally {
      removingFile = "";
    }
  }

  // Names of the plugins defined in a file (a file can define more than one).
  function pluginsOfFile(file) {
    return $pluginState.plugins.filter((plugin) => plugin.file === file).map((plugin) => plugin.name).join(", ");
  }
</script>

<div class="page-heading">
  <div class="page-heading-top">
    <BackButton />
    <p>{$t("nav.plugins")}</p>
  </div>
  <h1>{$t("plugins.title")}</h1>
  <span>{$t("plugins.subtitle")}</span>
</div>

<div class="plugin-toolbar">
  <button class="secondary-button" type="button" disabled={isRefreshing} onclick={refresh}>{$t("plugins.refresh")}</button>
  {#if $pluginState.uploadEnabled}
    <a class="feature-button" href="/plugins/install" onclick={(event) => { event.preventDefault(); navigate("/plugins/install"); }}>{$t("nav.installPlugin")}</a>
  {/if}
</div>

{#if $pluginState.error}<p class="compile-error" role="alert">{$pluginState.error}</p>{/if}
{#if errorMessage}<p class="compile-error" role="alert">{errorMessage}</p>{/if}

{#if !$pluginState.loaded}
  <p class="status">{$t("plugins.loadingList")}</p>
{:else if !$pluginState.plugins.length}
  <p class="explore-empty">{$t("plugins.empty")}</p>
{/if}

<ul class="plugin-list">
  {#each $pluginState.plugins as plugin (plugin.id)}
    <li class="plugin-card">
      <header>
        <!-- The name opens the page of the plugin, with its interface. -->
        <h2>
          <a class="plugin-card-link" href={`/plugins/${plugin.id}`} onclick={(event) => { event.preventDefault(); navigate(`/plugins/${plugin.id}`); }}>{plugin.name}</a>
        </h2>
        <span class="plugin-meta">{$t("plugins.meta", { id: plugin.id, version: plugin.version })}</span>
        <span class="plugin-badges">
          {#if plugin.has_ui}<span class="plugin-chip">{$t("plugins.hasUi")}</span>{/if}
          {#if plugin.legacy}<span class="plugin-chip legacy">{$t("plugins.legacy")}</span>{/if}
        </span>
      </header>
      {#if plugin.description}<p class="plugin-description">{plugin.description}</p>{/if}
      <div class="plugin-compatibilities" aria-label={$t("plugins.compatibilities")}>
        {#each plugin.compatibilities as type (type)}<span class="plugin-chip">{$t(`contentTypes.${type}`)}</span>{/each}
      </div>
      <div class="explore-card-actions">
        <button class="secondary-button" type="button" onclick={() => navigate(`/plugins/${plugin.id}`)}>{$t("plugins.open")}</button>
        {#if $pluginState.uploadEnabled}
          <button class="remove-content-button" type="button" disabled={removingFile === plugin.file} onclick={() => removeFile(plugin.file, pluginsOfFile(plugin.file))}>
            {removingFile === plugin.file ? $t("plugins.removing") : $t("plugins.remove")}
          </button>
        {/if}
      </div>
    </li>
  {/each}
</ul>

{#if $pluginState.errors.length}
  <section class="plugin-errors" aria-labelledby="plugin-errors-title">
    <h2 id="plugin-errors-title">{$t("plugins.brokenTitle")}</h2>
    <span class="plugin-help">{$t("plugins.brokenHint")}</span>
    <ul>
      {#each $pluginState.errors as broken (broken.file)}
        <li class="plugin-card broken">
          <header><h3>{broken.file}</h3></header>
          <p class="compile-error">{broken.error}</p>
          {#if $pluginState.uploadEnabled}
            <div class="explore-card-actions">
              <button class="remove-content-button" type="button" disabled={removingFile === broken.file} onclick={() => removeFile(broken.file, "—")}>
                {removingFile === broken.file ? $t("plugins.removing") : $t("plugins.remove")}
              </button>
            </div>
          {/if}
        </li>
      {/each}
    </ul>
  </section>
{/if}
