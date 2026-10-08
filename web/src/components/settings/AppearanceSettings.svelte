<script>
  import { confirmAction } from "../../confirm.js";
  import { onDestroy } from "svelte";
  import { t } from "../../i18n.js";
  import {
    MODES, TOKEN_GROUPS, appearance, baseColors, deleteTheme, duplicateTheme, isColor, previewThemeId, resolveTheme,
    themes, updateTheme
  } from "../../theme.js";

  // Appearance section of Settings: mode (system, light, dark), theme of each mode and the custom themes, whose every
  // color can be changed. The theme being edited is shown on the whole web app while its editor is open.

  // Colors shown in the preview strip of a theme.
  const SWATCHES = ["bg", "surface", "sidebar-bg", "accent", "text", "danger"];

  // Id of the custom theme being edited, null when the editor is closed.
  let editingId = null;
  let importInput;
  let importError = "";

  $: editing = editingId ? resolveTheme($appearance, editingId) : null;
  $: previewThemeId.set(editingId);

  onDestroy(() => previewThemeId.set(null));

  function themeName(theme) {
    return theme.builtIn ? $t(`settings.appearance.builtIn.${theme.id}`) : theme.name;
  }

  // E.g. "Light, built-in, in use".
  function themeDetails(theme) {
    return [
      $t(`settings.appearance.bases.${theme.base}`),
      theme.builtIn && $t("settings.appearance.builtInLabel"),
      isInUse(theme) && $t("settings.appearance.inUse")
    ].filter(Boolean).join(", ");
  }

  function setMode(mode) {
    appearance.update((value) => ({ ...value, mode }));
  }

  // Theme of a mode: "lightTheme" or "darkTheme".
  function setModeTheme(key, id) {
    appearance.update((value) => ({ ...value, [key]: id }));
  }

  function isInUse(theme) {
    return $appearance.lightTheme === theme.id || $appearance.darkTheme === theme.id;
  }

  function duplicate(theme) {
    editingId = duplicateTheme(theme.id, $t("settings.appearance.copyOf", { name: themeName(theme) }));
  }

  async function remove(theme) {
    if (!(await confirmAction($t("settings.appearance.confirmDelete", { name: theme.name }), { title: $t("confirm.titles.deleteTheme"), action: $t("confirm.actions.delete"), danger: true }))) {
      return;
    }
    if (editingId === theme.id) {
      editingId = null;
    }
    deleteTheme(theme.id);
  }

  // A color typed in the text field is applied only when complete (#rrggbb).
  function setColor(token, value) {
    const color = value.trim().toLowerCase();
    if (isColor(color)) {
      updateTheme(editingId, { colors: { [token]: color } });
    }
  }

  // The base decides in which mode the theme can be used; a theme no longer matching a mode is removed from it.
  function setBase(base) {
    updateTheme(editingId, { base });
    appearance.update((value) => ({
      ...value,
      lightTheme: base === "dark" && value.lightTheme === editingId ? "light" : value.lightTheme,
      darkTheme: base === "light" && value.darkTheme === editingId ? "dark" : value.darkTheme
    }));
  }

  // Downloads the custom theme as a JSON file, to share it or import it in another browser.
  function exportTheme(theme) {
    const resolved = resolveTheme($appearance, theme.id);
    const blob = new Blob(
      [JSON.stringify({ name: theme.name, base: resolved.base, colors: resolved.colors }, null, 2)],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${theme.name.replace(/[\\/:*?"<>|]+/g, " ").trim() || "theme"}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url));
  }

  // Imports a theme exported with exportTheme as a new custom theme; unknown or invalid colors are ignored.
  async function importTheme(event) {
    const [file] = event.target.files;
    event.target.value = "";
    importError = "";
    if (!file) {
      return;
    }
    try {
      const data = JSON.parse(await file.text());
      if (!data || typeof data.colors !== "object") {
        throw new Error();
      }
      const base = data.base === "dark" ? "dark" : "light";
      const id = duplicateTheme(base, typeof data.name === "string" && data.name.trim() ? data.name.trim() : file.name.replace(/\.json$/i, ""));
      const colors = Object.fromEntries(
        Object.entries(data.colors).filter(([token, color]) => token in baseColors(base) && isColor(String(color).toLowerCase()))
          .map(([token, color]) => [token, String(color).toLowerCase()])
      );
      updateTheme(id, { colors });
      editingId = id;
    } catch {
      importError = $t("settings.appearance.importError");
    }
  }
</script>

<section class="settings-section" aria-labelledby="settings-appearance-title">
  <div class="settings-section-heading">
    <h2 id="settings-appearance-title">{$t("settings.appearance.title")}</h2>
    <span>{$t("settings.appearance.description")}</span>
  </div>

  <div class="settings-options appearance-modes" role="radiogroup" aria-label={$t("settings.appearance.mode")}>
    {#each MODES as mode (mode)}
      <label class="settings-option" class:selected={$appearance.mode === mode}>
        <input type="radio" name="appearance-mode" value={mode} checked={$appearance.mode === mode} onchange={() => setMode(mode)} />
        <span class="settings-option-name">{$t(`settings.appearance.modes.${mode}`)}</span>
        <span class="settings-option-hint">{$t(`settings.appearance.modeHints.${mode}`)}</span>
      </label>
    {/each}
  </div>

  <div class="appearance-mode-themes">
    {#each [["lightTheme", "light"], ["darkTheme", "dark"]] as [key, base] (key)}
      <label>
        {$t(`settings.appearance.${key}`)}
        <select value={$appearance[key]} onchange={(event) => setModeTheme(key, event.target.value)}>
          {#each $themes.filter((theme) => theme.base === base) as theme (theme.id)}
            <option value={theme.id}>{themeName(theme)}</option>
          {/each}
        </select>
      </label>
    {/each}
  </div>

  <div class="appearance-themes-heading">
    <h3>{$t("settings.appearance.themes")}</h3>
    <input bind:this={importInput} type="file" accept=".json,application/json" hidden onchange={importTheme} />
    <button class="secondary-button" type="button" onclick={() => importInput?.click()}>{$t("settings.appearance.import")}</button>
  </div>
  {#if importError}<p class="compile-error" role="alert">{importError}</p>{/if}
  <ul class="theme-list">
    {#each $themes as theme (theme.id)}
      {@const colors = resolveTheme($appearance, theme.id).colors}
      <li class="theme-row" class:editing={theme.id === editingId}>
        <span class="theme-swatches" aria-hidden="true">
          {#each SWATCHES as token (token)}<span style={`background: ${colors[token]}`}></span>{/each}
        </span>
        <span class="theme-name">
          {themeName(theme)}
          <small>{themeDetails(theme)}</small>
        </span>
        <span class="theme-actions">
          <button class="secondary-button" type="button" onclick={() => duplicate(theme)}>{$t("settings.appearance.duplicate")}</button>
          {#if !theme.builtIn}
            <button class="secondary-button" type="button" aria-pressed={theme.id === editingId} onclick={() => (editingId = theme.id === editingId ? null : theme.id)}>
              {theme.id === editingId ? $t("settings.appearance.done") : $t("common.edit")}
            </button>
            <button class="icon-button" type="button" title={$t("settings.appearance.export")} aria-label={$t("settings.appearance.exportLabel", { name: theme.name })} onclick={() => exportTheme(theme)}>⤓</button>
            <button class="icon-button remove-row" type="button" title={$t("common.delete")} aria-label={$t("settings.appearance.deleteLabel", { name: theme.name })} onclick={() => remove(theme)}>🗑</button>
          {/if}
        </span>
      </li>
    {/each}
  </ul>
  <p class="settings-option-hint">{$t("settings.appearance.builtInHint")}</p>

  {#if editing}
    <div class="theme-editor" aria-label={$t("settings.appearance.editorLabel", { name: editing.name })} role="group">
      <div class="theme-editor-heading">
        <label>
          {$t("settings.appearance.name")}
          <input type="text" value={editing.name} maxlength="60" oninput={(event) => event.target.value.trim() && updateTheme(editingId, { name: event.target.value })} />
        </label>
        <label>
          {$t("settings.appearance.base")}
          <select value={editing.base} onchange={(event) => setBase(event.target.value)}>
            <option value="light">{$t("settings.appearance.bases.light")}</option>
            <option value="dark">{$t("settings.appearance.bases.dark")}</option>
          </select>
        </label>
      </div>
      <p class="settings-option-hint">{$t("settings.appearance.previewHint")}</p>
      {#each TOKEN_GROUPS as group (group.id)}
        <details class="theme-token-group" open={group.id === "surfaces"}>
          <summary>{$t(`settings.appearance.groups.${group.id}`)}</summary>
          <div class="theme-tokens">
            {#each group.tokens as token (token)}
              {@const value = editing.colors[token]}
              {@const original = baseColors(editing.base)[token]}
              <div class="theme-token">
                <label for={`token-${token}`}>{$t(`settings.appearance.tokens.${token}`)}</label>
                <input id={`token-${token}`} type="color" {value} oninput={(event) => setColor(token, event.target.value)} />
                <input
                  class="theme-token-hex"
                  type="text"
                  {value}
                  maxlength="7"
                  spellcheck="false"
                  aria-label={$t("settings.appearance.hexLabel", { token: $t(`settings.appearance.tokens.${token}`) })}
                  oninput={(event) => setColor(token, event.target.value)}
                />
                <button
                  class="icon-button"
                  type="button"
                  title={$t("settings.appearance.reset", { color: original })}
                  aria-label={$t("settings.appearance.resetLabel", { token: $t(`settings.appearance.tokens.${token}`) })}
                  disabled={value === original}
                  onclick={() => updateTheme(editingId, { colors: { [token]: original } })}
                >↺</button>
              </div>
            {/each}
          </div>
        </details>
      {/each}
    </div>
  {/if}
</section>
