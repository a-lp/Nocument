import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from docx import Document

from .render_interface import IRender
from ..compilers.docx_utils import find_toc_fields
from .toc_writer import write_toc

logger = logging.getLogger(__name__)
TOC_SCRIPT = Path(__file__).with_name("libreoffice_toc.py")

WINDOWS_SOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]


class LibreOfficeRenderImpl(IRender):
    """Converts to PDF with LibreOffice in headless mode (Docker, Linux, Windows)."""

    def __init__(self, soffice_path: str | None = None, timeout_seconds: int | None = None):
        """soffice_path: LibreOffice executable (default: automatic search); timeout_seconds: default SOFFICE_TIMEOUT or 120."""
        self.soffice_path = soffice_path or self.find_soffice()
        self.timeout_seconds = timeout_seconds or int(os.getenv("SOFFICE_TIMEOUT", "120"))
        # Python with LibreOffice's uno module, looked up at the first table of contents update (False = missing).
        self._uno_python: str | None | bool = None

    @staticmethod
    def is_available() -> bool:
        """True if the LibreOffice executable is found."""
        try:
            LibreOfficeRenderImpl.find_soffice()
        except RuntimeError:
            return False
        return True

    @staticmethod
    def find_soffice() -> str:
        """Looks for the LibreOffice executable in SOFFICE_PATH, in the PATH and in the standard Windows folders."""
        candidates = [os.getenv("SOFFICE_PATH"), shutil.which("soffice"), shutil.which("libreoffice"), *WINDOWS_SOFFICE_PATHS]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise RuntimeError("LibreOffice (soffice) not found. Install it or set SOFFICE_PATH.")

    def render_pdf(self, input_path: str, output_directory: str) -> str:
        """Converts input_path to PDF inside output_directory; raises RuntimeError if the conversion fails."""
        command = [
            self.soffice_path,
            "--headless",
            "--norestore",
            "--nolockcheck",
            f"-env:UserInstallation={self._profile_url(output_directory)}",
            "--convert-to",
            "pdf",
            "--outdir",
            output_directory,
            input_path,
        ]
        started = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout_seconds)
        _log_output("soffice", result)

        output_path = os.path.join(output_directory, f"{Path(input_path).stem}.pdf")
        if result.returncode != 0 or not os.path.isfile(output_path):
            raise RuntimeError(f"LibreOffice conversion failed ({result.returncode}): {result.stderr.strip()}")
        logger.info("Converted %s to PDF in %.1f s", Path(input_path).name, time.perf_counter() - started)
        return output_path

    def update_toc(self, document_path: str, working_directory: str) -> bool:
        """
        Lets LibreOffice compute the updated table of contents entries (script libreoffice_toc.py, run with a Python
        that has the uno module) and writes them into the document with python-docx. LibreOffice does not save the
        document, so the .docx keeps its original formatting.
        """
        python = self._find_uno_python()
        if not python:
            logger.warning("Table of contents update unavailable: no Python with LibreOffice's uno module.")
            return False

        document = Document(document_path)
        fields = find_toc_fields(document)
        if not fields:
            return True
        started = time.perf_counter()
        result = subprocess.run(
            [python, str(TOC_SCRIPT), self.soffice_path, os.path.abspath(document_path), self._profile_url(working_directory)],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        _log_output("libreoffice_toc", result)
        if result.returncode != 0:
            raise RuntimeError(f"Table of contents update failed ({result.returncode}): {result.stderr.strip()}")
        tables_of_contents = json.loads(result.stdout.strip().splitlines()[-1])
        # LibreOffice's tables of contents and the document's fields are in the same order.
        for field, entries in zip(fields, tables_of_contents):
            write_toc(document, field, entries)
        document.save(document_path)
        logger.info("Updated %d table(s) of contents of %s in %.1f s", len(fields), Path(document_path).name,
                    time.perf_counter() - started)
        return True

    @staticmethod
    def _profile_url(working_directory: str) -> str:
        """
        LibreOffice profile dedicated to the request: avoids conflicts between concurrent conversions. The table of
        contents update and the conversion of the same request share it, so only the first start creates it.
        """
        return (Path(working_directory) / "lo-profile").resolve().as_uri()

    def _find_uno_python(self) -> str | None:
        """
        Python with the uno module: UNO_PYTHON, the one bundled with LibreOffice (Windows) or the system one
        (Linux, package python3-uno). The result is cached.
        """
        if self._uno_python is None:
            program_directory = Path(self.soffice_path).resolve().parent
            candidates = [
                os.getenv("UNO_PYTHON"),
                str(program_directory / "python.exe"),
                str(program_directory / "python"),
                shutil.which("python3"),
                "/usr/bin/python3",
                sys.executable,
            ]
            self._uno_python = next((candidate for candidate in candidates if candidate and self._has_uno(candidate)), False)
        return self._uno_python or None

    @staticmethod
    def _has_uno(python: str) -> bool:
        """True if python can import the uno module."""
        if not os.path.isfile(python):
            return False
        try:
            return subprocess.run([python, "-c", "import uno"], capture_output=True, timeout=30).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False


def _log_output(program: str, result: subprocess.CompletedProcess) -> None:
    """Writes what a LibreOffice process printed in the log, at DEBUG (it is often noise, e.g. font warnings)."""
    for stream, text in (("stdout", result.stdout), ("stderr", result.stderr)):
        if text and text.strip():
            logger.debug("%s %s:\n%s", program, stream, text.strip())
