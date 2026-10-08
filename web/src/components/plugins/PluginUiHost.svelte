<script>
  import { onDestroy, tick } from "svelte";
  import { apiFetch } from "../../api.js";
  import { language, t } from "../../i18n.js";
  import { compileWithPlugin, loadParameters } from "../../plugins.js";
  import { createPluginStorage } from "../../plugins/pluginStorage.js";
  import ContentSheet from "../content/ContentSheet.svelte";

  // Custom interface of a plugin package (ui.svelte), compiled and mounted when the plugin page opens; the Svelte
  // compiler and the runtime are loaded only now (see plugins/pluginRuntime.js). The interface receives as props:
  // - plugin: { id, name, description, version, file (package), compatibilities, parameters: { <type>: [...] } };
  // - api: { parameters(type), compile(type, values) }: the parameters of the plugin and the content it creates
  //   (JSON of the contents, as in the Builder);
  // - storage: data of the package saved in the browser (see pluginStorage.js);
  // - language: language of the web app ("en", "it"); the interface is mounted again when it changes;
  // - components: { ContentSheet } of the web app, to preview contents as the rest of the app does.
  export let plugin;

  let target;
  let status = "loading";
  let errorMessage = "";
  let errorPosition = null;
  let destroyInterface = null;
  // Identifies the last mount: a mount finished after a newer one (e.g. language changed) is discarded.
  let mountToken = 0;

  const api = Object.freeze({
    parameters: (type) => loadParameters(plugin.id, type, $t("plugins.parametersError")),
    compile: (type, values = {}) => compileWithPlugin(plugin.id, type, values, $t("plugins.compileError"))
  });
  const storage = createPluginStorage(plugin.file);

  $: start($language);

  onDestroy(() => destroyInterface?.());

  async function start(currentLanguage) {
    const token = ++mountToken;
    destroyInterface?.();
    destroyInterface = null;
    status = "loading";
    errorMessage = "";
    errorPosition = null;
    try {
      const [runtime, source] = await Promise.all([import("../../plugins/pluginRuntime.js"), fetchSource()]);
      const Component = await runtime.loadPluginComponent(source, plugin.file);
      if (token !== mountToken) {
        return;
      }
      status = "ready";
      await tick();
      destroyInterface = runtime.mountPluginComponent(Component, target, {
        plugin,
        api,
        storage,
        language: currentLanguage,
        components: { ContentSheet }
      });
    } catch (error) {
      if (token !== mountToken) {
        return;
      }
      console.error(`Plugin interface of ${plugin.file}`, error);
      status = "error";
      errorMessage = error.message;
      errorPosition = error.position ?? null;
    }
  }

  async function fetchSource() {
    const response = await apiFetch(`/api/plugins/${encodeURIComponent(plugin.id)}/ui`);
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.error || $t("plugins.uiLoadError"));
    }
    return response.text();
  }
</script>

<!-- The interface is mounted in this element; status and errors are outside it. -->
{#if status === "loading"}<p class="plugin-help" role="status">{$t("plugins.uiLoading")}</p>{/if}
{#if status === "error"}
  <div class="compile-error plugin-ui-error" role="alert">
    <strong>{$t("plugins.uiError")}</strong>
    <span>{errorMessage}</span>
    {#if errorPosition}<span>{$t("plugins.uiErrorPosition", errorPosition)}</span>{/if}
  </div>
{/if}
<div bind:this={target} class="plugin-ui" class:hidden={status !== "ready"}></div>
