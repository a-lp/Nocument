// Runtime of the plugin interfaces (ui.svelte of a plugin package), loaded only when a plugin page is opened: the
// Svelte compiler is not part of the web app's main bundle, it comes with this module (a separate chunk).
// The interface is compiled in the browser and linked to the web app's own Svelte (the same instance, so stores,
// contexts and the components passed to it work together), then loaded as a module and mounted.
import { compile, VERSION } from "svelte/compiler";
import { mount, unmount } from "svelte";
import * as svelte from "svelte";
import * as animate from "svelte/animate";
import * as easing from "svelte/easing";
import * as events from "svelte/events";
import * as internalClient from "svelte/internal/client";
import "svelte/internal/disclose-version";
import "svelte/internal/flags/legacy";
import * as motion from "svelte/motion";
import * as reactivity from "svelte/reactivity";
import * as store from "svelte/store";
import * as transition from "svelte/transition";

// Modules an interface can import (the compiled code imports svelte/internal/* by itself).
const MODULES = {
  svelte,
  "svelte/animate": animate,
  "svelte/easing": easing,
  "svelte/events": events,
  "svelte/internal/client": internalClient,
  "svelte/motion": motion,
  "svelte/reactivity": reactivity,
  "svelte/store": store,
  "svelte/transition": transition
};
// Imported only for their effect, already applied by the web app.
const SIDE_EFFECT_MODULES = new Set(["svelte/internal/disclose-version", "svelte/internal/flags/legacy", "svelte/internal/flags/async"]);
const REGISTRY = "__nocumentPluginModules";

export const SVELTE_VERSION = VERSION;

globalThis[REGISTRY] = MODULES;

// Error of an interface, with the position in ui.svelte when known (line and column from 1).
export class PluginUiError extends Error {
  constructor(message, position = null) {
    super(message);
    this.position = position;
  }
}

// Compiled components, by source: reopening a plugin page does not compile again.
const cache = new Map();

// Component of the interface source (ui.svelte of the package), compiled and linked to the web app's Svelte.
export async function loadPluginComponent(source, packageName) {
  if (cache.has(source)) {
    return cache.get(source);
  }
  let compiled;
  try {
    compiled = compile(source, {
      generate: "client",
      css: "injected",
      filename: `${packageName}/ui.svelte`,
      name: "PluginUi",
      dev: false
    });
  } catch (error) {
    throw new PluginUiError(error.message, error.start ? { line: error.start.line, column: error.start.column + 1 } : null);
  }
  const url = URL.createObjectURL(new Blob([linkImports(compiled.js.code)], { type: "text/javascript" }));
  try {
    const module = await import(/* @vite-ignore */ url);
    cache.set(source, module.default);
    return module.default;
  } finally {
    URL.revokeObjectURL(url);
  }
}

// Mounts the component in target with the given props; returns the function that removes it.
export function mountPluginComponent(Component, target, props) {
  const instance = mount(Component, { target, props });
  return () => unmount(instance);
}

// Replaces the import declarations of the compiled code with the modules of the registry: the code is loaded from a
// blob URL, where bare specifiers like "svelte" could not be resolved.
function linkImports(code) {
  const declaration = /^\s*import\s+(?:([\w$*{}\s,]+?)\s+from\s+)?(['"])([^'"]+)\2\s*;?\s*$/gm;
  const linked = code.replace(declaration, (_match, clause, _quote, specifier) => {
    if (!clause) {
      if (SIDE_EFFECT_MODULES.has(specifier) || specifier in MODULES) {
        return "";
      }
      throw new PluginUiError(`The interface can only import svelte and its modules (it imports "${specifier}").`);
    }
    if (!(specifier in MODULES)) {
      throw new PluginUiError(`The interface can only import svelte and its modules (it imports "${specifier}").`);
    }
    const module = `globalThis.${REGISTRY}[${JSON.stringify(specifier)}]`;
    return importBindings(clause.trim(), module);
  });
  if (/^\s*import\s/m.test(linked) || /\bimport\s*\(/.test(linked)) {
    throw new PluginUiError("The interface can only import svelte and its modules.");
  }
  return linked;
}

// Variable declarations equivalent to an import clause: "X", "* as X", "{ a, b as c }" and their combinations.
function importBindings(clause, module) {
  const lines = [];
  let rest = clause;
  const namespace = /^\*\s+as\s+([\w$]+)$/.exec(rest);
  if (namespace) {
    return `const ${namespace[1]} = ${module};`;
  }
  const defaultName = /^([\w$]+)\s*(?:,\s*|$)/.exec(rest);
  if (defaultName && !rest.startsWith("{")) {
    lines.push(`const ${defaultName[1]} = ${module}.default;`);
    rest = rest.slice(defaultName[0].length).trim();
  }
  const namespaceAfterDefault = /^\*\s+as\s+([\w$]+)$/.exec(rest);
  if (namespaceAfterDefault) {
    lines.push(`const ${namespaceAfterDefault[1]} = ${module};`);
  } else if (rest.startsWith("{")) {
    const names = rest.slice(1, rest.lastIndexOf("}")).split(",").map((name) => name.trim()).filter(Boolean)
      .map((name) => name.replace(/^([\w$]+)\s+as\s+([\w$]+)$/, "$1: $2"));
    lines.push(`const { ${names.join(", ")} } = ${module};`);
  }
  return lines.join(" ");
}
