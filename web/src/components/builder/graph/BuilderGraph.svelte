<script>
  import { SvelteFlowProvider } from "@xyflow/svelte";
  import GraphCanvas from "./GraphCanvas.svelte";

  // Content graph of the Builder. The provider lets GraphCanvas use useSvelteFlow (e.g. to center a node).
  // The props are those of GraphCanvas.
  let props = $props();
  let canvas;

  // Centers the heading with the given key in the graph (see GraphCanvas.focusHeading).
  export function focusHeading(headingKey) {
    return canvas?.focusHeading(headingKey);
  }
</script>

<SvelteFlowProvider>
  <GraphCanvas bind:this={canvas} {...props} />
</SvelteFlowProvider>
