<script>
  import { t } from "../../i18n.js";

  // Table of contents like Word's navigation pane: headings only, indented by level and collapsible.
  // entries: [{ id, text, depth, parentIds, hasChildren }] in document order; selectedIds: ids of the headings
  // selected in the graph, highlighted.
  export let entries = [];
  export let activeId = null;
  export let selectedIds = new Set();
  export let onSelect = () => {};

  let collapsed = new Set();

  $: visibleEntries = entries.filter((entry) => !entry.parentIds.some((id) => collapsed.has(id)));

  // Expands or collapses the subheadings of a heading.
  function toggle(id) {
    collapsed = new Set(collapsed);
    if (collapsed.has(id)) {
      collapsed.delete(id);
    } else {
      collapsed.add(id);
    }
  }
</script>

<nav class="toc-panel" aria-label={$t("toc.label")}>
  {#if entries.length}
    <ul>
      {#each visibleEntries as entry (entry.id)}
        <li style={`--depth: ${entry.depth}`}>
          {#if entry.hasChildren}
            <button
              class="toc-toggle"
              type="button"
              aria-label={collapsed.has(entry.id) ? $t("toc.expand", { heading: entry.text }) : $t("toc.collapse", { heading: entry.text })}
              aria-expanded={!collapsed.has(entry.id)}
              onclick={() => toggle(entry.id)}
            >
              {collapsed.has(entry.id) ? "▸" : "▾"}
            </button>
          {:else}
            <span class="toc-toggle-spacer"></span>
          {/if}
          <button
            class="toc-entry"
            class:active={entry.id === activeId}
            class:selected={selectedIds.has(entry.id)}
            class:top-level={entry.depth === 0}
            type="button"
            title={entry.text}
            aria-current={entry.id === activeId ? "location" : undefined}
            onclick={() => onSelect(entry.id)}
          >
            {entry.text}
          </button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="empty-keywords">{$t("toc.empty")}</p>
  {/if}
</nav>
