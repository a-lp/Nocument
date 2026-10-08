<script>
  import { confirmAction } from "../../confirm.js";
  import BackButton from "../../components/BackButton.svelte";
  import { onMount } from "svelte";
  import { apiFetch } from "../../api.js";
  import { t } from "../../i18n.js";
  import { pluginState, refreshPlugins } from "../../plugins.js";

  // Installation of a plugin package: a .zip with plugin.py, ui.svelte and README.md, or the three files together,
  // dropped on the area or chosen with the "+" button. The backend checks it (files, syntax, loading, plugin ids) and
  // installs it in a folder of its own, named after the plugin; an installed package is replaced after confirmation.
  export let navigate;

  let fileInput;
  let isDragging = false;
  let isUploading = false;
  let errorMessage = "";
  // Plugins defined by the last installed package.
  let installed = [];
  const PACKAGE_FILES = ["plugin.py", "ui.svelte", "README.md"];

  onMount(refreshPlugins);

  // Sends the package to the backend; with replace it overwrites the installed package with the same name.
  async function upload(files, replace = false) {
    const names = files.map((file) => file.name);
    const isZip = files.length === 1 && names[0].toLowerCase().endsWith(".zip");
    if (!isZip && !PACKAGE_FILES.every((name) => names.includes(name))) {
      errorMessage = $t("plugins.invalidFile");
      return;
    }
    isUploading = true;
    errorMessage = "";
    installed = [];
    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }
      if (replace) {
        formData.append("replace", "true");
      }
      const response = await apiFetch("/api/plugins", { method: "POST", body: formData });
      const data = await response.json().catch(() => null);
      if (response.status === 409 && !replace) {
        isUploading = false;
        if (await confirmAction($t("plugins.confirmReplace", { file: data?.file ?? names[0] }), { title: $t("confirm.titles.replacePlugin"), action: $t("confirm.actions.replace") })) {
          await upload(files, true);
        }
        return;
      }
      if (!response.ok) {
        throw new Error(data?.error || $t("plugins.installError"));
      }
      installed = data.plugins;
      await refreshPlugins();
    } catch (error) {
      errorMessage = error.message;
    } finally {
      isUploading = false;
    }
  }

  function handleFileChange(event) {
    const files = [...event.target.files];
    event.target.value = "";
    if (files.length) {
      upload(files);
    }
  }

  function handleDragOver(event) {
    if (!event.dataTransfer?.types.includes("Files")) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    isDragging = true;
  }

  function handleDragLeave(event) {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      isDragging = false;
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    isDragging = false;
    const files = [...(event.dataTransfer?.files ?? [])];
    if (files.length && !isUploading) {
      upload(files);
    }
  }
</script>

<div class="page-heading">
  <div class="page-heading-top">
    <BackButton />
    <p>{$t("nav.plugins")}</p>
  </div>
  <h1>{$t("nav.installPlugin")}</h1>
  <span>{$t("plugins.installSubtitle")}</span>
</div>

{#if $pluginState.loaded && !$pluginState.uploadEnabled}
  <p class="table-warning" role="status">{$t("errors.pluginUploadDisabled")}</p>
{:else}
  <div
    class="plugin-drop-area"
    class:dragging={isDragging}
    role="region"
    aria-label={$t("plugins.dropArea")}
    aria-busy={isUploading}
    ondragenter={handleDragOver}
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    ondrop={handleDrop}
  >
    <input bind:this={fileInput} type="file" accept=".zip,.py,.svelte,.md,application/zip" multiple onchange={handleFileChange} hidden />
    <button class="insert-button plugin-add-button" type="button" aria-label={$t("plugins.choose")} title={$t("plugins.choose")} disabled={isUploading} onclick={() => fileInput?.click()}>+</button>
    <span>{isUploading ? $t("plugins.installing") : $t("plugins.dropHint")}</span>
  </div>
{/if}

{#if errorMessage}<p class="compile-error" role="alert">{errorMessage}</p>{/if}
{#if installed.length}
  <div class="settings-saved" role="status">
    {$t("plugins.installed", { count: installed.length })}
    {#each installed as plugin (plugin.id)}
      <a class="plugin-link" href={`/plugins/${plugin.id}`} onclick={(event) => { event.preventDefault(); navigate(`/plugins/${plugin.id}`); }}>{plugin.name}</a>
    {/each}
  </div>
{/if}

<section class="plugin-guide" aria-labelledby="plugin-guide-title">
  <h2 id="plugin-guide-title">{$t("plugins.guideTitle")}</h2>
  <span class="plugin-help">{$t("plugins.guideText")}</span>
  <pre><code>{`customers/
  plugin.py     # the plugin(s), in Python
  ui.svelte     # its interface, shown on the plugin page
  README.md     # what it does and how to use it`}</code></pre>
  <span class="plugin-help">{$t("plugins.guideScript")}</span>
  <pre><code>{`from src.plugins import IPlugin, PluginParameter, TABLE

class CustomersPlugin(IPlugin):
    id = "customers"
    name = "Customers"

    def parameters(self, content_type):
        return [PluginParameter("city", "City", required=True)]

    def compile_table(self, values):
        rows = [["Name", "City"], ["ACME", values["city"]]]
        return self.table(rows, caption="Customers")`}</code></pre>
  <span class="plugin-help">{$t("plugins.guideUi")}</span>
  <pre><code>{`<script>
  // plugin, api, storage, language and components are given by Nocument.
  let { plugin, api, storage, components } = $props();
  let city = $state(storage.get("city", "Rome"));
  let content = $state(null);

  async function load() {
    storage.set("city", city);   // remembered in this browser
    content = await api.compile("table", { city });
  }
</script>

<input bind:value={city} />
<button onclick={load}>Preview</button>
{#if content}<components.ContentSheet contents={[content]} readonly compact />{/if}`}</code></pre>
</section>
