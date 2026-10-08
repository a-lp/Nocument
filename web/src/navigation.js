// Items of the main sidebar, also used by Home (one row per group, with its description, and a card per item).
// Labels and descriptions are translation keys (see i18n.js), translated by the components that show them.
export const NAVIGATION_GROUPS = [
  {
    labelKey: "nav.documents",
    icon: "folder",
    descriptionKey: "home.groups.documents",
    items: [
      {
        path: "/documents/builder",
        labelKey: "nav.builder",
        icon: "builder",
        descriptionKey: "home.features.builder"
      },
      {
        path: "/documents/templates",
        labelKey: "nav.templates",
        icon: "templates",
        descriptionKey: "home.features.templates"
      },
      {
        path: "/documents/compiler",
        labelKey: "nav.compiler",
        icon: "compiler",
        descriptionKey: "home.features.compiler"
      }
    ]
  },
  {
    labelKey: "nav.content",
    icon: "content",
    descriptionKey: "home.groups.content",
    items: [
      {
        path: "/content/new",
        labelKey: "nav.addContent",
        icon: "add",
        descriptionKey: "home.features.addContent"
      },
      {
        path: "/content/explore",
        labelKey: "nav.exploreContents",
        icon: "explore",
        descriptionKey: "home.features.exploreContents"
      }
    ]
  },
  {
    labelKey: "nav.plugins",
    icon: "plugin",
    descriptionKey: "home.groups.plugins",
    items: [
      {
        path: "/plugins",
        labelKey: "nav.installedPlugins",
        icon: "plugins",
        descriptionKey: "home.features.installedPlugins"
      },
      {
        path: "/plugins/install",
        labelKey: "nav.installPlugin",
        icon: "upload",
        descriptionKey: "home.features.installPlugin"
      }
    ]
  }
];

// Items at the bottom of the main sidebar (configuration of the web app).
export const FOOTER_ITEMS = [{ path: "/settings", labelKey: "nav.settings", icon: "settings" }];

// Old paths of the pages (before the translation and before the Analyzer was renamed Compiler), redirected to the
// new ones.
export const LEGACY_PATHS = {
  "/documenti/builder": "/documents/builder",
  "/documenti/analyzer": "/documents/compiler",
  "/documents/analyzer": "/documents/compiler"
};
