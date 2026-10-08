// Rich text of the visual editor (RichTextEditor) outside paragraphs: table cells and Compiler text values.
// A value is plain text (a string) or rich text ({ html }) with formatting and hyperlinks; the backend writes both
// into the document (see src/builder/rich_text.py). Values stay plain text while they have no formatting, so
// existing tables, CSV imports and keywords like <NAME> keep working as before.

// Addresses accepted for hyperlinks: the same as the backend (web pages, e-mail, FTP).
const LINK_ADDRESS = /^(https?:\/\/|mailto:|ftp:\/\/)\S+$/i;

export function isSafeLink(href) {
  return LINK_ADDRESS.test((href ?? "").trim());
}

// Adds https:// to an address typed without scheme (e.g. "example.org"), and mailto: to an e-mail address.
export function normalizeLink(href) {
  const value = (href ?? "").trim();
  if (!value || isSafeLink(value)) {
    return value;
  }
  if (/^[^\s@/]+@[^\s@/]+\.[^\s@/]+$/.test(value)) {
    return `mailto:${value}`;
  }
  return `https://${value}`;
}

export function isRichValue(value) {
  return Boolean(value) && typeof value === "object" && typeof value.html === "string";
}

// Text of a value, without formatting (sorting, summaries, column names).
export function valueText(value) {
  if (!isRichValue(value)) {
    return value ?? "";
  }
  const document = new DOMParser().parseFromString(`<body>${value.html}</body>`, "text/html");
  return [...document.body.children].map((block) => block.textContent).join("\n") || document.body.textContent;
}

// HTML of a value for the editor: plain text becomes paragraphs (one per line), escaped.
export function valueHtml(value) {
  if (isRichValue(value)) {
    return value.html;
  }
  const escape = (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return (value ?? "").split("\n").map((line) => `<p>${escape(line)}</p>`).join("");
}

// Value from the editor's HTML: plain text if it is only paragraphs of text (no formatting, links or lists),
// otherwise { html }.
export function valueFromHtml(html) {
  const document = new DOMParser().parseFromString(`<body>${html ?? ""}</body>`, "text/html");
  const blocks = [...document.body.children];
  if (blocks.every((block) => block.tagName === "P" && block.children.length === 0)) {
    return blocks.map((block) => block.textContent).join("\n");
  }
  return { html };
}
