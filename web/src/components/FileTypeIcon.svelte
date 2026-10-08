<script>
  // Icon of a file type: white sheet with the format's abbreviation in its color (see .file-icon-* in app.css).
  export let type; // "pdf" | "word"
</script>

<svg class={`file-icon file-icon-${type}`} viewBox="0 0 24 24" aria-hidden="true">
  <path class="file-icon-page" d="M14 2H6a1.5 1.5 0 0 0-1.5 1.5v17A1.5 1.5 0 0 0 6 22h12a1.5 1.5 0 0 0 1.5-1.5V7.5z" />
  <path class="file-icon-fold" d="M14 2v5.5h5.5" />
  <text x="12" y="17.5" text-anchor="middle">{type === "pdf" ? "PDF" : "W"}</text>
</svg>
