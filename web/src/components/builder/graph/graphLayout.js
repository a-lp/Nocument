// Document graph of the Builder: each node is a content (heading, paragraph, image, table) and each edge means
// "comes after it in the document, and moves with it". A section is a column on the right of its heading:
// - the contents of the section before its first subheading (paragraphs, images, tables) are a chain starting from
//   the heading: moving one of them moves it with the contents that follow it, up to the next heading (moveRange);
// - the subheadings are a second chain that also starts from the heading (not from the last paragraph, which they do
//   not follow as a content), each one with its own section; a heading moves with its whole section.
// The top level works the same way from the start node. Reading depth-first (first the section, then the sibling)
// gives the document order.

import { MarkerType } from "@xyflow/svelte";

export const NODE_WIDTH = 260;
export const NODE_HEIGHT = 76;
const COLUMN_STEP = NODE_WIDTH + 70;
const ROW_STEP = NODE_HEIGHT + 34;

// Start node: dragging from it inserts at the beginning of the document.
export const START_ID = "start";
// Key of the Svelte context with the graph actions for the nodes (see GraphCanvas.svelte).
export const GRAPH_CONTEXT = Symbol("builder-graph");

// Key of a structure element: text and images of the same paragraph have the same id but different types;
// the elements of a layout table all have the table's id and differ by their position.
export function itemKey(item) {
  return item.layout == null ? `${item.id}-${item.type}` : `${item.id}.${item.layout}-${item.type}`;
}

// True if the element is inside a layout table (see SectionAnalyzer): it is edited and deleted on its own
// (also giving its layout position), but it only moves together with the whole table.
export function inLayoutTable(item) {
  return item?.layout != null;
}

// Headings, tables and paragraphs can be edited, also inside a layout table; a paragraph with images cannot
// (the images would be lost).
export function isEditable(item) {
  return item.type === "heading" || item.type === "table" || (item.type === "paragraph" && !item.has_image);
}

// Position and suggested level for a content inserted after the node: after a heading a subheading is suggested,
// after a content a heading of the section's level; from the start node, the beginning of the document.
export function insertionAfter(node) {
  if (node.id === START_ID) {
    return { after: null, level: 1 };
  }
  const { item, sectionLevel } = node.data;
  return {
    after: item.anchor,
    level: item.type === "heading" ? Math.min(9, item.level + 1) : Math.max(1, sectionLevel)
  };
}

// Number of elements contained, at any depth, in the section of a heading.
export function descendantCount(item) {
  return item.type === "heading"
    ? item.children.reduce((total, child) => total + 1 + descendantCount(child), 0)
    : 0;
}

// Document blocks taken by the element ({ id, anchor }, see SectionAnalyzer): for a heading also its whole
// section, which moves with it.
export function itemRange(item) {
  let anchor = item.anchor;
  if (item.type === "heading") {
    for (const child of item.children) {
      anchor = Math.max(anchor, itemRange(child).anchor);
    }
  }
  return { id: item.id, anchor };
}

// Blocks moved together with the element of a node and how many elements they are ({ id, anchor, count }): a
// heading with its section, a content with the contents that follow it up to the next heading (its chain), an
// element of a layout table with the whole table.
export function moveRange(node) {
  return node.data.moveRange;
}

// Outcome of a drop on node target while dragging from node source: the link into target is replaced by
// source -> target, i.e. target with what moves with it (moveRange) goes right after source.
// "move": valid move; "noop": target already follows source; "invalid" (with reason, a translation key): not allowed.
export function relinkCheck(source, target, edges) {
  if (edges.some((edge) => edge.source === source.id && edge.target === target.id)) {
    return { state: "noop" };
  }
  if (source.id !== START_ID && inLayoutTable(source.data.item) && inLayoutTable(target.data.item)
      && source.data.item.id === target.data.item.id) {
    return { state: "invalid", reason: "graph.moveSameLayoutTable" };
  }
  if (source.id !== START_ID) {
    const { id, anchor } = moveRange(target);
    if (id <= source.data.item.id && source.data.item.id <= anchor) {
      return {
        state: "invalid",
        reason: target.data.item.type === "heading" ? "graph.moveIntoOwnSection" : "graph.moveIntoOwnChain"
      };
    }
  }
  return { state: "move" };
}

// Range moved with each element of a section's list (see moveRange): contents take the following contents up to
// the next heading; layout table elements stay with their table and are not part of the chains of the others.
function moveRanges(items) {
  return items.map((item, index) => {
    if (item.type === "heading" || inLayoutTable(item)) {
      return { ...itemRange(item), count: 1 + descendantCount(item) };
    }
    let end = index;
    while (end + 1 < items.length && items[end + 1].type !== "heading" && !inLayoutTable(items[end + 1])) {
      end += 1;
    }
    return { id: item.id, anchor: items[end].anchor, count: end - index + 1 };
  });
}

// Builds nodes and edges from the structure (tree of SectionAnalyzer). collapsed holds the keys (collapseKey) of
// the collapsed headings, whose sections are not shown. It also returns, for each heading (by itemKey), the keys of
// the headings containing it (to expand them when going to a hidden heading).
export function buildGraph(structure, collapsed) {
  const nodes = [{
    id: START_ID,
    type: "content",
    position: { x: 0, y: 0 },
    data: { kind: "start" }
  }];
  const edges = [];
  const headingAncestors = new Map();
  let row = 1;

  function walk(items, depth, sectionLevel, parentId, parentKey, ancestors, visible) {
    const ranges = moveRanges(items);
    // Last node of the chain of contents and of the chain of subheadings: each starts from the parent.
    let previousContentId = parentId;
    let previousHeadingId = parentId;
    for (const [index, item] of items.entries()) {
      const id = itemKey(item);
      // Key that stays the same from one edit to the next (block ids change): path of the headings.
      const collapseKey = item.type === "heading" ? `${parentKey}/${item.level}:${item.text}` : null;
      if (item.type === "heading") {
        headingAncestors.set(id, ancestors);
      }
      const hasSection = item.type === "heading" && item.children.length > 0;
      const isCollapsed = hasSection && collapsed.has(collapseKey);

      if (visible) {
        nodes.push({
          id,
          type: "content",
          position: { x: depth * COLUMN_STEP, y: row * ROW_STEP },
          data: {
            kind: "content",
            item,
            sectionLevel,
            collapseKey,
            hasSection,
            isCollapsed,
            hiddenCount: isCollapsed ? descendantCount(item) : 0,
            moveRange: ranges[index]
          }
        });
        // The first content and the first subheading of a section start from the right side of the heading; the
        // others follow the previous one of their chain from below.
        const previousId = item.type === "heading" ? previousHeadingId : previousContentId;
        const fromHeading = previousId === parentId && parentId !== START_ID;
        edges.push({
          id: `${previousId}->${id}`,
          source: previousId,
          target: id,
          sourceHandle: fromHeading ? "right" : "bottom",
          targetHandle: fromHeading ? "left" : "top",
          type: "smoothstep",
          class: fromHeading ? "section-edge" : "sequence-edge",
          markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 }
        });
        row += 1;
      }
      if (item.type === "heading") {
        walk(item.children, depth + 1, item.level, id, collapseKey, [...ancestors, collapseKey], visible && !isCollapsed);
        previousHeadingId = id;
      } else {
        previousContentId = id;
      }
    }
  }

  walk(structure, 0, 0, START_ID, "", [], true);
  return { nodes, edges, headingAncestors };
}

// Keys of all the headings with a non-empty section (for "Collapse all").
export function allSectionKeys(structure, parentKey = "", output = []) {
  for (const item of structure) {
    if (item.type === "heading") {
      const key = `${parentKey}/${item.level}:${item.text}`;
      if (item.children.length) {
        output.push(key);
      }
      allSectionKeys(item.children, key, output);
    }
  }
  return output;
}
