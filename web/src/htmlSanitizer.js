// HTML of the paragraphs to show with {@html}: only the visual editor's tags are kept (see RichTextEditor and
// src/builder/html_converter.py), without attributes; links keep a safe address (web, e-mail, FTP) and open in a new
// tab. The content of scripts, styles and the like is removed.
import { isSafeLink } from "./richText.js";

const ALLOWED_TAGS = new Set(["P", "STRONG", "B", "EM", "I", "U", "S", "STRIKE", "DEL", "BR", "UL", "OL", "LI", "A"]);
const DROPPED_TAGS = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "EMBED", "TEMPLATE", "NOSCRIPT", "SVG", "MATH"]);

// Tags of documents such as the README of a plugin (Markdown rendered as HTML).
const DOCUMENT_TAGS = new Set([
  ...ALLOWED_TAGS, "H1", "H2", "H3", "H4", "H5", "H6", "BLOCKQUOTE", "PRE", "CODE", "HR", "TABLE", "THEAD", "TBODY",
  "TR", "TH", "TD", "KBD"
]);

// Returns the cleaned html.
export function sanitizeHtml(html) {
  return sanitizeWith(html, ALLOWED_TAGS);
}

// Returns the cleaned html of a document (headings, code, quotes and tables too), e.g. a plugin's README.
export function sanitizeDocumentHtml(html) {
  return sanitizeWith(html, DOCUMENT_TAGS);
}

function sanitizeWith(html, allowedTags) {
  const document = new DOMParser().parseFromString(`<body>${html ?? ""}</body>`, "text/html");
  clean(document.body, allowedTags);
  return document.body.innerHTML;
}

// Cleans the children of node: allowed tags without attributes, other tags replaced by their content.
function clean(node, allowedTags) {
  for (const child of [...node.childNodes]) {
    if (child.nodeType === Node.ELEMENT_NODE) {
      if (DROPPED_TAGS.has(child.tagName)) {
        child.remove();
        continue;
      }
      clean(child, allowedTags);
      if (allowedTags.has(child.tagName)) {
        const href = child.tagName === "A" ? child.getAttribute("href") : null;
        for (const attribute of [...child.attributes]) {
          child.removeAttribute(attribute.name);
        }
        if (child.tagName === "A") {
          if (!isSafeLink(href)) {
            child.replaceWith(...child.childNodes);
            continue;
          }
          child.setAttribute("href", href.trim());
          child.setAttribute("target", "_blank");
          child.setAttribute("rel", "noopener noreferrer");
        }
      } else {
        child.replaceWith(...child.childNodes);
      }
    } else if (child.nodeType !== Node.TEXT_NODE) {
      child.remove();
    }
  }
}
