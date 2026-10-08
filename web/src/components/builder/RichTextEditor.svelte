<script>
  import { Editor } from "@tiptap/core";
  import StarterKit from "@tiptap/starter-kit";
  import { onDestroy, onMount } from "svelte";
  import { t, tr } from "../../i18n.js";
  import { isSafeLink, normalizeLink } from "../../richText.js";
  import LinkDialog from "./LinkDialog.svelte";

  // Visual editor (TipTap) for paragraphs, table cells and Compiler texts: bold, italic, underline, strikethrough,
  // hyperlinks (toolbar button or Ctrl+K, see LinkDialog) and lists.
  // html: initial content; onChange receives the HTML at every change; label: accessible name of the text area.
  export let html = "";
  export let onChange = () => {};
  export let label = null;

  let element;
  let editor;
  // Increased at every transaction to update the active state of the toolbar buttons.
  let revision = 0;
  // Open link dialog: { url, withText, canRemove }, or null.
  let linkDialog = null;

  // The label of each action is the translation key editor.<name>.
  const ACTIONS = [
    { name: "bold", text: "B", run: (chain) => chain.toggleBold() },
    { name: "italic", text: "I", run: (chain) => chain.toggleItalic() },
    { name: "underline", text: "U", run: (chain) => chain.toggleUnderline() },
    { name: "strike", text: "S", run: (chain) => chain.toggleStrike() },
    { name: "bulletList", text: "•", run: (chain) => chain.toggleBulletList() },
    { name: "orderedList", text: "1.", run: (chain) => chain.toggleOrderedList() }
  ];

  onMount(() => {
    editor = new Editor({
      element,
      // Only what the backend can convert to Word (see src/builder/html_converter.py).
      extensions: [
        StarterKit.configure({
          heading: false,
          blockquote: false,
          code: false,
          codeBlock: false,
          horizontalRule: false,
          // Links: clicking edits them (it does not open them); addresses typed or pasted become links.
          link: {
            openOnClick: false,
            autolink: true,
            linkOnPaste: true,
            defaultProtocol: "https",
            protocols: ["mailto", "ftp"],
            isAllowedUri: (url) => isSafeLink(normalizeLink(url)),
            HTMLAttributes: { target: null, rel: null }
          }
        })
      ],
      content: html,
      editorProps: {
        attributes: { class: "rich-text-content", role: "textbox", "aria-multiline": "true", "aria-label": label ?? tr("editor.label") },
        handleKeyDown: (_view, event) => {
          if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
            event.preventDefault();
            openLinkDialog();
            return true;
          }
          return false;
        }
      },
      onTransaction: () => {
        revision += 1;
      },
      onUpdate: ({ editor: current }) => onChange(current.isEmpty ? "" : current.getHTML())
    });
  });

  onDestroy(() => editor?.destroy());

  // Runs a toolbar action keeping the focus in the editor.
  function runAction(action) {
    action.run(editor.chain().focus()).run();
  }

  // Opens the link dialog: on a link it edits it; without selected text it also asks for the text to insert.
  function openLinkDialog() {
    const href = editor.getAttributes("link").href ?? "";
    const onLink = editor.isActive("link");
    linkDialog = { url: href, withText: editor.state.selection.empty && !onLink, canRemove: onLink };
  }

  function applyLink({ url, text }) {
    const chain = editor.chain().focus();
    if (linkDialog.withText) {
      chain.insertContent({ type: "text", text: text || url, marks: [{ type: "link", attrs: { href: url } }] }).run();
    } else {
      chain.extendMarkRange("link").setLink({ href: url }).run();
    }
    linkDialog = null;
  }

  function removeLink() {
    editor.chain().focus().extendMarkRange("link").unsetLink().run();
    linkDialog = null;
  }
</script>

<div class="rich-text-editor">
  <div class="rich-text-toolbar" role="toolbar" aria-label={$t("editor.toolbar")}>
    {#each ACTIONS as action (action.name)}
      <button
        class={`rich-text-button rich-text-${action.name}`}
        class:active={revision >= 0 && editor?.isActive(action.name)}
        type="button"
        title={$t(`editor.${action.name}`)}
        aria-label={$t(`editor.${action.name}`)}
        aria-pressed={revision >= 0 && Boolean(editor?.isActive(action.name))}
        onmousedown={(event) => event.preventDefault()}
        onclick={() => runAction(action)}
      >
        {action.text}
      </button>
    {/each}
    <button
      class="rich-text-button rich-text-link"
      class:active={revision >= 0 && editor?.isActive("link")}
      type="button"
      title={$t("editor.linkHint")}
      aria-label={$t("editor.link")}
      aria-pressed={revision >= 0 && Boolean(editor?.isActive("link"))}
      onmousedown={(event) => event.preventDefault()}
      onclick={openLinkDialog}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1.2 1.2" /><path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2" /></svg>
    </button>
    <span class="rich-text-separator"></span>
    <button class="rich-text-button" type="button" title={$t("editor.undo")} aria-label={$t("editor.undo")} disabled={revision >= 0 && !editor?.can().undo()} onclick={() => editor.chain().focus().undo().run()}>↶</button>
    <button class="rich-text-button" type="button" title={$t("editor.redo")} aria-label={$t("editor.redo")} disabled={revision >= 0 && !editor?.can().redo()} onclick={() => editor.chain().focus().redo().run()}>↷</button>
  </div>
  <div bind:this={element}></div>
</div>

{#if linkDialog}
  <LinkDialog
    url={linkDialog.url}
    withText={linkDialog.withText}
    canRemove={linkDialog.canRemove}
    onApply={applyLink}
    onRemove={removeLink}
    onClose={() => {
      linkDialog = null;
      editor?.commands.focus();
    }}
  />
{/if}
