// Polyfills needed by pdf.js in older browsers (see pdfPolyfills.js).
import "./pdfPolyfills.js";
// Applies the color theme (CSS variables) before the app is mounted.
import "./theme.js";
import App from "./App.svelte";
import { mount } from "svelte";
// Fonts bundled with the app: Literata (titles, with optical sizes) and Schibsted Grotesk (interface).
import "@fontsource-variable/literata/opsz.css";
import "@fontsource-variable/schibsted-grotesk";
import "./app.css";

const app = mount(App, {
  target: document.getElementById("app")
});

export default app;
