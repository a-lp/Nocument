<script>
  // Interface of the "Azure DevOps query" package: runs a saved query and previews the table of its work items.
  // The recent queries (id, project and a name) are kept in this browser with storage; the token never is: it is a
  // secret, typed again when needed (or left empty to use the server's AZURE_DEVOPS_TOKEN).
  let { plugin, api, storage, language, components } = $props();

  const TEXT = {
    en: {
      intro: "Run a saved Azure DevOps (TFS) query and preview the table of its work items. In the Builder and in the content blocks the same table comes from the \"From plugin\" section of the table form.",
      token: "Token", query: "Query (id or link)", project: "Project", run: "Run query", running: "Running...",
      recent: "Recent queries in this browser", none: "No recent queries.", use: "Use", forget: "Forget",
      rows: (n) => `${n} work items`, name: "Name for the recent list (optional)"
    },
    it: {
      intro: "Esegui una query salvata di Azure DevOps (TFS) e guarda l'anteprima della tabella dei suoi work item. Nel Builder e nei blocchi di contenuti la stessa tabella si ottiene dalla sezione \"Da plugin\" del modulo della tabella.",
      token: "Token", query: "Query (id o link)", project: "Progetto", run: "Esegui query", running: "Esecuzione...",
      recent: "Query recenti in questo browser", none: "Nessuna query recente.", use: "Usa", forget: "Dimentica",
      rows: (n) => `${n} work item`, name: "Nome per l'elenco recenti (facoltativo)"
    }
  };
  const text = TEXT[language] ?? TEXT.en;
  const tokenParameter = plugin.parameters.table?.find((parameter) => parameter.name === "token");
  const MAX_RECENT = 8;

  let token = $state("");
  let query = $state("");
  let project = $state(plugin.parameters.table?.find((parameter) => parameter.name === "project")?.default ?? "");
  let label = $state("");
  let recent = $state(storage.get("recent", []));
  let table = $state(null);
  let isRunning = $state(false);
  let error = $state("");

  async function run() {
    isRunning = true;
    error = "";
    try {
      table = await api.compile("table", { token, query, project });
      // Remembered without the token.
      const entry = { query: query.trim(), project: project.trim(), label: label.trim() || query.trim() };
      recent = [entry, ...recent.filter((item) => item.query !== entry.query || item.project !== entry.project)].slice(0, MAX_RECENT);
      storage.set("recent", recent);
    } catch (failure) {
      table = null;
      error = failure.message;
    } finally {
      isRunning = false;
    }
  }

  function use(item) {
    query = item.query;
    project = item.project;
    label = item.label === item.query ? "" : item.label;
  }

  function forget(item) {
    recent = recent.filter((entry) => entry !== item);
    storage.set("recent", recent);
  }
</script>

<div class="azure">
  <p class="muted">{text.intro}</p>
  <form class="fields" onsubmit={(event) => { event.preventDefault(); run(); }}>
    <label>{text.token}<input type="password" autocomplete="off" placeholder={tokenParameter?.placeholder ?? ""} bind:value={token} /></label>
    <label class="wide">{text.query}<input type="text" required bind:value={query} /></label>
    <label>{text.project}<input type="text" required bind:value={project} /></label>
    <label class="wide">{text.name}<input type="text" bind:value={label} /></label>
    <div class="actions"><button type="submit" disabled={isRunning || !query.trim()}>{isRunning ? text.running : text.run}</button></div>
  </form>
  {#if error}<p class="error" role="alert">{error}</p>{/if}

  {#if table}
    <p class="muted">{text.rows(Math.max(0, table.rows.length - (table.header ? 1 : 0)))}</p>
    <div class="preview"><components.ContentSheet contents={[table]} readonly compact /></div>
  {/if}

  <section class="recent">
    <h3>{text.recent}</h3>
    {#if recent.length}
      <ul>
        {#each recent as item (item.query + item.project)}
          <li>
            <span title={item.query}>{item.label}<small>{item.project}</small></span>
            <button type="button" class="link" onclick={() => use(item)}>{text.use}</button>
            <button type="button" class="link danger" onclick={() => forget(item)}>{text.forget}</button>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">{text.none}</p>
    {/if}
  </section>
</div>

<style>
  .azure {
    display: grid;
    gap: 1rem;
  }

  .muted {
    margin: 0;
    color: var(--text-muted);
  }

  .fields {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 0.75rem 1rem;
    align-items: end;
  }

  .wide {
    grid-column: span 2;
  }

  label {
    display: grid;
    gap: 0.3rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  input {
    box-sizing: border-box;
    width: 100%;
    min-width: 0;
    padding: 0.5rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: 0.3rem;
    font: inherit;
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

  .recent {
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
    display: grid;
    flex: 1;
    min-width: 0;
    overflow-wrap: anywhere;
  }

  small {
    color: var(--text-muted);
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

  @media (max-width: 640px) {
    .wide {
      grid-column: auto;
    }
  }
</style>
