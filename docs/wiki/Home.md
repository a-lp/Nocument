# Nocument wiki

Detailed documentation of Nocument. For an overview, the installation and the screenshots, see the [README](../../README.md).

## Using Nocument

- [Installation](Installation.md): Docker (production and development) and running on the host
- [Configuration](Configuration.md): all the environment variables
- [Compiler](Compiler.md): fill in the keywords of a Word document and get the PDF
- [Builder](Builder.md): build a document on its content graph
- [Templates](Templates.md): documents to start from, with preallocated contents
- [Content blocks](Content-Blocks.md): reusable headings, paragraphs, images and tables
- [Plugins](Plugins.md): contents from external data; using and installing them
- [Settings](Settings.md): language, themes, PDF renderer, version and environment
- [Pages and navigation](User-Interface.md): the pages of the web app, confirmations, sidebars

## Developing Nocument

- [Project structure](Project-Structure.md)
- [API](API.md): the REST routes of the backend
- [Compilers and analyzers](Compilers-and-Analyzers.md): how documents are read and compiled
- [PDF renderers](PDF-Renderers.md): LibreOffice and Word, and the tables of contents
- [Writing plugins](Writing-Plugins.md): `plugin.py`, `ui.svelte` and the plugin registry
- [Localization](Localization.md): translations and adding a language
- [Logging](Logging.md)
