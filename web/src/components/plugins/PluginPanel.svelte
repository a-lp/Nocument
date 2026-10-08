<script>
  import { onMount } from "svelte";
  import { t } from "../../i18n.js";
  import { compileWithPlugin, loadParameters, pluginState, refreshPlugins, rememberValues, savedValues } from "../../plugins.js";
  import PluginForm from "./PluginForm.svelte";

  // "From plugin" section of the content modal: the plugins compatible with contentType, the form of the chosen
  // plugin's parameters and the button that asks it for the data. onContent(content) receives the content created
  // by the plugin (JSON of the contents), which the modal puts in its fields. Hidden if no plugin is compatible.
  export let contentType;
  export let disabled = false;
  export let onContent = () => {};

  let pluginId = "";
  let parameters = [];
  let values = {};
  let isLoadingParameters = false;
  let isCompiling = false;
  let errorMessage = "";
  let loadedNotice = false;
  // Identifies the last parameters request: answers for a plugin or type no longer chosen are ignored.
  let requestToken = 0;

  onMount(refreshPlugins);

  $: compatible = $pluginState.plugins.filter((plugin) => plugin.compatibilities.includes(contentType));
  // The chosen plugin stays if it supports the new type, otherwise the first compatible one is chosen.
  $: if (!compatible.some((plugin) => plugin.id === pluginId)) {
    pluginId = compatible[0]?.id ?? "";
  }
  $: selectParameters(pluginId, contentType);

  // Loads the parameters of the chosen plugin for the content type.
  async function selectParameters(id, type) {
    const token = ++requestToken;
    parameters = [];
    values = {};
    errorMessage = "";
    loadedNotice = false;
    if (!id) {
      return;
    }
    isLoadingParameters = true;
    try {
      const loaded = await loadParameters(id, type, $t("plugins.parametersError"));
      if (token === requestToken) {
        parameters = loaded;
        values = savedValues(id, type, loaded);
      }
    } catch (error) {
      if (token === requestToken) {
        errorMessage = error.message;
      }
    } finally {
      if (token === requestToken) {
        isLoadingParameters = false;
      }
    }
  }

  // Asks the plugin for the content and passes it to the modal.
  async function load() {
    isCompiling = true;
    errorMessage = "";
    loadedNotice = false;
    // Remembered also if the request fails (e.g. server not reachable), so they need not be written again.
    rememberValues(pluginId, contentType, parameters, values);
    try {
      onContent(await compileWithPlugin(pluginId, contentType, values, $t("plugins.compileError")));
      loadedNotice = true;
    } catch (error) {
      errorMessage = error.message;
    } finally {
      isCompiling = false;
    }
  }
</script>

{#if compatible.length}
  <details class="plugin-panel">
    <summary>{$t("plugins.fromPlugin", { count: compatible.length })}</summary>
    <div class="plugin-panel-body">
      <span class="plugin-help">{$t("plugins.fromPluginHint")}</span>
      <label for="plugin-choice">
        {$t("plugins.plugin")}
        <select id="plugin-choice" bind:value={pluginId} disabled={disabled || isCompiling}>
          {#each compatible as plugin (plugin.id)}
            <option value={plugin.id}>{plugin.name}</option>
          {/each}
        </select>
      </label>
      {#if isLoadingParameters}
        <p class="plugin-help">{$t("plugins.loadingParameters")}</p>
      {:else}
        <PluginForm {parameters} bind:values idPrefix={`plugin-${contentType}`} disabled={disabled || isCompiling} />
      {/if}
      {#if errorMessage}<p class="compile-error" role="alert">{errorMessage}</p>{/if}
      {#if loadedNotice}<p class="settings-saved" role="status">{$t("plugins.loaded")}</p>{/if}
      <div class="plugin-panel-actions">
        <button class="secondary-button" type="button" disabled={disabled || isCompiling || isLoadingParameters || !pluginId} onclick={load}>
          {isCompiling ? $t("plugins.loading") : $t("plugins.load")}
        </button>
      </div>
    </div>
  </details>
{/if}
