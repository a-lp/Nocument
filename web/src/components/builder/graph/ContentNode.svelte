<script>
  import { Handle, Position } from "@xyflow/svelte";
  import { getContext } from "svelte";
  import { t } from "../../../i18n.js";
  import { GRAPH_CONTEXT, inLayoutTable, isEditable } from "./graphLayout.js";
  import { valueText } from "../../../richText.js";

  // Node of the Builder graph: a content of the document (data.kind "content") or the beginning of the document
  // (data.kind "start"). Click: edit (select or deselect while some elements are selected, see GraphCanvas); drag: menu to add a content after the node; right click (or Shift+F10):
  // context menu. The events are handled by GraphCanvas through the context.
  let { id, data } = $props();

  const graph = getContext(GRAPH_CONTEXT);
  const TYPE_ICONS = { heading: "H", paragraph: "¶", image: "▣", table: "▦" };

  let item = $derived(data.item);
  let editable = $derived(data.kind === "content" && isEditable(item));
  let label = $derived(describe(data));
  let inLayout = $derived(data.kind === "content" && inLayoutTable(item));

  // Short text of the content, used in the node and as accessible label.
  function describe({ kind, item }) {
    if (kind === "start") {
      return $t("graph.start");
    }
    if (item.type === "heading") {
      return item.text.trim() || $t("graph.emptyHeading");
    }
    if (item.type === "table") {
      const columns = Math.max(0, ...item.rows.map((row) => row.length));
      const size = `${item.rows.length}×${columns}`;
      return item.caption
        ? `${item.caption} (${size})`
        : $t("graph.tableSummary", { size, cells: (item.rows[0] ?? []).map(valueText).filter((cell) => cell.trim()).join(" · ") });
    }
    if (item.type === "image") {
      return item.filename || $t("contentTypes.image");
    }
    return item.text.trim() || (item.has_image ? $t("graph.onlyImages") : $t("graph.emptyParagraph"));
  }

  // Type and style shown in the node header.
  function caption(item) {
    const style = item.style ? ` · ${item.style}` : "";
    if (item.type === "heading") {
      return `${$t("graph.headingLevel", { level: item.level })}${style}`;
    }
    if (item.type === "table") {
      return `${$t("contentTypes.table")}${style}`;
    }
    if (item.type === "image") {
      return $t("contentTypes.image");
    }
    return `${item.has_image ? $t("graph.paragraphWithImages") : $t("contentTypes.paragraph")}${style}`;
  }

  function handleKeydown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      graph.activate(id);
    } else if (event.key === "ContextMenu" || (event.key === "F10" && event.shiftKey)) {
      event.preventDefault();
      graph.openContextMenuAt(event.currentTarget, id);
    }
  }

  function handleToggle(event) {
    event.stopPropagation();
    graph.toggleSection(data.collapseKey);
  }
</script>

<Handle type="target" position={Position.Top} id="top" isConnectable={false} />
<Handle type="target" position={Position.Left} id="left" isConnectable={false} />

<!-- nopan/nodrag: dragging from the node moves neither the view nor the node, it opens the insertion menu. -->
<div
  class={`graph-node nopan nodrag ${data.kind === "start" ? "graph-node-start" : `graph-node-${item.type}`}`}
  class:editable
  class:collapsed={data.isCollapsed}
  style={item?.type === "heading" ? `--level: ${Math.min(item.level, 4)}` : undefined}
  role="button"
  tabindex="0"
  aria-label={data.kind === "start" ? $t("graph.startLabel") : `${caption(item)}: ${label}`}
  class:in-layout={inLayout}
  title={inLayout
    ? $t("graph.inLayoutHint")
    : data.kind === "content" && !editable ? $t("graph.notEditableHint") : undefined}
  onpointerdown={(event) => graph.pointerDown(event, id)}
  onpointermove={(event) => graph.pointerMove(event)}
  onpointerup={(event) => graph.pointerUp(event)}
  onpointercancel={() => graph.pointerCancel()}
  onclick={(event) => graph.click(event, id)}
  oncontextmenu={(event) => graph.contextMenu(event, id)}
  onkeydown={handleKeydown}
  onfocus={(event) => graph.focusIn(event.currentTarget, id)}
>
  {#if data.kind === "start"}
    <span class="graph-node-icon">▶</span>
    <span class="graph-node-text">{$t("graph.start")}</span>
  {:else}
    <div class="graph-node-header">
      <span class="graph-node-icon">{TYPE_ICONS[item.type]}</span>
      <span class="graph-node-caption">{caption(item)}</span>
      {#if inLayout}<span class="graph-node-layout" aria-label={$t("graph.inLayout")}>⊞</span>{/if}
      {#if data.hasSection}
        <button
          class="graph-node-toggle"
          type="button"
          aria-label={data.isCollapsed ? $t("graph.expandSectionOf", { heading: label }) : $t("graph.collapseSectionOf", { heading: label })}
          aria-expanded={!data.isCollapsed}
          title={data.isCollapsed ? $t("graph.expandSection") : $t("graph.collapseSection")}
          onpointerdown={(event) => event.stopPropagation()}
          onclick={handleToggle}
        >{data.isCollapsed ? `+${data.hiddenCount}` : "−"}</button>
      {/if}
    </div>
    <span class="graph-node-text">{label}</span>
  {/if}
</div>

<Handle type="source" position={Position.Bottom} id="bottom" isConnectable={false} />
<Handle type="source" position={Position.Right} id="right" isConnectable={false} />
