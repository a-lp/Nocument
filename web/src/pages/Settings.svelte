<script>
  import BackButton from "../components/BackButton.svelte";
  import { onMount } from "svelte";
  import { apiFetch } from "../api.js";
  import { LANGUAGES, language, t } from "../i18n.js";
  import AppearanceSettings from "../components/settings/AppearanceSettings.svelte";

  // Configuration of the web app, one section per setting. The language and the appearance (mode and color themes,
  // see AppearanceSettings) are preferences of this browser and apply at once; the PDF renderer is a setting of the server (GET/PUT /api/settings), shared by all users. The environment
  // variables of the server are only shown: they are changed in .env (or the environment) and need a restart.

  // Server settings: { renderer, renderers: [{ id, available }], environment: [{ name, group, default, set, value,
  // secret }] }; null while loading.
  let serverSettings = null;
  let serverError = "";
  let isSaving = false;
  // Key of the confirmation shown after a save (e.g. "settings.saved"), "" otherwise.
  let savedNotice = "";

  // Shows only the environment variables set on the server, hiding those using their default.
  let onlySetVariables = false;

  // Versions: git commit (hash and date) of the frontend, set when it was built (vite.config.js), and of the backend
  // (/api/version). null fields if unknown; backendVersion is null while loading, false if it cannot be read.
  // eslint-disable-next-line no-undef
  const frontendVersion = __NOCUMENT_VERSION__;
  let backendVersion = null;

  onMount(loadServerSettings);
  onMount(async () => {
    try {
      const response = await apiFetch("/api/version");
      backendVersion = response.ok ? await response.json() : false;
    } catch {
      backendVersion = false;
    }
  });

  // Commit date in the format of the web app's language.
  function formatCommitDate(date) {
    return date ? new Date(date).toLocaleString($language, { dateStyle: "medium", timeStyle: "short" }) : "";
  }

  $: environment = serverSettings?.environment ?? [];
  $: setVariablesCount = environment.filter((variable) => variable.set).length;
  // Variables grouped by section of .env.example, in the order sent by the server.
  $: variableGroups = environment
    .filter((variable) => variable.set || !onlySetVariables)
    .reduce((groups, variable) => {
      const group = groups.find((item) => item.id === variable.group);
      if (group) {
        group.variables.push(variable);
      } else {
        groups.push({ id: variable.group, variables: [variable] });
      }
      return groups;
    }, []);

  // Text of a value: secret values are never sent, null defaults are found automatically by the server.
  function formatValue(value, secret = false) {
    if (secret) {
      return $t("settings.environment.hidden");
    }
    if (value === null) {
      return $t("settings.environment.automatic");
    }
    return value === "" ? $t("settings.environment.empty") : value;
  }

  async function loadServerSettings() {
    serverError = "";
    try {
      const response = await apiFetch("/api/settings");
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("settings.loadError"));
      }
      serverSettings = data;
    } catch (error) {
      serverError = error.message || $t("settings.loadError");
    }
  }

  // Saves the chosen PDF renderer on the server.
  async function chooseRenderer(rendererId) {
    if (isSaving || rendererId === serverSettings.renderer) {
      return;
    }
    isSaving = true;
    serverError = "";
    savedNotice = "";
    try {
      const response = await apiFetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ renderer: rendererId })
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || $t("settings.saveError"));
      }
      serverSettings = data;
      savedNotice = "settings.saved";
    } catch (error) {
      serverError = error.message;
    } finally {
      isSaving = false;
    }
  }
</script>

<div class="page-heading">
  <div class="page-heading-top">
    <BackButton />
    <p>Nocument</p>
  </div>
  <h1>{$t("settings.title")}</h1>
  <span>{$t("settings.subtitle")}</span>
</div>

<div class="settings-sections">
  <section class="settings-section" aria-labelledby="settings-language-title">
    <div class="settings-section-heading">
      <h2 id="settings-language-title">{$t("settings.language.title")}</h2>
      <span>{$t("settings.language.description")}</span>
    </div>
    <div class="settings-options" role="radiogroup" aria-labelledby="settings-language-title">
      {#each LANGUAGES as option (option.code)}
        <label class="settings-option" class:selected={$language === option.code}>
          <input type="radio" name="language" value={option.code} bind:group={$language} />
          <span class="settings-option-name">{option.name}</span>
          <span class="settings-option-hint">{$t(`settings.language.options.${option.code}`)}</span>
        </label>
      {/each}
    </div>
  </section>

  <AppearanceSettings />

  <section class="settings-section" aria-labelledby="settings-renderer-title">
    <div class="settings-section-heading">
      <h2 id="settings-renderer-title">{$t("settings.renderer.title")}</h2>
      <span>{$t("settings.renderer.description")}</span>
    </div>
    {#if serverSettings}
      <div class="settings-options" role="radiogroup" aria-labelledby="settings-renderer-title">
        {#each serverSettings.renderers as renderer (renderer.id)}
          <label class="settings-option" class:selected={serverSettings.renderer === renderer.id} class:unavailable={!renderer.available}>
            <input
              type="radio"
              name="renderer"
              value={renderer.id}
              checked={serverSettings.renderer === renderer.id}
              disabled={!renderer.available || isSaving}
              onchange={() => chooseRenderer(renderer.id)}
            />
            <span class="settings-option-name">{$t(`settings.renderer.names.${renderer.id}`)}</span>
            <span class="settings-option-hint">
              {renderer.available ? $t(`settings.renderer.hints.${renderer.id}`) : $t("settings.renderer.unavailable")}
            </span>
          </label>
        {/each}
      </div>
      {#if serverSettings.renderers.some((renderer) => renderer.id === serverSettings.renderer && !renderer.available)}
        <p class="table-warning" role="status">{$t("settings.renderer.fallback")}</p>
      {/if}
    {:else if !serverError}
      <p class="status">{$t("settings.loading")}</p>
    {/if}
    {#if serverError}
      <p class="compile-error" role="alert">{serverError}</p>
      {#if !serverSettings}
        <button class="secondary-button" type="button" onclick={loadServerSettings}>{$t("settings.retry")}</button>
      {/if}
    {/if}
    {#if savedNotice}<p class="settings-saved" role="status">{$t(savedNotice)}</p>{/if}
  </section>

  <section class="settings-section" aria-labelledby="settings-environment-title">
    <div class="settings-section-heading">
      <h2 id="settings-environment-title">{$t("settings.environment.title")}</h2>
      <span>{$t("settings.environment.description")}</span>
    </div>
    {#if serverSettings}
      <div class="env-toolbar">
        <span class="env-summary">
          {$t("settings.environment.summary", { set: setVariablesCount, defaulted: environment.length - setVariablesCount })}
        </span>
        <label class="env-filter">
          <input type="checkbox" bind:checked={onlySetVariables} />
          {$t("settings.environment.onlySet")}
        </label>
      </div>
      {#each variableGroups as group (group.id)}
        <div class="env-group">
          <h3>{$t(`settings.environment.groups.${group.id}`)}</h3>
          <dl class="env-list">
            {#each group.variables as variable (variable.name)}
              <div class="env-variable" class:is-set={variable.set}>
                <dt>
                  <code>{variable.name}</code>
                  <span class="env-badge" class:is-set={variable.set}>
                    {variable.set ? $t("settings.environment.set") : $t("settings.environment.default")}
                  </span>
                </dt>
                <dd class="env-value">
                  {#if variable.set}
                    <code>{formatValue(variable.value, variable.secret)}</code>
                    <span class="env-default">{$t("settings.environment.defaultValue", { value: formatValue(variable.default) })}</span>
                  {:else}
                    <code>{formatValue(variable.default)}</code>
                  {/if}
                </dd>
                <dd class="env-description">{$t(`settings.environment.variables.${variable.name}`)}</dd>
              </div>
            {/each}
          </dl>
        </div>
      {:else}
        <p class="status">{$t("settings.environment.noneSet")}</p>
      {/each}
    {:else if !serverError}
      <p class="status">{$t("settings.loading")}</p>
    {/if}
  </section>
  <section class="settings-section" aria-labelledby="settings-version-title">
    <div class="settings-section-heading">
      <h2 id="settings-version-title">{$t("settings.version.title")}</h2>
      <span>{$t("settings.version.description")}</span>
    </div>
    <dl class="version-list">
      {#each [["frontend", frontendVersion], ["backend", backendVersion]] as [part, version] (part)}
        <div class="version-row">
          <dt>{$t(`settings.version.${part}`)}</dt>
          <dd>
            {#if version === null && part === "backend"}
              <span class="settings-option-hint">{$t("settings.loading")}</span>
            {:else if version?.commit}
              <code title={version.commit}>{version.commit.slice(0, 7)}</code>
              {#if version.date}<span class="settings-option-hint">{formatCommitDate(version.date)}</span>{/if}
            {:else}
              <span class="settings-option-hint">{$t("settings.version.unknown")}</span>
            {/if}
          </dd>
        </div>
      {/each}
    </dl>
    {#if frontendVersion.commit && backendVersion?.commit && frontendVersion.commit !== backendVersion.commit}
      <p class="table-warning" role="status">{$t("settings.version.mismatch")}</p>
    {/if}
  </section>
</div>
