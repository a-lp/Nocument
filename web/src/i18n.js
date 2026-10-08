// Translations of the web app: one file per language in locales/ (shared with the backend), mapping keys to texts.
// Nested objects group the keys ("builder.savePdf" is {"builder": {"savePdf": "..."}}); texts may contain {name}
// placeholders and, for plurals, be an object {"one", "other"} chosen by the "count" parameter.
// In components: $t("key", { name: value }). Outside components (e.g. plain JS modules): tr("key").
import { derived, get, writable } from "svelte/store";
import en from "../../locales/en.json";
import it from "../../locales/it.json";

const TRANSLATIONS = { en, it };
export const DEFAULT_LANGUAGE = "en";
// Languages offered in Settings: code and own name ("English", "Italiano").
export const LANGUAGES = Object.keys(TRANSLATIONS).map((code) => ({ code, name: TRANSLATIONS[code].language.name }));
const STORAGE_KEY = "nocument.language";

// The language is a per-browser preference: saved in localStorage, English until the user picks another one.
function savedLanguage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved in TRANSLATIONS ? saved : DEFAULT_LANGUAGE;
  } catch {
    // localStorage not available (e.g. private browsing): the default language for this visit.
    return DEFAULT_LANGUAGE;
  }
}

export const language = writable(savedLanguage());

language.subscribe((value) => {
  document.documentElement.lang = value;
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch {
    // Without localStorage the choice only lasts for this visit.
  }
});

// Value of a dotted key in the nested translations, or undefined.
function lookup(translations, key) {
  return key.split(".").reduce((value, part) => (value && typeof value === "object" ? value[part] : undefined), translations);
}

// Text of key in the given language (falling back to English), with the placeholders replaced by params.
// A missing key is returned as is, so it stays visible on the page.
export function translate(languageCode, key, params = {}) {
  let text = lookup(TRANSLATIONS[languageCode], key) ?? lookup(TRANSLATIONS[DEFAULT_LANGUAGE], key);
  if (text === undefined) {
    return key;
  }
  if (typeof text === "object") {
    text = params.count === 1 ? text.one : text.other;
  }
  return text.replace(/\{(\w+)\}/g, (placeholder, name) => (name in params ? String(params[name]) : placeholder));
}

// Store with the translation function of the current language: $t("key", params) in components updates the page
// when the language changes.
export const t = derived(language, ($language) => (key, params) => translate($language, key, params));

// Translation in the current language, for code that is not a component (it does not react to language changes).
export function tr(key, params) {
  return translate(get(language), key, params);
}
