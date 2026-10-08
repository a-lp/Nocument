<script>
  import { Background, Controls, MiniMap, Panel, SvelteFlow, useSvelteFlow } from "@xyflow/svelte";
  import "@xyflow/svelte/dist/style.css";
  import { setContext, tick } from "svelte";
  import { t } from "../../../i18n.js";
  import { NEW_CONTENT, SAVED_CONTENT } from "../../content/dragTypes.js";
  import ContentNode from "./ContentNode.svelte";
  import GraphMenu from "./GraphMenu.svelte";
  import {
    GRAPH_CONTEXT, NODE_HEIGHT, NODE_WIDTH, START_ID, allSectionKeys, buildGraph, inLayoutTable, insertionAfter,
    isEditable, itemKey, moveRange, relinkCheck
  } from "./graphLayout.js";

  // Content graph of the document (see graphLayout.js), inside a SvelteFlowProvider (see BuilderGraph).
  // structure: tree of SectionAnalyzer; activeId: key (itemKey) of the heading chosen in the table of contents;
  // selectedKeys: keys (itemKey) of the selected elements: while there is at least one (selection mode) a click or
  // Enter on a node selects or deselects it instead of opening its editing; stylesReady: false until the styles are
  // loaded.
  // Callback: onInsert(after, suggestedLevel, type), onEdit(item), onDelete(item), onToggleSelect(item),
  // onAppend(type) for a content dragged from the sidebar and dropped outside the nodes and onMove(item, range, after)
  // when dragging from a node to another: item, with the blocks moving with it (range, see moveRange), must be moved
  // after the block after.
  let {
    structure,
    activeId = null,
    selectedKeys = new Set(),
    disabled = false,
    stylesReady = true,
    onInsert,
    onEdit,
    onDelete,
    onToggleSelect,
    onAppend,
    onMove
  } = $props();

  // Minimum movement (px) for a press on a node to become a drag rather than a click.
  const DRAG_THRESHOLD = 6;
  const NEW_CONTENT_ACTIONS = [
    { type: "heading", icon: "H" },
    { type: "paragraph", icon: "¶" },
    { type: "image", icon: "▣" },
    { type: "table", icon: "▦" },
    { type: SAVED_CONTENT, icon: "⧉" }
  ];
  const nodeTypes = { content: ContentNode };

  const flow = useSvelteFlow();
  let wrapper;
  let bounds = $state({ width: 0, height: 0 });
  // Keys of the collapsed headings (see buildGraph).
  let collapsed = $state(new Set());
  let graph = $derived(buildGraph(structure, collapsed));
  let nodes = $state.raw([]);
  let edges = $state.raw([]);
  // Drag from a node: { nodeId, pointerId, startX, startY, fromX, fromY, x, y, active }, plus targetId,
  // targetState and reason (see relinkCheck) when the pointer is over another node.
  let link = $state(null);
  // Open menu: { x, y, groups }.
  let menu = $state(null);
  // Node a content from the sidebar is being dragged over.
  let dropTargetId = $state(null);
  // The click ending a drag must not open the editing.
  let suppressClick = false;
  // Selection mode: at least one element is selected.
  let selecting = $derived(selectedKeys.size > 0);
  // Only the id, not link: otherwise every pointer movement would recreate all the nodes.
  let linkSourceId = $derived(link?.nodeId ?? null);
  let linkTargetId = $derived(link?.targetId ?? null);
  let linkTargetState = $derived(link?.targetState ?? null);
  // Temporary message (e.g. move not allowed), at the bottom center of the graph.
  let notice = $state("");
  let noticeTimer;

  $effect(() => {
    nodes = graph.nodes.map((node) => ({ ...node, class: nodeClass(node) }));
    edges = graph.edges;
  });

  function nodeClass(node) {
    const item = node.data.item;
    return [
      item?.type === "heading" && itemKey(item) === activeId && "active",
      // Not "selected": Svelte Flow toggles that class itself (its own selection, disabled here) and would remove it.
      item && selectedKeys.has(itemKey(item)) && "multi-selected",
      node.id === dropTargetId && "drop-target",
      node.id === linkSourceId && "link-source",
      node.id === linkTargetId && `link-target link-${linkTargetState}`
    ].filter(Boolean).join(" ");
  }

  function nodeById(id) {
    return graph.nodes.find((node) => node.id === id);
  }

  // How a node is named in "Add after ..." (e.g. "the beginning of the document", the quoted text, "the table").
  function nodeLabel(node) {
    if (node.id === START_ID) {
      return $t("graph.target.start");
    }
    // After an element of a layout table, contents are inserted (or moved) after the whole table.
    if (inLayoutTable(node.data.item)) {
      return $t("graph.target.layoutTable");
    }
    const { item } = node.data;
    const text = item.type === "heading" || item.type === "paragraph" ? item.text.trim() : "";
    const short = text.length > 40 ? `${text.slice(0, 40)}…` : text;
    return short ? $t("graph.target.quoted", { text: short }) : $t(`graph.target.${item.type}`);
  }

  // Position relative to the graph container.
  function relative(clientX, clientY) {
    const rect = wrapper.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }

  // Items to add a content after the node.
  function addGroup(node) {
    const { after, level } = insertionAfter(node);
    return {
      title: $t("graph.addAfter", { target: nodeLabel(node) }),
      actions: NEW_CONTENT_ACTIONS.map((action) => ({
        ...action,
        label: $t(`contentTypes.${action.type}`),
        disabled: disabled || (action.type !== SAVED_CONTENT && !stylesReady),
        onSelect: () => onInsert(after, level, action.type)
      }))
    };
  }

  // Full context menu: actions on the element and adding a content after it.
  function contextGroups(node) {
    if (node.id === START_ID) {
      return [addGroup(node)];
    }
    const { item } = node.data;
    const selected = selectedKeys.has(itemKey(item));
    return [
      {
        title: "",
        actions: [
          { label: $t("common.edit"), icon: "✎", disabled: disabled || !isEditable(item), onSelect: () => onEdit(item) },
          { label: selected ? $t("graph.deselect") : $t("graph.select"), icon: selected ? "☐" : "☑", disabled, onSelect: () => onToggleSelect(item) },
          { label: $t("common.delete"), icon: "🗑", danger: true, disabled, onSelect: () => onDelete(item) }
        ]
      },
      addGroup(node)
    ];
  }

  function openMenu(x, y, groups) {
    bounds = { width: wrapper.clientWidth, height: wrapper.clientHeight };
    menu = { x, y, groups };
  }

  function showNotice(message) {
    notice = message;
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => (notice = ""), 3500);
  }

  // Node under the pointer while dragging from source (excluding source and the beginning of the document).
  function linkTargetAt(clientX, clientY, sourceId) {
    const id = document.elementFromPoint(clientX, clientY)?.closest(".svelte-flow__node")?.dataset.id;
    if (!id || id === sourceId || id === START_ID) {
      return { targetId: null, targetState: null, reason: "" };
    }
    const { state, reason = "" } = relinkCheck(nodeById(sourceId), nodeById(id), graph.edges);
    return { targetId: id, targetState: state, reason };
  }

  function closeMenu() {
    menu = null;
    link = null;
  }

  // Actions for the nodes (ContentNode), through the context.
  setContext(GRAPH_CONTEXT, {
    pointerDown(event, nodeId) {
      if (disabled || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.target.closest("button")) {
        return;
      }
      const rect = event.currentTarget.getBoundingClientRect();
      // The line starts from the right side of the node, at half height.
      const from = relative(rect.right, rect.top + rect.height / 2);
      const point = relative(event.clientX, event.clientY);
      event.currentTarget.setPointerCapture(event.pointerId);
      link = {
        nodeId,
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        fromX: from.x,
        fromY: from.y,
        ...point,
        active: false
      };
    },
    pointerMove(event) {
      if (!link || menu || event.pointerId !== link.pointerId) {
        return;
      }
      const moved = Math.hypot(event.clientX - link.startX, event.clientY - link.startY) > DRAG_THRESHOLD;
      const active = link.active || moved;
      const target = active ? linkTargetAt(event.clientX, event.clientY, link.nodeId) : {};
      link = { ...link, ...relative(event.clientX, event.clientY), active, ...target };
    },
    pointerUp(event) {
      if (!link || menu || event.pointerId !== link.pointerId) {
        return;
      }
      if (!link.active) {
        link = null;
        return;
      }
      suppressClick = true;
      setTimeout(() => (suppressClick = false));
      // Drop on another node: its incoming link is replaced (move).
      const { targetId, targetState, reason } = linkTargetAt(event.clientX, event.clientY, link.nodeId);
      if (targetId) {
        const source = nodeById(link.nodeId);
        link = null;
        if (targetState === "move") {
          const target = nodeById(targetId);
          onMove(target.data.item, moveRange(target), insertionAfter(source).after);
        } else if (targetState === "invalid") {
          showNotice($t(reason));
        }
        return;
      }
      const point = relative(event.clientX, event.clientY);
      // The line stays visible while the menu is open.
      link = { ...link, ...point };
      openMenu(point.x, point.y, [addGroup(nodeById(link.nodeId))]);
    },
    pointerCancel() {
      if (!menu) {
        link = null;
      }
    },
    click(event, nodeId) {
      if (suppressClick) {
        return;
      }
      if (event.ctrlKey || event.metaKey) {
        toggleNode(nodeId);
        return;
      }
      activateNode(nodeId);
    },
    activate: activateNode,
    contextMenu(event, nodeId) {
      event.preventDefault();
      const point = relative(event.clientX, event.clientY);
      openMenu(point.x, point.y, contextGroups(nodeById(nodeId)));
    },
    openContextMenuAt(element, nodeId) {
      const rect = element.getBoundingClientRect();
      const point = relative(rect.left + 12, rect.bottom);
      openMenu(point.x, point.y, contextGroups(nodeById(nodeId)));
    },
    toggleSection(key) {
      collapsed = new Set(collapsed);
      if (collapsed.has(key)) {
        collapsed.delete(key);
      } else {
        collapsed.add(key);
      }
    },
    // With the keyboard (Tab) the reached node is centered if it is out of view.
    focusIn(element, nodeId) {
      if (!element.matches(":focus-visible")) {
        return;
      }
      const rect = element.getBoundingClientRect();
      const view = wrapper.getBoundingClientRect();
      if (rect.left < view.left || rect.right > view.right || rect.top < view.top || rect.bottom > view.bottom) {
        centerNode(nodeById(nodeId));
      }
    }
  });

  // Click or Enter on a node: in selection mode it is selected or deselected, otherwise its editing is opened.
  function activateNode(nodeId) {
    if (selecting) {
      toggleNode(nodeId);
    } else {
      editNode(nodeId);
    }
  }

  function toggleNode(nodeId) {
    const node = nodeById(nodeId);
    if (!disabled && node.id !== START_ID) {
      onToggleSelect(node.data.item);
    }
  }

  function editNode(nodeId) {
    const node = nodeById(nodeId);
    if (!disabled && node.id !== START_ID && isEditable(node.data.item)) {
      onEdit(node.data.item);
    }
  }

  function centerNode(node, zoom = flow.getZoom()) {
    return flow.setCenter(node.position.x + NODE_WIDTH / 2, node.position.y + NODE_HEIGHT / 2, { zoom, duration: 400 });
  }

  // Centers the heading with the given key (itemKey, from the table of contents), expanding the sections containing it.
  export async function focusHeading(headingKey) {
    const ancestors = graph.headingAncestors.get(headingKey) ?? [];
    if (ancestors.some((key) => collapsed.has(key))) {
      collapsed = new Set([...collapsed].filter((key) => !ancestors.includes(key)));
      await tick();
    }
    const node = nodeById(headingKey);
    if (node) {
      await centerNode(node, Math.max(flow.getZoom(), 0.8));
    }
  }

  // Contents dragged from the sidebar: on a node they are inserted after it, outside the nodes at the end.
  function nodeIdAt(target) {
    return target.closest?.(".svelte-flow__node")?.dataset.id ?? null;
  }

  function handleDragOver(event) {
    if (disabled || !event.dataTransfer?.types.includes(NEW_CONTENT)) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    dropTargetId = nodeIdAt(event.target);
  }

  function handleDragLeave(event) {
    if (!wrapper.contains(event.relatedTarget)) {
      dropTargetId = null;
    }
  }

  function handleDrop(event) {
    const type = event.dataTransfer?.getData(NEW_CONTENT);
    const nodeId = nodeIdAt(event.target);
    dropTargetId = null;
    if (disabled || !type) {
      return;
    }
    event.preventDefault();
    if (nodeId) {
      const { after, level } = insertionAfter(nodeById(nodeId));
      onInsert(after, level, type);
    } else {
      onAppend(type);
    }
  }

  // Dashed curve from the node to the pointer while dragging.
  function linkPath({ fromX, fromY, x, y }) {
    const bend = Math.max(40, Math.abs(x - fromX) / 2);
    return `M ${fromX} ${fromY} C ${fromX + bend} ${fromY}, ${x - bend} ${y}, ${x} ${y}`;
  }
</script>

<div
  bind:this={wrapper}
  class="builder-graph"
  class:linking={link?.active}
  role="application"
  aria-label={$t("graph.label")}
  ondragover={handleDragOver}
  ondragleave={handleDragLeave}
  ondrop={handleDrop}
>
  <SvelteFlow
    bind:nodes
    bind:edges
    {nodeTypes}
    initialViewport={{ x: 48, y: 72, zoom: 0.9 }}
    minZoom={0.1}
    maxZoom={1.75}
    nodesDraggable={false}
    nodesConnectable={false}
    elementsSelectable={false}
    nodesFocusable={false}
    edgesFocusable={false}
    deleteKey={null}
    zoomOnDoubleClick={false}
    onmovestart={() => menu && closeMenu()}
    onpaneclick={() => menu && closeMenu()}
  >
    <Background gap={24} />
    <Controls showLock={false} position="bottom-left" />
    <MiniMap position="bottom-right" pannable zoomable nodeColor={(node) => (node.class?.includes("active") ? "var(--warning)" : node.data.item?.type === "heading" ? "var(--node-heading)" : "var(--node-paragraph)")} />
    <Panel position="top-right">
      <div class="graph-toolbar">
        <button class="secondary-button" type="button" disabled={!collapsed.size} onclick={() => (collapsed = new Set())}>{$t("graph.expandAll")}</button>
        <button class="secondary-button" type="button" onclick={() => (collapsed = new Set(allSectionKeys(structure)))}>{$t("graph.collapseAll")}</button>
      </div>
    </Panel>
  </SvelteFlow>

  {#if link?.active}
    <svg class="graph-link" class:invalid={link.targetState === "invalid"} aria-hidden="true">
      <path d={linkPath(link)} />
      <circle cx={link.x} cy={link.y} r="5" />
    </svg>
    {#if link.targetId}
      <!-- Cosa succede rilasciando qui. -->
      <span class={`graph-link-label link-${link.targetState}`} style={`left: ${link.x + 14}px; top: ${link.y + 14}px`}>
        {link.targetState === "noop" ? $t("graph.drop.linked") : link.targetState === "invalid" ? $t("graph.drop.notAllowed")
          : inLayoutTable(nodeById(link.targetId)?.data.item) ? $t("graph.drop.moveLayoutTable")
          : inLayoutTable(nodeById(link.nodeId)?.data.item) ? $t("graph.drop.moveAfterLayoutTable")
          : $t("graph.drop.move")}
      </span>
    {/if}
  {/if}
  {#if notice}<p class="graph-notice" role="alert">{notice}</p>{/if}
  {#if menu}
    <GraphMenu x={menu.x} y={menu.y} {bounds} groups={menu.groups} onClose={closeMenu} />
  {/if}
</div>
