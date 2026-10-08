// Confirmation of an operation in the web app's own dialog (ConfirmDialog, mounted once in App), instead of the
// browser's window.confirm. confirmAction returns a promise resolved with true (confirmed) or false (cancelled):
//   if (!(await confirmAction(message, { title, action, danger: true }))) return;
// title and action (label of the confirm button) are texts already translated; danger marks destructive operations
// (red button, focus on Cancel). Requests made while a dialog is open wait for their turn.
import { writable } from "svelte/store";

// Dialog shown: { message, title, action, danger, resolve }, or null.
export const currentConfirm = writable(null);
const queue = [];

export function confirmAction(message, { title = "", action = "", danger = false } = {}) {
  return new Promise((resolve) => {
    queue.push({ message, title, action, danger, resolve });
    if (queue.length === 1) {
      currentConfirm.set(queue[0]);
    }
  });
}

// Answer of the dialog shown; the next request in the queue, if any, is shown.
export function answerConfirm(confirmed) {
  const request = queue.shift();
  request?.resolve(confirmed);
  currentConfirm.set(queue[0] ?? null);
}
