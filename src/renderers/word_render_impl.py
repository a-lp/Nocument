import os
from pathlib import Path
import sys
import threading

from .render_interface import IRender

WD_FORMAT_PDF = 17

# Word via COM does not handle parallel conversions well: they are serialized.
_word_lock = threading.Lock()


class WordRenderImpl(IRender):
    """Converts to PDF with Microsoft Word via COM (Windows only)."""

    def __init__(self):
        """Loads pywin32; raises RuntimeError if it is not available."""
        # Local import: pywin32 only exists on Windows, so the module stays importable elsewhere (e.g. Docker).
        try:
            import pythoncom
            import win32com.client
        except ImportError as error:
            raise RuntimeError("WordRenderImpl requires Windows with Microsoft Word and pywin32 installed.") from error
        self._pythoncom = pythoncom
        self._win32com_client = win32com.client

    @staticmethod
    def is_available() -> bool:
        """True on Windows with pywin32 installed and Word registered as a COM server."""
        if sys.platform != "win32":
            return False
        try:
            import pythoncom  # noqa: F401
            import win32com.client  # noqa: F401
            import winreg

            # Word registers its COM class in the registry: no need to start it.
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"))
        except (ImportError, OSError):
            return False
        return True

    def render_pdf(self, input_path: str, output_directory: str) -> str:
        """Converts input_path to PDF inside output_directory with a dedicated Word instance."""
        input_path = os.path.abspath(input_path)
        output_path = os.path.abspath(os.path.join(output_directory, f"{Path(input_path).stem}.pdf"))

        with _word_lock:
            # Every Flask thread must initialize COM before using it.
            self._pythoncom.CoInitialize()
            word = None
            document = None
            try:
                # DispatchEx starts a dedicated instance: Quit() does not close the Word the user has open.
                word = self._win32com_client.DispatchEx("Word.Application")
                word.Visible = False
                word.DisplayAlerts = 0
                document = word.Documents.Open(input_path, ReadOnly=True, AddToRecentFiles=False)
                document.SaveAs(output_path, FileFormat=WD_FORMAT_PDF)
            finally:
                if document is not None:
                    document.Close(SaveChanges=False)
                if word is not None:
                    word.Quit()
                self._pythoncom.CoUninitialize()

        if not os.path.isfile(output_path):
            raise RuntimeError("Word conversion failed: PDF not created.")
        return output_path

    def update_toc(self, document_path: str, working_directory: str) -> bool:
        """Updates the tables of contents with Word itself and saves the document."""
        with _word_lock:
            self._pythoncom.CoInitialize()
            word = None
            document = None
            try:
                word = self._win32com_client.DispatchEx("Word.Application")
                word.Visible = False
                word.DisplayAlerts = 0
                # Opened for writing and without conversion dialogs: the document is saved with the updated table.
                document = word.Documents.Open(
                    os.path.abspath(document_path), ConfirmConversions=False, ReadOnly=False, AddToRecentFiles=False
                )
                # Update recomputes entries (including new headings), numbering, links and page numbers.
                for index in range(1, document.TablesOfContents.Count + 1):
                    document.TablesOfContents(index).Update()
                document.Save()
            finally:
                if document is not None:
                    document.Close(SaveChanges=False)
                if word is not None:
                    word.Quit()
                self._pythoncom.CoUninitialize()
        return True
