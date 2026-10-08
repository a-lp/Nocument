<script>
  import { t } from "../../i18n.js";
  import { NEW_CONTENT, SAVED_CONTENT } from "./dragTypes.js";

  // Content types to add (sidebar of Add new content and of the Builder): they are dragged to the wanted spot
  // (NEW_CONTENT data) or clicked (onSelect(type)). The SAVED_CONTENT type opens the choice among the saved blocks.
  // disabled: turns off heading, paragraph, image and table (e.g. styles not loaded yet); disableSaved that type.
  export let hint = "";
  export let disabled = false;
  export let disableSaved = false;
  export let onSelect = () => {};

  // Labels and hints are the translation keys contentTypes.<type> and palette.hints.<type>.
  const ITEMS = [
    { type: "heading", icon: "H" },
    { type: "paragraph", icon: "¶" },
    { type: "image", icon: "▣" },
    { type: "table", icon: "▦" },
    { type: SAVED_CONTENT, icon: "⧉" }
  ];

  // True if the type cannot be used right now. Reactive ($:) and not a plain function: the template recomputes
  // isDisabled(...) only when isDisabled changes, not when the props read inside it change.
  $: isDisabled = (type) => (type === SAVED_CONTENT ? disableSaved : disabled);

  // Starts dragging a content type.
  function handleDragStart(event, type) {
    event.dataTransfer.setData(NEW_CONTENT, type);
    event.dataTransfer.effectAllowed = "copy";
  }
</script>

<div>
  <p class="toc-title">{$t("palette.title")}</p>
  {#if hint}<span class="palette-hint">{hint}</span>{/if}
</div>
<ul class="content-palette">
  {#each ITEMS as item (item.type)}
    <li>
      <button
        class="palette-item"
        type="button"
        draggable={!isDisabled(item.type)}
        disabled={isDisabled(item.type)}
        title={$t(`palette.hints.${item.type}`)}
        ondragstart={(event) => handleDragStart(event, item.type)}
        onclick={() => onSelect(item.type)}
      >
        <span class="palette-icon" aria-hidden="true">{item.icon}</span>
        <span>{$t(`contentTypes.${item.type}`)}<small>{$t(`palette.hints.${item.type}`)}</small></span>
      </button>
    </li>
  {/each}
</ul>
