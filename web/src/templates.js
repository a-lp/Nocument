// Document templates (GET/POST/DELETE /api/templates): Word files whose structure holds the preallocated nodes of
// the documents created from them.
import { apiFetch } from "./api.js";
import { tr } from "./i18n.js";

// Template to open in the Builder: { template (summary), edit }, set by the Templates page right before going to
// /documents/builder and taken (once) by the Builder when it starts, instead of restoring its session. With edit the
// Builder edits the template itself (Save template updates it), otherwise it creates a new document from it.
let pendingTemplate = null;

export function openTemplateInBuilder(template, { edit = false } = {}) {
  pendingTemplate = { template, edit };
}

export function takePendingTemplate() {
  const pending = pendingTemplate;
  pendingTemplate = null;
  return pending;
}

// Information of a template kept by the Builder while editing it.
export function templateInfo({ id, name, description, version }) {
  return { id, name, description, version };
}

// Saves a template from a Word file (Blob or File): origin "builder" for the document of the Builder, "import" for
// an uploaded file. Returns the summary of the saved template; throws an Error with the message to show.
export async function saveTemplate({ file, fileName, name, description, version, origin }) {
  const formData = templateForm({ file, fileName, name, description, version });
  formData.append("origin", origin);
  return sendTemplate("/api/templates", "POST", formData);
}

// Updates name, description and version of a template and, with file, its Word file. Returns the updated summary;
// throws an Error with the message to show.
export async function updateTemplate(templateId, { file = null, fileName = "", name, description, version }) {
  return sendTemplate(`/api/templates/${encodeURIComponent(templateId)}`, "PUT", templateForm({ file, fileName, name, description, version }));
}

function templateForm({ file, fileName, name, description, version }) {
  const formData = new FormData();
  if (file) {
    formData.append("file", file, fileName);
  }
  formData.append("name", name);
  formData.append("description", description);
  formData.append("version", version);
  return formData;
}

async function sendTemplate(url, method, body) {
  const response = await apiFetch(url, { method, body });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error || tr("templates.modal.saveError"));
  }
  return data;
}
