<script>
  // Form of the parameters of a plugin (see PluginParameter in src/plugins/plugin_interface.py), drawn from their
  // description: the plugin decides the fields, the web app only shows them. values: { name: value }, bound.
  export let parameters = [];
  export let values = {};
  export let idPrefix = "plugin";
  export let disabled = false;

  // Number fields: empty stays "" (missing value), otherwise a number.
  function setNumber(name, raw) {
    values = { ...values, [name]: raw === "" ? "" : Number(raw) };
  }
</script>

<div class="plugin-form">
  {#each parameters as parameter (parameter.name)}
    {@const id = `${idPrefix}-${parameter.name}`}
    {#if parameter.type === "checkbox"}
      <label class="plugin-checkbox" for={id}>
        <input {id} type="checkbox" bind:checked={values[parameter.name]} {disabled} />
        <span>{parameter.label}</span>
      </label>
    {:else}
      <label for={id}>
        <span>{parameter.label}{parameter.required ? " *" : ""}</span>
        {#if parameter.type === "textarea"}
          <textarea {id} rows="3" placeholder={parameter.placeholder || undefined} bind:value={values[parameter.name]} {disabled}></textarea>
        {:else if parameter.type === "select"}
          <select {id} bind:value={values[parameter.name]} {disabled}>
            {#if !parameter.required}<option value="">—</option>{/if}
            {#each parameter.options as option (option.value)}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        {:else if parameter.type === "number"}
          <input
            {id}
            type="number"
            min={parameter.minimum ?? undefined}
            max={parameter.maximum ?? undefined}
            step="any"
            placeholder={parameter.placeholder || undefined}
            value={values[parameter.name] ?? ""}
            {disabled}
            oninput={(event) => setNumber(parameter.name, event.target.value)}
          />
        {:else if parameter.type === "password"}
          <!-- Secrets (e.g. tokens): hidden and not saved by the browser's form autofill. -->
          <input {id} type="password" autocomplete="off" placeholder={parameter.placeholder || undefined} bind:value={values[parameter.name]} {disabled} />
        {:else}
          <input {id} type={parameter.type === "date" ? "date" : "text"} placeholder={parameter.placeholder || undefined} bind:value={values[parameter.name]} {disabled} />
        {/if}
      </label>
    {/if}
    {#if parameter.help}<span class="plugin-help">{parameter.help}</span>{/if}
  {/each}
</div>
