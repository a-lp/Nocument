<script>
  // Logo of Nocument: a document with the corner folded and an "N" drawn as a small graph of connected nodes, like
  // the content graph of the Builder, in the accent colors of the theme. The same drawing, with the default colors,
  // is the favicon (web/public/favicon.svg).
  export let className = "logo";
</script>

<svg class={className} viewBox="0 0 32 32" aria-hidden="true">
  <path d="M7 2.5h13.5L28 10v17.5a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-23a2 2 0 0 1 2-2z" style="fill: var(--accent)" />
  <path d="M20.5 2.5V8.5a1.5 1.5 0 0 0 1.5 1.5H28z" style="fill: var(--sidebar-accent)" />
  <path d="M11 23.5V12.5l10 11V14" style="fill: none; stroke: var(--on-color)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
  <circle cx="11" cy="23.5" r="2.3" style="fill: var(--on-color)" />
  <circle cx="11" cy="12.5" r="2.3" style="fill: var(--on-color)" />
  <circle cx="21" cy="23.5" r="2.3" style="fill: var(--on-color)" />
  <circle cx="21" cy="14" r="2.3" style="fill: var(--on-color)" />
</svg>
