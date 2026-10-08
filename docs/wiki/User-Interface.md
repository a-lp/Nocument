# Pages and navigation

- `/` — Home: the welcome page (a Word page with ruler and style names), then the **workflow guide** (`WorkflowGuide`): five numbered steps, from the Word template to the external data, each with its explanation, a drawing and a link to the page where it is done (the step in view is marked on the rail while scrolling); at the bottom a row per group of the sidebar (Documents, Content, Plugins) with its title and description and a card per item, in columns
- `/documents/builder` — Builder: content graph, table of contents and insertion of headings, paragraphs, images and tables (see [Builder](Builder.md))
- `/documents/templates` — saved [templates](Templates.md): search, filters, import and creation of a document from a template
- `/documents/compiler` — Compiler: upload a `.docx`, PDF preview (pdf.js), keyword management and highlighting, content assignment and compilation (see [Compiler](Compiler.md))
- `/content/new` — creation of a [ContentBlock](Content-Blocks.md#add-new-content)
- `/content/edit/<id>` — editing of a saved ContentBlock, with the same page
- `/content/explore` — search and exploration of the [ContentBlocks](Content-Blocks.md#explore-contents)
- `/plugins` — installed [plugins](Plugins.md), with the files that could not be loaded
- `/plugins/install` — installation of a plugin script
- `/plugins/<id>` — page of a plugin, to try it
- `/settings` — [Settings](Settings.md) of the web app

**Confirmations** (deleting, closing a document, moving several elements, replacing a sheet or a plugin, ...) appear in the web app's own dialog (`ConfirmDialog`, `web/src/confirm.js`), not in the browser's: `await confirmAction(message, { title, action, danger })` returns `true` if confirmed. Destructive operations have a red button and the focus on *Cancel*; Esc or a click outside cancel.

The **back arrow** (`BackButton`, `web/src/history.js`) returns to the page opened before, like the browser's back button: it sits on the left of the title of the secondary sidebar or, on pages without one, at the top left of the page. It appears only when there is an earlier page of the web app in the history (not on the first page opened), also after a reload; it is hidden while choosing saved contents, which closes with *Cancel*.

In the navigation sidebar **Documents**, **Content** and **Plugins** are non-clickable groups containing their items (the installed plugins are listed only in the *Installed plugins* page, which stays highlighted on the page of a plugin); **Settings** is at the bottom. The sidebar can be collapsed with the hamburger button (☰): when collapsed it only shows the item icons. The Compiler keyword sidebar only appears when a document is loaded. All the secondary sidebars (Compiler keywords, Builder table of contents, *Add new content* and *Explore contents* sidebars) are resized by dragging their right border or, once it is focused, with the keyboard arrows; in the Builder and in the Content pages a double click on the border resets the initial width and the chosen width is remembered by the browser (`localStorage`). On narrow screens the sidebars go above the content and are not resized.
