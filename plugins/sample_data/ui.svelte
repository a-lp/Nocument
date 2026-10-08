<script>
  // Interface of the "Sample data" package: a small report playground that shows what a plugin interface can do.
  // - api.compile creates the contents with the plugin (here a table and a bar chart, together);
  // - components.ContentSheet previews them as Nocument does;
  // - storage keeps presets and a counter in this browser (separate from the other plugins' data);
  // - the colors are the variables of the Nocument theme, so the interface follows light, dark and custom themes.
  let { plugin, api, storage, language, components } = $props();

  const TEXT = {
    en: {
      intro: "Build a sample sales report: a table of products and a bar chart, previewed as they will look in a document.",
      products: "Products", chart: "Chart color", total: "Total row", caption: "Caption", width: "Chart width (cm)",
      generate: "Generate report", generating: "Generating...", presets: "Presets saved in this browser",
      presetName: "Preset name", save: "Save preset", load: "Load", remove: "Delete", noPresets: "No presets yet.",
      count: (n) => `Reports generated in this browser: ${n}`, saveFailed: "This browser cannot save data (private browsing or storage full)."
    },
    it: {
      intro: "Crea un report di vendite di prova: una tabella di prodotti e un grafico a barre, in anteprima come appariranno in un documento.",
      products: "Prodotti", chart: "Colore del grafico", total: "Riga del totale", caption: "Didascalia", width: "Larghezza del grafico (cm)",
      generate: "Genera report", generating: "Generazione...", presets: "Preimpostazioni salvate in questo browser",
      presetName: "Nome della preimpostazione", save: "Salva preimpostazione", load: "Carica", remove: "Elimina", noPresets: "Nessuna preimpostazione.",
      count: (n) => `Report generati in questo browser: ${n}`, saveFailed: "Questo browser non può salvare dati (navigazione privata o spazio esaurito)."
    }
  };
  const text = TEXT[language] ?? TEXT.en;
  // Colors offered by the plugin itself (options of its "color" parameter for images).
  const colors = plugin.parameters.image?.find((parameter) => parameter.name === "color")?.options ?? [];

  let settings = $state(storage.get("settings", { rows: 4, color: colors[0]?.value ?? "teal", total: true, caption: "Sales by product", width: 12 }));
  let presets = $state(storage.get("presets", []));
  let generated = $state(storage.get("generated", 0));
  let presetName = $state("");
  let contents = $state([]);
  let isBusy = $state(false);
  let error = $state("");
  let notice = $state("");

  function remember(key, value) {
    if (!storage.set(key, value)) {
      notice = text.saveFailed;
    }
  }

  async function generate() {
    isBusy = true;
    error = "";
    remember("settings", $state.snapshot(settings));
    try {
      // Both contents are asked to the plugin at the same time.
      const [table, chart] = await Promise.all([
        api.compile("table", { rows: settings.rows, total: settings.total, caption: settings.caption }),
        api.compile("image", { bars: settings.rows, color: settings.color, width: settings.width })
      ]);
      contents = [table, chart];
      generated += 1;
      remember("generated", generated);
    } catch (failure) {
      error = failure.message;
    } finally {
      isBusy = false;
    }
  }

  function savePreset() {
    const name = presetName.trim();
    if (!name) {
      return;
    }
    presets = [...presets.filter((preset) => preset.name !== name), { name, settings: $state.snapshot(settings) }];
    remember("presets", presets);
    presetName = "";
  }

  function deletePreset(name) {
    presets = presets.filter((preset) => preset.name !== name);
    remember("presets", presets);
  }
</script>

<div class="playground">
  <p class="intro">{text.intro}</p>

  <div class="fields">
    <label>{text.products}<input type="number" min="1" max="8" bind:value={settings.rows} /></label>
    <label>
      {text.chart}
      <select bind:value={settings.color}>
        {#each colors as color (color.value)}<option value={color.value}>{color.label}</option>{/each}
      </select>
    </label>
    <label>{text.width}<input type="number" min="1" max="30" bind:value={settings.width} /></label>
    <label>{text.caption}<input type="text" bind:value={settings.caption} /></label>
    <label class="check"><input type="checkbox" bind:checked={settings.total} />{text.total}</label>
  </div>

  <div class="actions">
    <button type="button" disabled={isBusy} onclick={generate}>{isBusy ? text.generating : text.generate}</button>
    <span class="muted">{text.count(generated)}</span>
  </div>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  {#if notice}<p class="muted" role="status">{notice}</p>{/if}

  {#if contents.length}
    <div class="preview">
      <components.ContentSheet {contents} readonly compact />
    </div>
  {/if}

  <section class="presets">
    <h3>{text.presets}</h3>
    {#if presets.length}
      <ul>
        {#each presets as preset (preset.name)}
          <li>
            <span>{preset.name}</span>
            <button type="button" class="link" onclick={() => (settings = { ...preset.settings })}>{text.load}</button>
            <button type="button" class="link danger" onclick={() => deletePreset(preset.name)}>{text.remove}</button>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">{text.noPresets}</p>
    {/if}
    <div class="save">
      <input type="text" placeholder={text.presetName} aria-label={text.presetName} bind:value={presetName} />
      <button type="button" class="secondary" disabled={!presetName.trim()} onclick={savePreset}>{text.save}</button>
    </div>
  </section>
</div>

<style>
  .playground {
    display: grid;
    gap: 1rem;
  }

  .intro,
  .muted {
    margin: 0;
    color: var(--text-muted);
  }

  .fields {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
    gap: 0.75rem 1rem;
  }

  label {
    display: grid;
    gap: 0.3rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  label.check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    align-self: end;
  }

  input:not([type="checkbox"]),
  select {
    box-sizing: border-box;
    width: 100%;
    min-width: 0;
    padding: 0.5rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: 0.3rem;
    font: inherit;
  }

  .save input {
    flex: 1 1 14rem;
    width: auto;
  }

  .actions,
  .save {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
  }

  .secondary {
    border: 1px solid var(--accent-border);
    color: var(--accent-text);
    background: transparent;
  }

  .link {
    padding: 0.1rem 0.4rem;
    color: var(--accent-text);
    background: transparent;
    font-weight: 500;
  }

  .link.danger {
    color: var(--danger-text);
  }

  .error {
    margin: 0;
    color: var(--danger-text);
  }

  .preview {
    max-height: 520px;
    overflow: auto;
    padding: 1rem;
    border-radius: 0.4rem;
    background: var(--surface-sunken);
  }

  .presets {
    display: grid;
    gap: 0.5rem;
    padding: 1rem;
    border: 1px solid var(--border-subtle);
    border-radius: 0.4rem;
    background: var(--surface);
  }

  h3 {
    margin: 0;
    font-size: 1rem;
  }

  ul {
    display: grid;
    gap: 0.25rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  li span {
    flex: 1;
  }
</style>
