"""
Script run with a Python that has LibreOffice's uno module (e.g. /usr/bin/python3 with python3-uno, or the
python bundled with LibreOffice on Windows), not with the app's one: see LibreOfficeRenderImpl.update_toc.

Usage: python libreoffice_toc.py <soffice> <document.docx> <LibreOffice profile url>
Opens the document, updates the tables of contents and prints their entries as JSON, without saving the document:
[[{"level": 1, "text": "1\tScope\t4"}, ...], ...]  (one list per table of contents, in document order)
"""
import json
import os
import re
import subprocess
import sys
import time

import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.connection import NoConnectException

CONNECT_ATTEMPTS = 150
CONNECT_DELAY_SECONDS = 0.2
# Styles of the table of contents entries: "Contents N" in LibreOffice, "TOC N"/"toc N" in imported Word documents.
ENTRY_STYLE = re.compile(r"(?:contents|toc)\s*(\d+)$", re.IGNORECASE)


def connect(soffice: str, profile_url: str):
    """Starts LibreOffice listening on a dedicated pipe and returns (process, desktop)."""
    pipe = f"nocument_toc_{os.getpid()}"
    process = subprocess.Popen(
        [soffice, "--headless", "--invisible", "--norestore", "--nolockcheck", "--nodefault",
         f"-env:UserInstallation={profile_url}", f"--accept=pipe,name={pipe};urp;"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local_context)
    for _ in range(CONNECT_ATTEMPTS):
        try:
            context = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
            return process, context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)
        except NoConnectException:
            if process.poll() is not None:
                break
            time.sleep(CONNECT_DELAY_SECONDS)
    process.kill()
    raise RuntimeError("Cannot connect to LibreOffice.")


def index_entries(index) -> list[dict]:
    """Entries of an already updated table of contents: level (from the paragraph style) and text."""
    anchor = index.getAnchor()
    cursor = anchor.getText().createTextCursorByRange(anchor)
    entries = []
    paragraphs = cursor.createEnumeration()
    while paragraphs.hasMoreElements():
        paragraph = paragraphs.nextElement()
        if not paragraph.supportsService("com.sun.star.text.Paragraph"):
            continue
        match = ENTRY_STYLE.search(paragraph.ParaStyleName or "")
        text = paragraph.getString()
        # The table of contents title has another style and is left out.
        if match and text.strip():
            entries.append({"level": int(match.group(1)), "text": text})
    return entries


def main(soffice: str, document_path: str, profile_url: str) -> None:
    """Updates the document's tables of contents and prints their entries as JSON."""
    process, desktop = connect(soffice, profile_url)
    document = None
    try:
        hidden = PropertyValue()
        hidden.Name, hidden.Value = "Hidden", True
        document = desktop.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(document_path)), "_blank", 0, (hidden,))
        indexes = document.getDocumentIndexes()
        contents = [indexes.getByIndex(i) for i in range(indexes.getCount())]
        contents = [index for index in contents if index.supportsService("com.sun.star.text.ContentIndex")]
        # Two passes: the first can change the length of the table of contents and so the headings' pages.
        for _ in range(2):
            for index in contents:
                index.update()
        print(json.dumps([index_entries(index) for index in contents]))
    finally:
        if document is not None:
            document.close(True)
        try:
            desktop.terminate()
        except Exception:
            pass
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main(*sys.argv[1:4])
