// Appearance of the web app: light/dark mode and color themes, a preference of this browser (localStorage).
// Every color of the interface is a CSS variable (--<token>, see TOKEN_GROUPS) used by app.css; a theme gives a
// color (#rrggbb) to each token. The built-in themes are "light" and "dark"; custom themes start as a copy of
// another theme, keep its base ("light" or "dark") and can change any color. The mode chooses which theme is used:
// the light one, the dark one or, with "system", the one matching the operating system.
// Transparent shades (shadows, hover backgrounds, the modal backdrop) are mixed in app.css from these colors with
// color-mix, so they follow the theme too.
import { derived, get, writable } from "svelte/store";

// Tokens grouped as shown in Settings; labels in locales/ (settings.appearance.groups / settings.appearance.tokens).
export const TOKEN_GROUPS = [
  { id: "surfaces", tokens: ["bg", "surface", "surface-muted", "surface-sunken", "chip-bg", "border", "border-subtle", "overlay", "shadow"] },
  { id: "text", tokens: ["text", "text-secondary", "text-muted"] },
  { id: "accent", tokens: ["accent", "accent-hover", "accent-text", "on-color", "accent-soft", "accent-muted", "accent-border"] },
  { id: "status", tokens: ["danger", "danger-hover", "danger-text", "danger-border", "success", "success-hover", "warning", "warning-bg", "warning-text"] },
  {
    id: "sidebar",
    tokens: [
      "sidebar-bg", "sidebar-panel-bg", "sidebar-text", "sidebar-text-strong", "sidebar-muted", "sidebar-hover",
      "sidebar-border", "sidebar-input-bg", "sidebar-accent"
    ]
  },
  { id: "graph", tokens: ["graph-bg", "graph-edge", "node-heading", "node-paragraph", "node-table", "node-image", "node-start"] },
  { id: "paper", tokens: ["paper", "paper-text", "paper-muted", "paper-border", "paper-heading", "paper-caption", "viewer-bg"] },
  { id: "highlights", tokens: ["highlight", "highlight-active", "highlight-ring"] },
  { id: "files", tokens: ["pdf", "pdf-hover", "word", "word-hover", "code-bg", "code-text"] }
];
export const TOKENS = TOKEN_GROUPS.flatMap((group) => group.tokens);

const LIGHT_COLORS = {
  bg: "#eceff4",
  surface: "#ffffff",
  "surface-muted": "#f4f6f9",
  "surface-sunken": "#e3e8ef",
  "chip-bg": "#e9edf3",
  border: "#c5cdd8",
  "border-subtle": "#dde3eb",
  overlay: "#0f1a2c",
  shadow: "#14213a",
  text: "#1b2230",
  "text-secondary": "#3b4557",
  "text-muted": "#5f6b7d",
  accent: "#2b579a",
  "accent-hover": "#1f4277",
  "accent-text": "#2b579a",
  "on-color": "#ffffff",
  "accent-soft": "#eef3fa",
  "accent-muted": "#dce7f6",
  "accent-border": "#9fb8de",
  danger: "#b3261e",
  "danger-hover": "#8c1d17",
  "danger-text": "#b3261e",
  "danger-border": "#ecbcb8",
  success: "#2e7d4f",
  "success-hover": "#22603c",
  warning: "#ffe45c",
  "warning-bg": "#fff8d6",
  "warning-text": "#5a4a00",
  "sidebar-bg": "#14213a",
  "sidebar-panel-bg": "#1c2d4d",
  "sidebar-text": "#b9c6dc",
  "sidebar-text-strong": "#ffffff",
  "sidebar-muted": "#8797b3",
  "sidebar-hover": "#263a5f",
  "sidebar-border": "#3a4f74",
  "sidebar-input-bg": "#101b30",
  "sidebar-accent": "#8fb3e8",
  "graph-bg": "#eceff4",
  "graph-edge": "#8d9ab0",
  "node-heading": "#2b579a",
  "node-paragraph": "#b9c3d2",
  "node-table": "#6b5ea8",
  "node-image": "#c47f2c",
  "node-start": "#14213a",
  paper: "#ffffff",
  "paper-text": "#1b2230",
  "paper-muted": "#eef1f5",
  "paper-border": "#8d9ab0",
  "paper-heading": "#1f3864",
  "paper-caption": "#44546a",
  "viewer-bg": "#525659",
  highlight: "#ffe45c",
  "highlight-active": "#ffc107",
  "highlight-ring": "#c98200",
  pdf: "#c5221f",
  "pdf-hover": "#9b1b18",
  word: "#185abd",
  "word-hover": "#124a9c",
  "code-bg": "#14213a",
  "code-text": "#e6edf3"
};

const DARK_COLORS = {
  ...LIGHT_COLORS,
  bg: "#0f1520",
  surface: "#182132",
  "surface-muted": "#1e293c",
  "surface-sunken": "#0b1018",
  "chip-bg": "#243049",
  border: "#34425b",
  "border-subtle": "#283449",
  overlay: "#000000",
  shadow: "#000000",
  text: "#e4e9f1",
  "text-secondary": "#c0c9d8",
  "text-muted": "#8e9ab0",
  accent: "#3768b8",
  "accent-hover": "#2c5aa3",
  "accent-text": "#8ab4f0",
  "accent-soft": "#17233a",
  "accent-muted": "#1f3152",
  "accent-border": "#3d5a8a",
  danger: "#c4453d",
  "danger-hover": "#a3352f",
  "danger-text": "#f08a83",
  "danger-border": "#6e2f2c",
  success: "#2a7a4d",
  "success-hover": "#21633e",
  "warning-bg": "#3a341a",
  "warning-text": "#f3e3a0",
  "sidebar-bg": "#0a1120",
  "sidebar-panel-bg": "#131d30",
  "sidebar-hover": "#1f2f4d",
  "sidebar-border": "#33456a",
  "sidebar-input-bg": "#0e1626",
  "graph-bg": "#121a27",
  "graph-edge": "#5d6b82",
  "node-heading": "#5b8bd6",
  "node-paragraph": "#66748a",
  "node-table": "#8b7fd0",
  "node-image": "#d89a4a",
  "node-start": "#2a3a57",
  "viewer-bg": "#2b2f33",
  "code-bg": "#0a1120"
};

// Built-in themes: not editable, they can be duplicated.
export const BUILT_IN_THEMES = [
  { id: "light", base: "light", builtIn: true, colors: LIGHT_COLORS },
  { id: "dark", base: "dark", builtIn: true, colors: DARK_COLORS }
];
export const MODES = ["system", "light", "dark"];
const STORAGE_KEY = "nocument.appearance";
const COLOR = /^#[0-9a-f]{6}$/;
const DEFAULT_APPEARANCE = { mode: "system", lightTheme: "light", darkTheme: "dark", customThemes: [] };

// Preferences: { mode, lightTheme, darkTheme (theme ids), customThemes: [{ id, name, base, colors }] }.
export const appearance = writable(loadAppearance());
// Theme shown instead of the one of the mode, e.g. while it is edited in Settings; null otherwise.
export const previewThemeId = writable(null);

const systemDark = window.matchMedia?.("(prefers-color-scheme: dark)");
const systemPrefersDark = writable(Boolean(systemDark?.matches));
systemDark?.addEventListener?.("change", (event) => systemPrefersDark.set(event.matches));

// All the themes: built-in first, then the custom ones.
export const themes = derived(appearance, ($appearance) => [...BUILT_IN_THEMES, ...$appearance.customThemes]);

// Theme in use, with all its colors (a custom theme saved before a token existed gets it from its base).
export const activeTheme = derived(
  [appearance, previewThemeId, systemPrefersDark],
  ([$appearance, $previewThemeId, $systemPrefersDark]) => {
    const dark = $appearance.mode === "dark" || ($appearance.mode === "system" && $systemPrefersDark);
    const id = $previewThemeId ?? (dark ? $appearance.darkTheme : $appearance.lightTheme);
    return resolveTheme($appearance, id, dark ? "dark" : "light");
  }
);

activeTheme.subscribe(applyTheme);
appearance.subscribe((value) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // Without localStorage the appearance only lasts for this visit.
  }
});

// Theme with the given id and complete colors; a missing theme (e.g. deleted) falls back to the built-in one of base.
export function resolveTheme(value, id, fallbackBase = "light") {
  const theme = [...BUILT_IN_THEMES, ...value.customThemes].find((item) => item.id === id)
    ?? BUILT_IN_THEMES.find((item) => item.id === fallbackBase);
  return { ...theme, colors: { ...baseColors(theme.base), ...theme.colors } };
}

// Colors of the built-in theme of a base ("light" or "dark").
export function baseColors(base) {
  return base === "dark" ? DARK_COLORS : LIGHT_COLORS;
}

// Sets the CSS variables of the theme on the page and the color scheme of the native controls (scrollbars, inputs).
function applyTheme(theme) {
  const root = document.documentElement;
  for (const token of TOKENS) {
    root.style.setProperty(`--${token}`, theme.colors[token]);
  }
  root.style.colorScheme = theme.base;
  root.dataset.theme = theme.base;
}

// Creates a custom theme as a copy of another one and returns its id.
export function duplicateTheme(sourceId, name) {
  const source = resolveTheme(get(appearance), sourceId);
  const id = `custom-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  appearance.update((value) => ({
    ...value,
    customThemes: [...value.customThemes, { id, name, base: source.base, colors: { ...source.colors } }]
  }));
  return id;
}

// Changes name, base or colors of a custom theme (changes: { name?, base?, colors? }, colors merged).
export function updateTheme(id, changes) {
  appearance.update((value) => ({
    ...value,
    customThemes: value.customThemes.map((theme) =>
      theme.id === id ? { ...theme, ...changes, colors: { ...theme.colors, ...(changes.colors ?? {}) } } : theme
    )
  }));
}

// Deletes a custom theme; the modes using it go back to the built-in theme of the same base.
export function deleteTheme(id) {
  appearance.update((value) => ({
    ...value,
    lightTheme: value.lightTheme === id ? "light" : value.lightTheme,
    darkTheme: value.darkTheme === id ? "dark" : value.darkTheme,
    customThemes: value.customThemes.filter((theme) => theme.id !== id)
  }));
}

export function isColor(value) {
  return COLOR.test(value);
}

// Saved preferences, with invalid values (e.g. edited by hand) replaced by the defaults.
function loadAppearance() {
  let saved = null;
  try {
    saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
  } catch {
    // Missing, unreadable or localStorage not available: the defaults.
  }
  if (!saved || typeof saved !== "object") {
    return { ...DEFAULT_APPEARANCE };
  }
  const customThemes = (Array.isArray(saved.customThemes) ? saved.customThemes : [])
    .filter((theme) => theme && typeof theme.id === "string" && typeof theme.name === "string")
    .map((theme) => ({
      id: theme.id,
      name: theme.name,
      base: theme.base === "dark" ? "dark" : "light",
      colors: Object.fromEntries(
        Object.entries(theme.colors ?? {}).filter(([token, color]) => TOKENS.includes(token) && isColor(color))
      )
    }));
  const ids = new Set([...BUILT_IN_THEMES, ...customThemes].map((theme) => theme.id));
  return {
    mode: MODES.includes(saved.mode) ? saved.mode : DEFAULT_APPEARANCE.mode,
    lightTheme: ids.has(saved.lightTheme) ? saved.lightTheme : "light",
    darkTheme: ids.has(saved.darkTheme) ? saved.darkTheme : "dark",
    customThemes
  };
}
