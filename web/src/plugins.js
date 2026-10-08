// Installed plugins, shared by the Plugins pages and the content modal (GET /api/plugins).
// { plugins: [{ id, name, description, version, file, compatibilities }], errors: [{ file, error }],
//   uploadEnabled, loaded, error }: refreshPlugins reloads it, e.g. after an installation.
import { writable } from "svelte/store";
import { apiFetch } from "./api.js";

export const pluginState = writable({ plugins: [], errors: [], uploadEnabled: false, loaded: false, error: "" });

// Reloads the list from the backend (which also picks up the scripts copied by hand into the plugins folder).
export async function refreshPlugins() {
  try {
    const response = await apiFetch("/api/plugins");
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(data?.error || response.statusText);
    }
    pluginState.set({ plugins: data.plugins, errors: data.errors, uploadEnabled: data.upload_enabled, loaded: true, error: "" });
  } catch (error) {
    pluginState.update((state) => ({ ...state, loaded: true, error: error.message }));
  }
}

// Initial values of a parameter form: the plugin's defaults, false for checkboxes, otherwise empty.
export function initialValues(parameters) {
  return Object.fromEntries(
    parameters.map((parameter) => [parameter.name, parameter.default ?? (parameter.type === "checkbox" ? false : "")])
  );
}

const VALUES_PREFIX = "nocument:plugin-values:";

// Values last used with the plugin for a content type (see rememberValues) over the initial ones; parameters the
// plugin no longer has and select values no longer among the options are ignored.
export function savedValues(pluginId, type, parameters) {
  const values = initialValues(parameters);
  const key = `${VALUES_PREFIX}${pluginId}:${type}`;
  const saved = { ...readStorage(() => localStorage, key), ...readStorage(() => sessionStorage, key) };
  for (const parameter of parameters) {
    const value = saved[parameter.name];
    const valid = parameter.type !== "select" || value === "" || parameter.options.some((option) => option.value === value);
    if (value !== undefined && valid) {
      values[parameter.name] = value;
    }
  }
  return values;
}

// Remembers the values used with the plugin, to propose them next time. Passwords (e.g. tokens) are secrets: they
// are kept only in this tab (sessionStorage, cleared when it is closed), the other values in this browser.
export function rememberValues(pluginId, type, parameters, values) {
  const key = `${VALUES_PREFIX}${pluginId}:${type}`;
  const persistent = {};
  const session = {};
  for (const parameter of parameters) {
    (parameter.type === "password" ? session : persistent)[parameter.name] = values[parameter.name];
  }
  writeStorage(() => localStorage, key, persistent);
  writeStorage(() => sessionStorage, key, session);
}

// JSON object saved in a storage, {} if missing or not readable (e.g. private browsing).
function readStorage(storage, key) {
  try {
    const value = JSON.parse(storage().getItem(key) ?? "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

// Saves a JSON object in a storage; without storage the values only last for this visit.
function writeStorage(storage, key, value) {
  try {
    storage().setItem(key, JSON.stringify(value));
  } catch {
    // Storage not available or full: nothing to remember.
  }
}

// Asks the plugin for a content of the given type with the form values; returns the content (JSON of the contents)
// or throws an Error with the backend message.
export async function compileWithPlugin(pluginId, type, values, fallbackMessage) {
  const response = await apiFetch(`/api/plugins/${encodeURIComponent(pluginId)}/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type, values })
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error || fallbackMessage);
  }
  return data.content;
}

// Parameters of the plugin for a content type; throws an Error with the backend message.
export async function loadParameters(pluginId, type, fallbackMessage) {
  const response = await apiFetch(`/api/plugins/${encodeURIComponent(pluginId)}/parameters?type=${encodeURIComponent(type)}`);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error || fallbackMessage);
  }
  return data.parameters;
}
