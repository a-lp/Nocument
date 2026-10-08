# PDF renderers

The `.docx` → PDF conversion goes through the `IRender` interface (`src/renderers/`). The renderer is chosen at runtime in [Settings](Settings.md) among those available on the server (`src/renderers/registry.py`); the default is LibreOffice. If the chosen renderer is not available (e.g. settings copied from Windows to Docker), the first available one is used and the backend logs it; with no renderer available the conversions fail with an error message, while the rest of the backend keeps working.

| Implementation          | Platform                         | Available when                                                     |
| ----------------------- | -------------------------------- | ------------------------------------------------------------------ |
| `LibreOfficeRenderImpl` | Docker, Linux, Windows           | `soffice` is found in `SOFFICE_PATH`, in the `PATH` or in the standard Windows folders |
| `WordRenderImpl`        | Windows with Microsoft Word only | `pywin32` is installed and Word is registered as a COM server. It uses a dedicated Word instance; conversions are serialized |

`IRender.update_toc` updates the tables of contents of the `.docx` (used by the Builder before the conversion):

- `WordRenderImpl` uses Word itself (`TablesOfContents.Update()`).
- `LibreOfficeRenderImpl` runs `src/renderers/libreoffice_toc.py` with a Python that has LibreOffice's `uno` module: the script opens the document, updates the indexes and returns the entries (level, numbering, heading, page), which `toc_writer.py` writes into the table of contents field of the `.docx` with python-docx (`TOC N` styles, links to the headings' bookmarks, pages as `PAGEREF` fields). LibreOffice does not save the document, so the template's formatting stays intact. The Python is looked up in `UNO_PYTHON`, among LibreOffice's programs (Windows) and in the system `python3` (Linux: package `python3-uno`, included in the Docker images); if it is missing, the table of contents is not updated and the backend logs it.

> With LibreOffice some templates do not show the page numbers of the second level entries in the PDF, even before the update: the right tab of the `TOC 2` style is beyond the right indent. In Word the table of contents is correct.

The variables of the renderers (`SOFFICE_PATH`, `SOFFICE_TIMEOUT`, `UNO_PYTHON`) are described in [Configuration](Configuration.md).
