// Transfer of the open document between the Builder and the Compiler (e.g. to fill in the keywords of a document
// built in the Builder, and bring it back). The sending page calls transferDocument; the receiving one, when it
// starts, takes the document with takeTransferredDocument and opens it instead of restoring its session (which it
// then replaces). If the receiving page already has a document open (in its session), the user confirms first.
import { confirmAction } from "./confirm.js";
import { tr } from "./i18n.js";
import { loadSession } from "./sessionStore.js";

const DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
// Page and session key of each side ("analyzer" is the Compiler session, named before the rename).
const TARGETS = {
  builder: { path: "/documents/builder", sessionKey: "builder", nameKey: "nav.builder" },
  compiler: { path: "/documents/compiler", sessionKey: "analyzer", nameKey: "nav.compiler" }
};

// Document waiting to be opened: { target, file }.
let pending = null;

// Sends the Word document (Blob or File) with the given name to target ("builder" or "compiler") and opens that
// page. Returns false if the user keeps the document already open there.
export async function transferDocument(target, blob, fileName, navigate) {
  const { path, sessionKey, nameKey } = TARGETS[target];
  let session = null;
  try {
    session = await loadSession(sessionKey);
  } catch {
    // Without the session nothing is overwritten.
  }
  if (session?.file) {
    const confirmed = await confirmAction(
      tr("transfer.confirmReplace", { section: tr(nameKey), open: session.fileName, name: fileName }),
      { title: tr("transfer.confirmTitle", { section: tr(nameKey) }), action: tr("transfer.replace"), danger: true }
    );
    if (!confirmed) {
      return false;
    }
  }
  pending = { target, file: new File([blob], fileName, { type: DOCX_MIME_TYPE }) };
  navigate(path);
  return true;
}

// The document sent to target, once (null if there is none).
export function takeTransferredDocument(target) {
  if (pending?.target !== target) {
    return null;
  }
  const { file } = pending;
  pending = null;
  return file;
}
