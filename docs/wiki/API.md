# API

All the routes answer in the language given in `Accept-Language` (see [Localization](Localization.md)).

| Method | Route             | Input                     | Output            |
| ------ | ----------------- | ------------------------- | ----------------- |
| GET    | `/api/hello`      | —                         | test JSON         |
| GET    | `/api/version`    | —                         | `{"commit", "date"}`: git commit of the backend (`null` if unknown) |
| GET    | `/api/settings`   | —                         | `{"renderer", "renderers": [{"id", "available"}], "languages", "environment": [{"name", "group", "default", "set", "value", "secret"}]}` |
| PUT    | `/api/settings`   | JSON: `{"renderer": "libreoffice" \| "word"}` (only available renderers) | same as `GET` |
| POST   | `/api/render-pdf` | multipart, `file`: `.docx` | JSON: `{"pdf": "<base64>", "keywords": [...]}` |
| POST   | `/api/parse-csv`  | multipart, `file`: `.csv`  | JSON: `{"rows": [[...], ...], "has_header": true}` |
| POST   | `/api/compile`    | JSON (see below)          | JSON: `{"pdf": "<base64>", "docx": "<base64>"}` (compiled PDF and Word) |
| POST   | `/api/builder/open`   | multipart, `file`: `.docx` or `.dotx` | Builder JSON (see below) |
| POST   | `/api/builder/new`    | — | Builder JSON of an empty document |
| POST   | `/api/builder/template/<id>` | — | Builder JSON of a new document from the template; `404` if it does not exist |
| POST   | `/api/builder/insert` | JSON (see below)      | Builder JSON      |
| POST   | `/api/builder/update` | JSON like `insert`, with `target` instead of `after` (with `layout` for an element of a layout table) | Builder JSON |
| POST   | `/api/builder/move`   | JSON: `file`, `target` (blocks to move, `{"id", "anchor"}`) and `after` (`anchor` of the element to move them after, `null` = beginning) | Builder JSON |
| POST   | `/api/builder/delete` | JSON: `file` and `target`, or `targets` (list) for several elements; for an element of a layout table `target` includes `layout` | Builder JSON |
| POST   | `/api/builder/export` | JSON: `file` (the document returned by the other Builder routes), `pdf` (bool) | `{"docx": "<base64>"}` with the tables of contents updated and, with `pdf`, `"pdf": "<base64>"` |
| GET    | `/api/plugins`        | query `type` (only the plugins compatible with it) | `{"plugins": [{"id", "name", "description", "version", "file" (package folder or loose script), "compatibilities", "has_ui", "has_readme", "legacy"}], "errors": [{"file", "error"}], "upload_enabled"}` |
| GET    | `/api/plugins/<id>/ui` | — | source of the package's `ui.svelte` (text); `404` without it |
| GET    | `/api/plugins/<id>/readme` | — | the package's `README.md` (Markdown); `404` without it |
| GET    | `/api/plugins/<id>`   | — | the plugin with `parameters`: `{"<type>": [parameters]}` for each compatible type |
| GET    | `/api/plugins/<id>/parameters` | query `type` | `{"parameters": [{"name", "label", "type", "required", "default", "options", "minimum", "maximum", "help"}]}` |
| POST   | `/api/plugins/<id>/compile` | JSON: `{"type", "values": {"<parameter>": value}}` | `{"content": <content>}` in the format of the contents (`content_from_dict`); `400` for invalid values, `502` if the plugin fails |
| POST   | `/api/plugins`        | multipart, `files` (repeatable): a `.zip` with `plugin.py`, `ui.svelte`, `README.md`, or the three files; `replace=true` to overwrite | `201` `{"package", "plugins": [...]}`; `409` if the package exists, `403` if uploads are disabled |
| DELETE | `/api/plugins/files/<package>` | — | `204` (the package folder, or a loose script, is deleted); `404` if it does not exist |
| GET    | `/api/content-blocks` | query `skip`, `limit` (max 100), filters `title`, `description`, `source` (repeatable) and/or `manual=true` (alternative origins), `full=true` for the complete blocks | `{"items": [summaries or blocks], "total": n}` (`total` with the filters) |
| GET    | `/api/content-blocks/sources` | — | `{"sources": [import files]}` |
| POST   | `/api/content-blocks` | JSON: `title`, `description`, `source`, `contents` (and optional `id`) | `201` with the ContentBlock |
| GET    | `/api/content-blocks/<id>` | — | ContentBlock |
| PUT    | `/api/content-blocks/<id>` | JSON: `title`, `description`, `source`, `contents` | updated ContentBlock |
| DELETE | `/api/content-blocks/<id>` | — | `204` |
| GET    | `/api/content-blocks/styles` | — | styles of the default Word template (`StyleAnalyzer` format) |
| POST   | `/api/content-blocks/import` | multipart, `file`: `.docx` or `.dotx` | `{"title", "groups": [{"title", "contents"}], "styles", "warnings"}` (saves nothing) |
| GET    | `/api/templates` | query `skip`, `limit` (max 100), `search` (name or description), `origin` (`builder` or `import`, repeatable) | `{"items": [{"id", "name", "description", "version", "origin", "source", "created_at", "updated_at"}], "total": n}` |
| POST   | `/api/templates` | multipart: `file` (`.docx` or `.dotx`), `name` (required, max 120), `description` (max 1000), `version` (max 40), `origin` | `201` with the summary |
| GET    | `/api/templates/<id>` | — | summary of the template |
| PUT    | `/api/templates/<id>` | multipart: `name` (required), `description`, `version` and, optionally, `file` replacing the Word file | updated summary; `404` if it does not exist |
| GET    | `/api/templates/<id>/file` | — | the Word file of the template |
| DELETE | `/api/templates/<id>` | — | `204`; `404` if it does not exist |

Body of `/api/compile`: the document and, for each compiled keyword, the compiler class to use and its value.

```json
{
  "file": { "name": "document.docx", "content": "<docx in base64>" },
  "keywords": [
    { "keyword": "<REV>",  "class": "KeywordCompiler", "value": "B" },
    { "keyword": "<LOGO>", "class": "ImageCompiler",   "value": "<image in base64>" },
    { "keyword": "<TRCR>", "class": "TableCompiler",   "value": [["101", "Fix login"], ["102", "Export PDF"]] }
  ]
}
```

| Class             | Value                      | Effect                                                                                   |
| ----------------- | -------------------------- | ---------------------------------------------------------------------------------------- |
| `KeywordCompiler` | string, or `{"html": "..."}` (formatting and hyperlinks) | replaces the keyword with the text, keeping its formatting; the paragraphs of the HTML become line breaks |
| `ImageCompiler`   | base64 (PNG, JPEG, GIF, BMP, TIFF), or `{"data": base64, "width": cm}` | replaces the keyword with the image, with the given width or reduced if needed to the page width |
| `TableCompiler`   | list of rows of cells (strings or `{"html": "..."}`), or `{"rows": [...], "column_widths": [1, 3, ...]}` | the table row with the keyword is the template: filled with the first row and duplicated for the next ones. `column_widths` (positive numbers, one per cell of the template row) redistributes the column widths proportionally, keeping the total table width and setting a fixed layout |

`/api/parse-csv` uses `TableCompiler.read_csv`: it detects separator and encoding, drops empty rows and aligns all rows to the same number of cells; `has_header` tells whether the first row looks like a header. Selecting and reordering columns and rows happens in the frontend, which then sends the final rows to `/api/compile`.

The Builder routes (except `/api/builder/export`) return `{"name", "docx", "structure", "styles", "warnings"}`: document in base64, structure (`SectionAnalyzer`), styles (`StyleAnalyzer`) and warnings about the operation. Body of `/api/builder/insert` (`after` is the `anchor` of the element to insert after, `null` for the beginning of the document; instead of `content` there can be `contents`, a list of contents inserted together and in order, whose styles missing from the document are replaced with the default ones with a warning in `warnings`):

```json
{
  "file": { "name": "document.docx", "content": "<docx in base64>" },
  "after": 52,
  "content": { "type": "heading", "text": "Scope", "level": 2, "style": "Heading2", "formatting": { "color": "#C00000" } }
}
```

| `type`      | Fields                                                                                     |
| ----------- | ------------------------------------------------------------------------------------------ |
| `heading`   | `text`, `level` (1-9), `style`, `formatting` (`font`, `size`, `color`, `alignment`, `bold`, `italic`, `underline`) |
| `paragraph` | `html` (editor HTML: `p`, `strong`, `em`, `u`, `s`, `br`, `ul`/`ol`/`li`), `style`, `formatting` |
| `table`     | `rows`, `header`, `caption`, `caption_position` (`above`/`below`), `style`, `alignment` (`left`/`center`/`right`) |

`target` (`{"id": 49, "anchor": 49}`) gives the blocks taken by the element to edit or delete, as reported in the structure. In the structure headings and paragraphs also include `formatting` and `has_fields`, paragraphs `html` and `has_image`, tables `alignment`: they fill in the edit form.

In the ContentBlocks each content has the format of the table above, with a hexadecimal `"id"` (optional on input: generated if missing) and also the `image` type: `data` (base64 of a PNG, JPEG, GIF, BMP or TIFF), `filename`, `width` (cm), `alignment`. List summaries have `id`, `title`, `description`, `source`, `content_count`, `content_types`, `created_at` and `updated_at`, without the contents. An existing ID on creation returns `409`; an unreachable database `503`.

Validation or compilation errors return `400` with `{"error": "..."}`.
