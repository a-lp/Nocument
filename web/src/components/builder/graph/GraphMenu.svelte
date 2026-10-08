<script>
  import { onMount } from "svelte";

  // Context menu of the graph, placed at (x, y) relative to the container and kept inside its borders.
  // groups: [{ title, actions: [{ label, icon, danger, disabled, onSelect }] }]. Esc or a click outside close it.
  let { x, y, bounds, groups, onClose } = $props();

  let menu;
  let width = $state(0);
  let height = $state(0);
  let left = $derived(Math.max(8, Math.min(x, bounds.width - width - 8)));
  let top = $derived(Math.max(8, Math.min(y, bounds.height - height - 8)));

  onMount(() => {
    menu.querySelector("button:not(:disabled)")?.focus();
    // In the capture phase: a click outside closes the menu before reaching the graph.
    const closeOutside = (event) => {
      if (!menu.contains(event.target)) {
        onClose();
      }
    };
    window.addEventListener("pointerdown", closeOutside, true);
    return () => window.removeEventListener("pointerdown", closeOutside, true);
  });

  // Up and down arrows between the items, Esc to close.
  function handleKeydown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
      return;
    }
    event.preventDefault();
    const items = [...menu.querySelectorAll("button:not(:disabled)")];
    const index = items.indexOf(document.activeElement);
    const next = event.key === "ArrowDown" ? index + 1 : index - 1;
    items[(next + items.length) % items.length]?.focus();
  }

  function select(action) {
    onClose();
    action.onSelect();
  }
</script>

<div
  bind:this={menu}
  bind:clientWidth={width}
  bind:clientHeight={height}
  class="graph-menu"
  style={`left: ${left}px; top: ${top}px`}
  role="menu"
  tabindex="-1"
  onkeydown={handleKeydown}
>
  {#each groups as group}
    {#if group.title}<p class="graph-menu-title">{group.title}</p>{/if}
    {#each group.actions as action}
      <button
        class="graph-menu-item"
        class:danger={action.danger}
        type="button"
        role="menuitem"
        disabled={action.disabled}
        onclick={() => select(action)}
      >
        <span class="graph-menu-icon">{action.icon}</span>{action.label}
      </button>
    {/each}
  {/each}
</div>
