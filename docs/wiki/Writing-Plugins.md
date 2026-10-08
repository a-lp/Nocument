# Writing plugins

A plugin is a subclass of `IPlugin` (`src/plugins/plugin_interface.py`) in the `plugin.py` of its package, importable with everything it needs from `src.plugins`. `plugins/sample_data/plugin.py` is a complete example for the four content types.

```python
from src.plugins import IPlugin, PluginError, PluginParameter, TABLE

class CustomersPlugin(IPlugin):
    id = "customers"            # lowercase letters, digits, "-" and "_"; unique among the installed plugins
    name = "Customers"
    description = "Customers of the CRM."
    version = "1.0"

    def parameters(self, content_type):
        # Called every time the form is opened: the options can come from the external data.
        return [
            PluginParameter("city", "City", type="select", required=True, options=["Rome", "Milan"]),
            PluginParameter("active", "Active only", type="checkbox", default=True),
        ]

    def compile_table(self, values):
        customers = load_customers(values["city"], values["active"])   # the plugin's own data access
        if not customers:
            raise PluginError(f"No customers in {values['city']}")       # message shown to the user
        return self.table([["Name", "Email"], *[[c.name, c.email] for c in customers]], caption="Customers")
```

- **Compatibilities**: the content types whose method the plugin overrides among `compile_heading`, `compile_paragraph`, `compile_image` and `compile_table`. The registry offers the plugin only for those types.
- **Parameters** (`PluginParameter`): `name`, `label`, `type` (`text`, `password` for secrets such as tokens, hidden while typing, `textarea`, `number`, `checkbox`, `select`, `date`), `required`, `default`, `options` (values or `(value, label)` pairs, for `select`), `minimum`/`maximum` (for `number`), `help` (hint under the field) and `placeholder` (text in the empty field, e.g. what happens if it is left empty). The compile methods receive the values already checked and converted: numbers as `int`/`float`, checkboxes as `bool`, dates as `"YYYY-MM-DD"`, empty fields as `None`.
- **Helpers** to create the contents: `self.heading(text, level, style=None, **formatting)`, `self.paragraph(text)` (an empty line starts a new paragraph) or `self.paragraph(html_text="<p>...</p>")`, `self.image(data, filename, width_cm, alignment)` and `self.table(rows, header=True, caption="", caption_position="below", style=None, alignment=None)`. The content classes (`NewHeading`, `NewParagraph`, `NewImage`, `WordTable`) can also be used directly.
- **Log**: `self.logger.info(...)` or simply `print(...)` end up in the backend log under `nocument.plugins.<id>` (see [Logging](Logging.md)).
- **Errors**: `PluginError("...")` shows its message to the user; any other exception shows a generic error and goes in the server log. A returned content of the wrong type, or not valid (e.g. bytes that are not an image), is an error too.

The plugin is created once, without arguments, when its file is loaded: it can open connections or read configuration (e.g. environment variables) in `__init__`.

## Writing the interface

`ui.svelte` is a Svelte 5 component (runes or the legacy syntax), shown in the **Interface** tab of the plugin page. It is **not part of the web app's build**: when the page opens, the web app downloads the source (`/api/plugins/<id>/ui`), compiles it in the browser with the Svelte compiler (loaded only then, as a separate chunk) and mounts it with the web app's own Svelte runtime. It receives these props:

| Prop | Content |
| ---- | ------- |
| `plugin` | `{ id, name, description, version, file (package), compatibilities, parameters: { <type>: [...] } }` |
| `api` | `parameters(type)` and `compile(type, values)`: the parameters of the plugin and the content it creates (JSON of the contents, as in the Builder); errors are thrown with the message to show |
| `storage` | data saved **in the browser** for the package: `get(key, fallback)`, `set(key, value)` (JSON; returns `false` if it cannot be saved, e.g. private browsing or storage full), `remove(key)`, `keys()`, `clear()`. The keys are prefixed with `nocument.plugin.<package>.` in `localStorage`, so packages do not see each other's data |
| `language` | language of the web app (`"en"`, `"it"`); the interface is mounted again when it changes |
| `components` | `{ ContentSheet }`: the web app's preview of contents (`<components.ContentSheet contents={[content]} readonly compact />`) |

```svelte
<script>
  let { api, storage, components } = $props();
  let city = $state(storage.get("city", "Rome"));
  let content = $state(null);

  async function load() {
    storage.set("city", city);                          // remembered in this browser
    content = await api.compile("table", { city });     // created by the plugin.py of the package
  }
</script>

<input bind:value={city} />
<button onclick={load}>Preview</button>
{#if content}<components.ContentSheet contents={[content]} readonly compact />{/if}
```

The interface can import only `svelte` and its modules (`svelte/store`, `svelte/transition`, `svelte/motion`, ...): it is a single file. Its `<style>` is scoped as usual; the CSS variables of the theme (`--accent`, `--surface`, `--text`, `--border`, ... see [Settings](Settings.md)) make it follow light, dark and custom themes. A compile error is shown on the page with its line and column. The interface runs in the web app's page with its permissions, like the Python script runs on the server: install only packages you trust. Secrets (e.g. tokens) should not be saved with `storage`.

## Backend

- `src/plugins/plugin_interface.py`: `IPlugin`, `PluginParameter`, `PluginError` and the content type constants (`HEADING`, `PARAGRAPH`, `IMAGE`, `TABLE`).
- `src/plugins/registry.py`: `PluginRegistry`, the internal registry. It discovers the packages (and loose scripts) in the folder, knows their compatibilities (`plugins(content_type)`), returns their parameters, runs them (`compile`: values validated, content checked with `content_from_dict`), reads `ui.svelte` and `README.md` (`package_file`) and installs (`read_package`, `install`) or removes the packages.
- `web/src/plugins/pluginRuntime.js` (with the Svelte compiler, loaded only on a plugin page), `web/src/components/plugins/PluginUiHost.svelte`, `PluginReadme.svelte` and `web/src/plugins/pluginStorage.js`: compilation and mounting of the interfaces, the README (rendered with `marked`) and the browser storage of the packages.
- `src/plugins/api.py`: REST routes `/api/plugins` (see [API](API.md)).
