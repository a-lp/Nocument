<script>
  import { tick } from "svelte";
  import { t } from "../i18n.js";
  import { answerConfirm, currentConfirm } from "../confirm.js";

  // Dialog of confirmAction (see confirm.js). The focus goes to the confirm button, or to Cancel for destructive
  // operations, stays inside the dialog (Tab) and goes back where it was when the dialog closes; Esc and a click
  // outside cancel.
  let dialog;
  let cancelButton;
  let confirmButton;
  let previousFocus = null;

  $: request = $currentConfirm;
  $: if (request) {
    focusDialog(request);
  }

  async function focusDialog(shown) {
    previousFocus ??= document.activeElement;
    await tick();
    (shown.danger ? cancelButton : confirmButton)?.focus();
  }

  async function answer(confirmed) {
    const focus = previousFocus;
    previousFocus = null;
    answerConfirm(confirmed);
    await tick();
    // Another request may have opened the dialog again: the focus stays in it.
    if (!$currentConfirm && focus?.isConnected) {
      focus.focus();
    }
  }

  function handleKeydown(event) {
    if (!request) {
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      answer(false);
    } else if (event.key === "Tab") {
      const buttons = [cancelButton, confirmButton];
      const index = buttons.indexOf(document.activeElement);
      event.preventDefault();
      buttons[(index + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length].focus();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if request}
  <div class="keyword-modal-backdrop confirm-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && answer(false)}>
    <div
      bind:this={dialog}
      class="confirm-dialog"
      class:danger={request.danger}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-message"
    >
      <h2 id="confirm-dialog-title">{request.title || $t("confirm.defaultTitle")}</h2>
      <span id="confirm-dialog-message" class="confirm-message">{request.message}</span>
      <div class="confirm-actions">
        <button bind:this={cancelButton} class="secondary-button" type="button" onclick={() => answer(false)}>{$t("common.cancel")}</button>
        <button bind:this={confirmButton} class="confirm-button" type="button" onclick={() => answer(true)}>
          {request.action || $t("confirm.defaultAction")}
        </button>
      </div>
    </div>
  </div>
{/if}
