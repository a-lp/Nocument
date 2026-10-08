# Project structure

```text
.
├── compose.yaml                # production: app + MongoDB
├── compose.dev.yaml            # development: development image + MongoDB
├── Dockerfile                  # production image (nginx + gunicorn + LibreOffice)
├── Dockerfile.dev              # development image (Python + Node + LibreOffice)
├── docker/                     # nginx configuration and container start scripts
├── requirements.txt
├── locales/                    # translations, one file per language (en.json, it.json), shared by frontend and backend
├── scripts/
│   └── check_locales.py        # checks that every language has the same keys and that the keys used exist
├── instance/                   # server settings (settings.json) and SQLite database (nocument.sqlite3), not in git
├── templates/                  # sample Word template (business plan); local/ is ignored by git
├── docs/                       # screenshots/ (used in the README) and wiki/ (this documentation)
├── plugins/                    # installed plugin packages (plugin.py, ui.svelte, README.md each); sample_data/ is the example
├── src/
│   ├── app.py                  # Flask backend, analysis pipeline and settings routes
│   ├── i18n.py                 # t(): backend texts in the language of the request
│   ├── logging_setup.py        # centralized logging (console + rotating file) and capture of the plugins' print()
│   ├── settings.py             # server settings (load and save)
│   ├── sqlite_store.py         # SqliteStore: base of the SQLite repositories (connections, schema, errors)
│   ├── templates/
│   │   ├── template.py                 # DocumentTemplate and DocumentTemplateSummary
│   │   ├── repository.py               # ITemplateRepository, TemplateFilter and in-memory repository
│   │   ├── mongo_repository.py         # MongoTemplateRepository
│   │   ├── sqlite_repository.py        # SqliteTemplateRepository
│   │   └── api.py                      # REST routes /api/templates
│   ├── analyzers/
│   │   ├── analyzer_interface.py       # IAnalyzer
│   │   ├── keyword_analyzer.py         # KeywordAnalyzer: document keywords (configurable regex)
│   │   ├── section_analyzer.py         # SectionAnalyzer: section tree with block ids
│   │   └── style_analyzer.py           # StyleAnalyzer: heading, paragraph and table styles
│   ├── content_blocks/
│   │   ├── content_block.py            # ContentBlock and ContentBlockSummary
│   │   ├── builder.py                  # ContentBlockBuilder (builder pattern)
│   │   ├── repository.py               # IContentBlockRepository and in-memory repository
│   │   ├── mongo_repository.py         # MongoContentBlockRepository
│   │   ├── sqlite_repository.py        # SqliteContentBlockRepository (no database server)
│   │   ├── importer.py                 # contents of a Word document for a ContentBlock
│   │   ├── migrations.py               # migrations of the blocks in MongoDB (source file from the description)
│   │   └── api.py                      # REST routes /api/content-blocks
│   ├── builder/
│   │   ├── content_interface.py        # IDocumentContent and hexadecimal content IDs
│   │   ├── model.py                    # IContent, TextContent, ImageContent, Section
│   │   ├── word_table.py               # WordTable: content and caption of a table
│   │   ├── contents.py                 # NewHeading, NewParagraph, NewImage and content_from_dict
│   │   ├── document_builder.py         # DocumentBuilder: inserts, replaces, moves and deletes contents
│   │   ├── html_converter.py           # visual editor HTML -> Word paragraphs
│   │   ├── paragraph_reader.py         # Word paragraph -> HTML and formatting (for editing)
│   │   ├── formatting.py               # direct formatting (font, size, color...)
│   │   ├── styles.py                   # style lookup and caption style
│   │   └── docx_files.py               # .dotx template -> .docx conversion
│   ├── compilers/
│   │   ├── compiler_interface.py       # ICompiler
│   │   ├── document_compiler.py        # DocumentCompiler: finds keywords and applies the compilers
│   │   ├── keyword_compiler.py         # KeywordCompiler (text)
│   │   ├── image_compiler.py           # ImageCompiler (image)
│   │   ├── table_compiler.py           # TableCompiler (table rows, also from CSV)
│   │   └── docx_utils.py               # python-docx utilities (keyword runs, paragraph and block iteration, heading levels, layout tables)
│   ├── plugins/
│   │   ├── __init__.py                 # what the plugins import (IPlugin, PluginParameter, content classes...)
│   │   ├── plugin_interface.py         # IPlugin, PluginParameter, PluginError
│   │   ├── registry.py                 # PluginRegistry: discovery, compatibilities, run, install and remove
│   │   └── api.py                      # REST routes /api/plugins
│   └── renderers/
│       ├── render_interface.py         # IRender
│       ├── registry.py                 # available renderers and the one chosen in the settings
│       ├── libreoffice_render_impl.py  # LibreOfficeRenderImpl
│       ├── libreoffice_toc.py          # UNO script: updates the tables of contents and returns their entries
│       ├── toc_writer.py               # writes the entries into the table of contents field of the .docx
│       └── word_render_impl.py         # WordRenderImpl
└── web/                        # Svelte + Vite frontend
    ├── public/
    │   └── favicon.svg                     # icon of the web app (same drawing as Logo.svelte)
    └── src/
        ├── main.js
        ├── app.css                         # global styles
        ├── App.svelte                      # layout, navigation sidebar and client-side routing
        ├── i18n.js                         # language store and $t() / tr() translations
        ├── api.js                          # apiFetch: calls to the backend with the language
        ├── navigation.js                   # sidebar items (also used by the grid in Home) and old paths
        ├── sessionStore.js                 # Compiler and Builder sessions in IndexedDB (save, load, clear)
        ├── plugins.js                      # installed plugins store and plugin calls
        ├── templates.js                    # template saving and the template to open in the Builder
        ├── theme.js                        # light/dark mode and color themes (CSS variables), saved in the browser
        ├── htmlSanitizer.js                # paragraph HTML cleaned before showing it
        ├── components/
        │   ├── KeywordSidebar.svelte       # Compiler keyword sidebar
        │   ├── FileTypeIcon.svelte         # PDF and Word icons of the save buttons
        │   ├── FileDropZone.svelte         # upload screen with drag-and-drop (Compiler and Builder)
        │   ├── Logo.svelte                 # logo of Nocument (sidebar and Home)
        │   ├── NavIcon.svelte              # navigation item icons
        │   ├── SidebarResizer.svelte       # handle to resize the secondary sidebars
        │   ├── content/
        │   │   ├── ContentSheet.svelte     # A4 content sheet (drag-and-drop, +, editing; also preview only)
        │   │   ├── ImportContentsModal.svelte # choice of the content groups imported from Word
        │   │   ├── ContentPalette.svelte   # content types to drag (Add new content and Builder)
        │   │   └── dragTypes.js            # types of the data dragged onto the sheet
        │   ├── plugins/
        │   │   ├── PluginForm.svelte       # form drawn from the parameters of a plugin
        │   │   └── PluginPanel.svelte      # "From plugin" section of the content form
        │   ├── settings/
        │   │   └── AppearanceSettings.svelte # mode, theme of each mode and editor of the custom themes
        │   ├── templates/
        │   │   └── TemplateModal.svelte    # name, description and version of a template (save or import)
        │   ├── table/
        │   │   ├── TableEditor.svelte      # table grid: CSV, included columns, reordering, sorting
        │   │   └── tableModel.js           # grid model and final table rows
        │   └── builder/
        │       ├── TocPanel.svelte         # table of contents (headings only, collapsible)
        │       ├── graph/                  # Builder content graph (Svelte Flow)
        │       │   ├── BuilderGraph.svelte # Svelte Flow provider and heading centering
        │       │   ├── GraphCanvas.svelte  # graph, gestures (click, drag, right click) and menus
        │       │   ├── ContentNode.svelte  # node: a content of the document or the beginning of the document
        │       │   ├── GraphMenu.svelte    # context menu (add, edit, select, delete)
        │       │   └── graphLayout.js      # nodes and edges from the structure: sections as branches
        │       ├── ContentModal.svelte     # form of headings, paragraphs, images and tables (Builder and Content)
        │       ├── FormattingFields.svelte # direct formatting fields
        │       └── RichTextEditor.svelte   # paragraph visual editor (TipTap)
        └── pages/
            ├── Home.svelte                 # rows of feature cards, one per sidebar group
            ├── Settings.svelte             # Settings: language, appearance, PDF renderer and environment variables
            ├── plugins/
            │   ├── Plugins.svelte          # installed plugins and files not loaded
            │   ├── InstallPlugin.svelte    # installation with drag-and-drop or +
            │   └── PluginDetail.svelte     # page of a plugin, to try it
            ├── content/
            │   ├── AddContent.svelte       # Add new content and block editing: sidebar, sheet, import and save
            │   └── ExploreContents.svelte  # Explore contents: filters and list of the blocks with preview
            └── documents/
                ├── DocumentBuilder.svelte  # Builder: table of contents, content graph and content insertion
                ├── Templates.svelte        # Templates: search, filters, grid and import
                └── Compiler.svelte         # upload, PDF preview, keywords, contents and compilation
```
