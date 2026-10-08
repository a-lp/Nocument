# Compilers and analyzers

How the backend reads a Word document (analyzers) and replaces its keywords (compilers).

## Compilers

The `.docx` is compiled in `src/compilers/` with python-docx. `DocumentCompiler` opens the document, looks for the keywords (body, tables including nested ones, content controls, headers and footers) and applies the associated compiler to each occurrence:

```python
compiler = DocumentCompiler("document.docx")
compiler.add_keyword("<REV>", KeywordCompiler("B"))
compiler.add_keyword("<LOGO>", ImageCompiler("logo.png", width=Cm(3)))
compiler.add_keyword("<TRCR>", TableCompiler([["101", "Fix login"], ["102", "Export PDF"]]))
# or from CSV: skips the header and keeps the third and first column, in this order
compiler.add_keyword("<TRCR>", TableCompiler.from_csv(open("data.csv", "rb").read(), columns=[2, 0]))
# with column proportions (1:3): the total width of the table does not change
compiler.add_keyword("<TRCR>", TableCompiler([["101", "Fix login"]], column_widths=[1, 3]))
compiler.compile("compiled.docx")   # False if the document cannot be opened; without argument it overwrites the original
```

Word often splits the text of a keyword over several runs with different formatting: the compilers join it back before replacing it (`docx_utils.isolate_keyword_runs`), so no formatting is lost.

Limits: keywords inside hyperlinks or text boxes are not found; in `TableCompiler` the other keywords in the template row are only compiled in the first row.

### Adding a content type

1. Create in `src/compilers/` a class implementing `ICompiler.compile(keyword, paragraph)`.
2. Add it to `build_compiler` in `src/app.py`, validating the value received in the JSON.
3. In the frontend, add the type to `COMPILER_CLASSES` and `contentLabels` in `web/src/pages/documents/Compiler.svelte`, with its field in the modal and its texts in `locales/`.

## Analyzers

On upload (`/api/render-pdf`) the document goes through `_analyze_document` in `src/app.py`: a pipeline of analyzers (`src/analyzers/`) implementing `IAnalyzer.analyze(document)` and keeping their result inside them.

| Analyzer          | Result                                                                                                      |
| ----------------- | ----------------------------------------------------------------------------------------------------------- |
| `KeywordAnalyzer` | `keywords`: keywords matching the regex given to the constructor (default `<NAME>`), without duplicates; returned to the frontend |
| `SectionAnalyzer` | `contents`: structure of the body (contents before the first heading and `Section`s with title, level, style and `TextContent`, `WordTable`, `ImageContent` or nested `Section` contents). Each element has an `id` (index of the block in the body) and an `anchor` (block to insert after); used by the Builder and by *Import from Word*. Headings are paragraphs with an outline level, with a "Heading N" style and with the **Title** (level 1) and **Subtitle** (level 2) styles, also through derived styles. **Layout tables** (tables containing headings, used by templates like `business_plan.docx` to place the text in cells) are opened: the content of the cells is read in order as headings, paragraphs, images and tables; these elements have the table's `id` and `anchor` and in `layout` their position inside it, which `/api/builder/update` and `/api/builder/delete` use to edit or delete only that element |
| `StyleAnalyzer`   | visible styles of the document split into headings (with level), paragraphs and tables, caption style and default styles; used by the Builder |

If the analysis fails, the preview is returned anyway with an empty keyword list.

To recognize other keyword formats (e.g. also `@name`) just pass a different regex:

```python
keyword_analyzer = KeywordAnalyzer(r"<\s*[A-Za-z][^<>]*?>|@[A-Za-z][A-Za-z0-9_-]*")
```

### Adding an analyzer

1. Create in `src/analyzers/` a class implementing `IAnalyzer.analyze(document)` and saving its result in an attribute.
2. Add it to the `pipeline` in `_analyze_document` (`src/app.py`) and, if the frontend needs it, include the result in the response of `/api/render-pdf`.
