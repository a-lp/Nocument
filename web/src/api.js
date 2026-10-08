// Calls to the backend: like fetch, plus the language of the web app in Accept-Language, so the backend answers
// (e.g. error messages) in the language chosen in Settings.
import { get } from "svelte/store";
import { language } from "./i18n.js";

export function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers);
  headers.set("Accept-Language", get(language));
  return fetch(url, { ...options, headers });
}
