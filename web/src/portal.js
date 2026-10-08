// Svelte action moving an element to the end of <body> (e.g. a dialog opened from inside a form or a modal): it is
// not nested in their forms and does not inherit their styles. Svelte still removes it when the component does.
export function portal(node) {
  document.body.appendChild(node);
  return {
    destroy() {
      node.remove();
    }
  };
}
