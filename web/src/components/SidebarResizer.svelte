<script>
  import { onMount } from "svelte";
  import { t } from "../i18n.js";

  // Handle to resize the width of a secondary sidebar: it is dragged, moved with the keyboard arrows and goes back
  // to the initial width with a double click. It goes in a container with position: relative and --sidebar-width
  // equal to width (in px), which the container uses for the sidebar column.
  // storageKey: key to remember the width in the browser (localStorage), from one visit to the next;
  // label: accessible name of the handle (default: a generic "Resize the sidebar").
  export let width;
  export let min = 200;
  export let max = 560;
  export let storageKey = null;
  export let label = null;

  const STORAGE_PREFIX = "nocument:sidebar-width:";
  const KEYBOARD_STEP = 16;
  const initialWidth = width;

  onMount(() => {
    try {
      const saved = Number(storageKey && localStorage.getItem(STORAGE_PREFIX + storageKey));
      if (saved) {
        width = clamp(saved);
      }
    } catch {
      // localStorage not available (e.g. private browsing): the initial width stays.
    }
  });

  // Width within the limits; the maximum is at most half the window, to leave room for the rest of the page.
  function clamp(value) {
    return Math.round(Math.min(max, window.innerWidth / 2, Math.max(min, value)));
  }

  // Sets and remembers the width.
  function setWidth(value) {
    width = clamp(value);
    try {
      if (storageKey) {
        localStorage.setItem(STORAGE_PREFIX + storageKey, String(width));
      }
    } catch {
      // Without localStorage the width only lasts for this visit.
    }
  }

  // Resizes following the pointer while the button stays pressed.
  function startResize(event) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = width;
    const resize = (moveEvent) => setWidth(startWidth + moveEvent.clientX - startX);
    window.addEventListener("pointermove", resize);
    window.addEventListener("pointerup", () => window.removeEventListener("pointermove", resize), { once: true });
  }

  // Left/right arrows to shrink or widen.
  function handleKeydown(event) {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      setWidth(width + (event.key === "ArrowLeft" ? -KEYBOARD_STEP : KEYBOARD_STEP));
    }
  }
</script>

<button
  class="resize-handle"
  type="button"
  role="separator"
  aria-orientation="vertical"
  aria-valuenow={width}
  aria-valuemin={min}
  aria-valuemax={max}
  aria-label={label ?? $t("sidebar.resize")}
  title={$t("sidebar.resizeHint")}
  onpointerdown={startResize}
  onkeydown={handleKeydown}
  ondblclick={() => setWidth(initialWidth)}
></button>
