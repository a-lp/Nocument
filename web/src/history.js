// In-app history for the back arrow: every entry pushed by the app carries its position (history.state.index), so
// the arrow shows only when there is an earlier page of the web app to go back to (not on the first page opened, nor
// to a page of another site). The browser keeps the state, so it also works after a reload.
import { writable } from "svelte/store";

let currentIndex = 0;
export const canGoBack = writable(false);

function update(index) {
  currentIndex = index;
  canGoBack.set(index > 0);
}

// Called once at startup: the first entry gets index 0, unless it already has one (e.g. after a reload).
export function initHistory() {
  const index = window.history.state?.index;
  if (typeof index === "number") {
    update(index);
  } else {
    window.history.replaceState({ ...window.history.state, index: 0 }, "");
    update(0);
  }
}

// Adds an entry for the path, after the current one.
export function pushPath(path) {
  window.history.pushState({ index: currentIndex + 1 }, "", path);
  update(currentIndex + 1);
}

// After the browser's back/forward (popstate), with the state of the entry reached.
export function restoreIndex(state) {
  update(typeof state?.index === "number" ? state.index : 0);
}

export function goBack() {
  window.history.back();
}
