<script>
  import { onMount } from "svelte";
  import ConfirmDialog from "./components/ConfirmDialog.svelte";
  import Logo from "./components/Logo.svelte";
  import NavIcon from "./components/NavIcon.svelte";
  import { t } from "./i18n.js";
  import { FOOTER_ITEMS, LEGACY_PATHS, NAVIGATION_GROUPS } from "./navigation.js";
  import { initHistory, pushPath, restoreIndex } from "./history.js";
  import Home from "./pages/Home.svelte";
  import Settings from "./pages/Settings.svelte";
  import Compiler from "./pages/documents/Compiler.svelte";
  import DocumentBuilder from "./pages/documents/DocumentBuilder.svelte";
  import Templates from "./pages/documents/Templates.svelte";
  import AddContent from "./pages/content/AddContent.svelte";
  import ExploreContents from "./pages/content/ExploreContents.svelte";
  import InstallPlugin from "./pages/plugins/InstallPlugin.svelte";
  import PluginDetail from "./pages/plugins/PluginDetail.svelte";
  import Plugins from "./pages/plugins/Plugins.svelte";

  // Old links (e.g. bookmarks of /documenti/builder) open the translated path.
  if (LEGACY_PATHS[window.location.pathname]) {
    window.history.replaceState(window.history.state, "", LEGACY_PATHS[window.location.pathname]);
  }
  initHistory();
  let currentPath = window.location.pathname;

  // Full width pages (with their own sidebar) and ID of the block open in /content/edit/<id>.
  const FULL_WIDTH_PATHS = ["/documents/compiler", "/documents/builder", "/documents/templates", "/content/new", "/content/explore"];
  $: editedBlockId = currentPath.match(/^\/content\/edit\/([0-9a-f]{32})$/)?.[1] ?? null;
  // ID of the plugin open in /plugins/<id> ("install" is the installation page).
  $: pluginId = currentPath.match(/^\/plugins\/(?!install$)([a-z0-9][a-z0-9_-]*)$/)?.[1] ?? null;
  let sidebarCollapsed = false;

  // True if the sidebar item of the path is the current page: the page of a plugin (opened from "Installed
  // plugins", the plugins are not listed in the sidebar) highlights "Installed plugins".
  $: isActive = (path) => currentPath === path || (path === "/plugins" && pluginId !== null);

  // Updates the URL in the browser history and the page shown.
  function navigate(path) {
    pushPath(path);
    currentPath = path;
  }

  // Handles a click on an internal link without reloading the page.
  function handleNavigation(event, path) {
    event.preventDefault();
    navigate(path);
  }

  // Keeps the page shown in sync with the browser's back/forward buttons.
  onMount(() => {
    const handlePopState = (event) => {
      restoreIndex(event.state);
      currentPath = window.location.pathname;
    };

    window.addEventListener("popstate", handlePopState);

    return () => window.removeEventListener("popstate", handlePopState);
  });
</script>

<div class="shell">
  <aside class:collapsed={sidebarCollapsed} class="sidebar">
    <div class="sidebar-header">
      <a class="brand" href="/" onclick={(event) => handleNavigation(event, "/")}>
        <Logo />
        <span>Nocument</span>
      </a>
      <button
        class="sidebar-toggle"
        type="button"
        aria-label={sidebarCollapsed ? $t("nav.expandSidebar") : $t("nav.collapseSidebar")}
        title={sidebarCollapsed ? $t("nav.expandSidebar") : $t("nav.collapseSidebar")}
        aria-expanded={!sidebarCollapsed}
        onclick={() => (sidebarCollapsed = !sidebarCollapsed)}
      >
        <NavIcon name="menu" />
      </button>
    </div>

    <nav aria-label={$t("nav.main")}>
      <a class:active={currentPath === "/"} href="/" title={$t("nav.home")} onclick={(event) => handleNavigation(event, "/")}>
        <NavIcon name="home" />
        <span class="nav-label">{$t("nav.home")}</span>
      </a>
      <!-- Groups are only headings: their items are the clickable links. -->
      {#each NAVIGATION_GROUPS as group}
        <div class="nav-group" role="group" aria-label={$t(group.labelKey)}>
          <span class="nav-group-title" title={$t(group.labelKey)}>
            <NavIcon name={group.icon} />
            <span class="nav-label">{$t(group.labelKey)}</span>
          </span>
          {#each group.items as item}
            <a class="nav-subitem" class:active={isActive(item.path)} href={item.path} title={$t(item.labelKey)} onclick={(event) => handleNavigation(event, item.path)}>
              <NavIcon name={item.icon} />
              <span class="nav-label">{$t(item.labelKey)}</span>
            </a>
          {/each}
        </div>
      {/each}
    </nav>

    <!-- Configuration of the web app, at the bottom of the sidebar. -->
    <nav class="sidebar-footer" aria-label={$t("nav.footer")}>
      {#each FOOTER_ITEMS as item}
        <a class:active={currentPath === item.path} href={item.path} title={$t(item.labelKey)} onclick={(event) => handleNavigation(event, item.path)}>
          <NavIcon name={item.icon} />
          <span class="nav-label">{$t(item.labelKey)}</span>
        </a>
      {/each}
    </nav>
  </aside>

  <!-- Home takes the whole width and centers its contents (home-main); the full width pages have their own layout. -->
  <main class:word-main={FULL_WIDTH_PATHS.includes(currentPath) || editedBlockId} class:home-main={currentPath === "/"}>
    {#if currentPath === "/documents/compiler"}
      <Compiler {navigate} />
    {:else if currentPath === "/documents/builder"}
      <DocumentBuilder {navigate} />
    {:else if currentPath === "/documents/templates"}
      <Templates {navigate} />
    {:else if currentPath === "/content/new" || editedBlockId}
      <!-- key: going from a block to another (or to a new block) restarts the page from scratch. -->
      {#key currentPath}
        <AddContent blockId={editedBlockId} {navigate} />
      {/key}
    {:else if currentPath === "/content/explore"}
      <ExploreContents {navigate} />
    {:else if currentPath === "/plugins"}
      <Plugins {navigate} />
    {:else if currentPath === "/plugins/install"}
      <InstallPlugin {navigate} />
    {:else if pluginId}
      {#key pluginId}
        <PluginDetail {pluginId} {navigate} />
      {/key}
    {:else if currentPath === "/settings"}
      <Settings />
    {:else}
      <Home {navigate} />
    {/if}
  </main>
</div>

<!-- Confirmation of the operations (confirm.js), above every page. -->
<ConfirmDialog />
