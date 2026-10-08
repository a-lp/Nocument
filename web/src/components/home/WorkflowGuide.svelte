<script>
  import { onDestroy, onMount } from "svelte";
  import { t } from "../../i18n.js";
  import FileTypeIcon from "../FileTypeIcon.svelte";
  import Logo from "../Logo.svelte";

  // Guide of the Home page: the five steps of the workflow of Nocument, in order, each with its text, a link to the
  // page where it is done and a small drawing of it (made with the theme colors, so it follows light, dark and
  // custom themes). The step in view is marked on the rail while the page scrolls.
  export let navigate;

  const STEPS = [
    { id: "template", path: "/documents/templates" },
    { id: "components", path: "/content/new" },
    { id: "build", path: "/documents/builder" },
    { id: "keywords", path: "/documents/compiler" },
    { id: "plugins", path: "/plugins/install" }
  ];

  let list;
  let activeStep = "template";
  let observer;

  // The step closest to the middle of the window is the active one.
  onMount(() => {
    observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting);
        if (visible.length) {
          activeStep = visible[0].target.dataset.step;
        }
      },
      { rootMargin: "-45% 0px -45% 0px" }
    );
    for (const step of list.querySelectorAll("[data-step]")) {
      observer.observe(step);
    }
  });

  onDestroy(() => observer?.disconnect());

  function open(event, path) {
    event.preventDefault();
    navigate(path);
  }
</script>

<section class="workflow" aria-labelledby="workflow-title">
  <header class="workflow-heading">
    <h2 id="workflow-title">{$t("home.workflow.title")}</h2>
    <span>{$t("home.workflow.intro")}</span>
  </header>

  <ol class="workflow-steps" bind:this={list}>
    {#each STEPS as step, index (step.id)}
      <li class="workflow-step" class:active={activeStep === step.id} data-step={step.id}>
        <span class="workflow-number" aria-hidden="true">{index + 1}</span>
        <div class="workflow-text">
          <h3>{$t(`home.workflow.steps.${step.id}.title`)}</h3>
          <p>{$t(`home.workflow.steps.${step.id}.text`)}</p>
          <a class="workflow-link" href={step.path} onclick={(event) => open(event, step.path)}>{$t(`home.workflow.steps.${step.id}.action`)}</a>
        </div>

        <!-- Drawings of the steps: decoration that repeats the text, hidden from screen readers. -->
        <div class="workflow-figure" aria-hidden="true">
          {#if step.id === "template"}
            <!-- The template is a Word file, made in Microsoft Word and uploaded to Nocument; below, its styles. -->
            <div class="figure-styles">
              <span class="figure-upload">
                <span class="word-tile"><FileTypeIcon type="word" /></span>
                <span class="figure-file">{$t("home.workflow.figure.templateFile")}</span>
                <span class="upload-arrow">→</span>
                <Logo className="figure-logo" />
              </span>
              <span class="style-sample style-title">Title</span>
              <span class="style-sample style-heading">Heading 1</span>
              <span class="style-sample style-normal">Normal</span>
              <span class="style-table"><i></i><i></i><i></i><i></i><i></i><i></i></span>
              <span class="style-caption">Table Grid</span>
            </div>
          {:else if step.id === "components"}
            <div class="figure-reuse">
              {#each [0, 1, 2] as page (page)}
                <span class="mini-page">
                  <i class="line short"></i>
                  <span class="mini-block"><i class="line heading"></i><i class="line"></i><i class="line"></i><i class="mini-image"></i></span>
                  <i class="line"></i>
                  <i class="line short"></i>
                </span>
              {/each}
            </div>
          {:else if step.id === "build"}
            <!-- A heading with its paragraph, a second heading with its table and a component being added. -->
            <div class="figure-graph">
              <span class="node heading at-1-1">H</span>
              <span class="edge horizontal at-1-2"></span>
              <span class="node at-1-3">¶</span>
              <span class="edge vertical at-2-1"></span>
              <span class="node heading at-3-1">H</span>
              <span class="edge horizontal at-3-2"></span>
              <span class="node table at-3-3">▦</span>
              <span class="edge horizontal dashed at-3-4"></span>
              <span class="node new at-3-5">+</span>
            </div>
          {:else if step.id === "keywords"}
            <div class="figure-keywords">
              <span class="keyword-line">{$t("home.workflow.figure.release")} <mark>&lt;VERSION&gt;</mark></span>
              <span class="keyword-arrow">↓</span>
              <span class="keyword-line">{$t("home.workflow.figure.release")} <strong>2.4.0</strong></span>
              <span class="keyword-line muted"><mark>&lt;DATE&gt;</mark> → 08/10/2026</span>
            </div>
          {:else}
            <div class="figure-plugin">
              <!-- One element per line: whitespace inside code would be collapsed. -->
              <code>
                <span class="code-line"><span class="code-key">def</span> compile_table(self, values):</span>
                <span class="code-line indent">rows = tasks.query(values)</span>
                <span class="code-line indent"><span class="code-key">return</span> self.table(rows)</span>
              </code>
              <span class="plugin-arrow">↓</span>
              <span class="style-table wide"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
            </div>
          {/if}
        </div>
      </li>
    {/each}
  </ol>
</section>
