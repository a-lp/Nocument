<script>
  // Icon of a navigation item: name is the icon key (see navigation.js).
  export let name;
  export let className = "nav-icon";
</script>

<svg class={className} viewBox="0 0 24 24" aria-hidden="true">
  {#if name === "home"}
    <path d="M3 10.5 12 3l9 7.5" />
    <path d="M5 9v12h5v-6h4v6h5V9" />
  {:else if name === "menu"}
    <path d="M4 6h16M4 12h16M4 18h16" />
  {:else if name === "folder"}
    <path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
  {:else if name === "builder"}
    <path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z" />
    <path d="M14 3v5h5" />
    <path d="M12 11v6M9 14h6" />
  {:else if name === "templates"}
    <rect x="4" y="3" width="16" height="18" rx="1" />
    <path d="M8 7h8M8 11h3M8 15h3" />
    <rect x="13" y="10" width="3" height="6" rx="0.5" />
  {:else if name === "content"}
    <rect x="4" y="4" width="16" height="5" rx="1" />
    <rect x="4" y="11" width="16" height="4" rx="1" />
    <path d="M4 19h10" />
  {:else if name === "add"}
    <rect x="4" y="4" width="16" height="16" rx="2" />
    <path d="M12 8v8M8 12h8" />
  {:else if name === "explore"}
    <circle cx="11" cy="11" r="6" />
    <path d="m20 20-4.5-4.5" />
  {:else if name === "settings"}
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
  {:else if name === "plugin"}
    <path d="M9 4h4v2.5a1.5 1.5 0 0 0 3 0V4h3a1 1 0 0 1 1 1v4h-2.5a1.5 1.5 0 0 0 0 3H20v7a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-7h2.5a1.5 1.5 0 0 0 0-3H4V5a1 1 0 0 1 1-1z" />
  {:else if name === "plugins"}
    <rect x="4" y="4" width="7" height="7" rx="1" />
    <rect x="13" y="4" width="7" height="7" rx="1" />
    <rect x="4" y="13" width="7" height="7" rx="1" />
    <rect x="13" y="13" width="7" height="7" rx="1" />
  {:else if name === "upload"}
    <path d="M12 16V4M7 9l5-5 5 5" />
    <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
  {:else if name === "compiler"}
    <path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z" />
    <path d="M14 3v5h5" />
    <circle cx="11" cy="14" r="2.5" />
    <path d="m13 16 2 2" />
  {/if}
</svg>
