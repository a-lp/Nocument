<script>
  import { apiFetch } from "../api.js";
  import BackButton from "../components/BackButton.svelte";
  import Logo from "../components/Logo.svelte";
  import NavIcon from "../components/NavIcon.svelte";
  import WorkflowGuide from "../components/home/WorkflowGuide.svelte";
  import { t } from "../i18n.js";
  import { NAVIGATION_GROUPS } from "../navigation.js";

  export let navigate;

  // Answer of the backend test endpoint; null while loading, false if the backend does not answer.
  let backendMessage = null;

  apiFetch("/api/hello")
    .then((response) => response.json())
    .then((data) => {
      backendMessage = data.message;
    })
    .catch(() => {
      backendMessage = false;
    });

  // Opens the page of the feature through the client-side router, without reloading the page.
  function openFeature(event, path) {
    event.preventDefault();
    navigate(path);
  }
</script>

<div class="home-page">
  <div class="home-back"><BackButton /></div>
  <!-- The welcome is a page of a document: ruler above, letterhead, and title and subtitle set in the Title and
       Subtitle styles, whose names are shown in the left margin as in Word's style area. -->
  <header class="home-sheet">
    <div class="home-ruler" aria-hidden="true"></div>
    <div class="home-sheet-body">
      <div class="home-letterhead">
        <Logo className="home-logo" />
        <span>Nocument</span>
      </div>
      <div class="home-style-row">
        <span class="home-style-name" aria-hidden="true">{$t("home.styleTitle")}</span>
        <h1>{$t("home.title")}</h1>
      </div>
      <div class="home-style-row">
        <span class="home-style-name" aria-hidden="true">{$t("home.styleSubtitle")}</span>
        <p class="home-subtitle">{$t("home.subtitle")}</p>
      </div>
    </div>
  </header>

  <!-- How Nocument is used, step by step; then all the features, by group. -->
  <WorkflowGuide {navigate} />

  <h2 class="home-features-title" id="home-features-title">{$t("home.featuresTitle")}</h2>

  <!-- One row per group of the sidebar: its title and description, then a card per feature, in columns. -->
  {#each NAVIGATION_GROUPS as group, index (group.labelKey)}
    <section class="features" aria-labelledby={`feature-group-${index}`}>
      <header class="feature-group-heading">
        <span class="feature-group-icon"><NavIcon name={group.icon} className="" /></span>
        <div>
          <h2 id={`feature-group-${index}`}>{$t(group.labelKey)}</h2>
          <span class="feature-group-description">{$t(group.descriptionKey)}</span>
        </div>
      </header>
      <div class="feature-grid">
        {#each group.items as feature (feature.path)}
          <article class="feature">
            <div class="feature-icon">
              <NavIcon name={feature.icon} className="" />
            </div>
            <div class="feature-body">
              <p>{$t(group.labelKey)}</p>
              <h3>{$t(feature.labelKey)}</h3>
              <span>{$t(feature.descriptionKey)}</span>
              <a class="feature-button" href={feature.path} onclick={(event) => openFeature(event, feature.path)}>
                {$t("home.open", { feature: $t(feature.labelKey) })}
              </a>
            </div>
          </article>
        {/each}
      </div>
    </section>
  {/each}
</div>
