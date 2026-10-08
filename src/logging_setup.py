"""
Centralized logging of the backend: Flask, the services outside it (renderers, repositories, plugin registry) and the
plugins all write through the standard logging module, configured here once per process (configure_logging).

Every record goes to the console (stderr) and, unless disabled, to a rotating file. Configuration from the environment:
- NOCUMENT_LOG_LEVEL: minimum level (DEBUG, INFO, WARNING, ERROR), default INFO;
- NOCUMENT_LOG_LEVELS: levels of single loggers, e.g. "nocument.plugins=DEBUG,werkzeug=WARNING";
- NOCUMENT_LOG_FILE: log file, default instance/logs/nocument.log; empty to log only to the console;
- NOCUMENT_LOG_MAX_BYTES and NOCUMENT_LOG_BACKUPS: size of a file before rotation (default 5 MB) and number of old
  files kept (default 5).

Output written with print() while capture_output is active (e.g. by a plugin) becomes log records of the given
logger: one record per line, stdout at INFO and stderr at WARNING. The capture is per thread (context variable), so
concurrent requests do not mix their output.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import io
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading

LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(process)d] %(name)s: %(message)s"
DEFAULT_LOG_FILE = Path(__file__).resolve().parent.parent / "instance" / "logs" / "nocument.log"
# Root of the loggers of the services and plugins (e.g. nocument.plugins.<id>).
ROOT_LOGGER = "nocument"

_configured = False
_configure_lock = threading.Lock()
# Logger receiving the output written with print() in the current context, None outside capture_output.
_capture_target: ContextVar[logging.Logger | None] = ContextVar("capture_target", default=None)


def configure_logging(log_to_file: bool = True) -> None:
    """
    Configures the root logger (handlers, levels) and the output capture; later calls do nothing.
    log_to_file=False logs only to the console (e.g. in the watcher process of the Flask reloader, which must not
    keep the file open: on Windows an open file cannot be rotated).
    """
    global _configured
    with _configure_lock:
        if _configured:
            return
        _configured = True

        # The original streams: the console handler must not write through the capture (it would capture itself).
        console_stream = sys.__stderr__ or sys.stderr
        formatter = logging.Formatter(LOG_FORMAT)
        handlers: list[logging.Handler] = [logging.StreamHandler(console_stream)]

        log_file = os.getenv("NOCUMENT_LOG_FILE", str(DEFAULT_LOG_FILE)).strip() if log_to_file else ""
        file_error = None
        if log_file:
            try:
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                # delay: the file is opened at the first record, so a process that never logs (e.g. the parent of
                # the Flask reloader) does not keep it open and block the rotation on Windows.
                handlers.append(RotatingFileHandler(
                    log_file, maxBytes=_int_env("NOCUMENT_LOG_MAX_BYTES", 5 * 1024 * 1024),
                    backupCount=_int_env("NOCUMENT_LOG_BACKUPS", 5), encoding="utf-8", delay=True,
                ))
            except OSError as error:
                file_error = error

        root = logging.getLogger()
        root.setLevel(_level(os.getenv("NOCUMENT_LOG_LEVEL", "INFO"), logging.INFO))
        for handler in handlers:
            handler.setFormatter(formatter)
            root.addHandler(handler)
        # Libraries that are verbose at INFO; NOCUMENT_LOG_LEVELS can still change them.
        logging.getLogger("pymongo").setLevel(logging.WARNING)
        for item in os.getenv("NOCUMENT_LOG_LEVELS", "").split(","):
            name, _, level = item.partition("=")
            if name.strip() and level.strip():
                logging.getLogger(name.strip()).setLevel(_level(level, logging.INFO))

        sys.stdout = _CapturingStream(sys.stdout, logging.INFO)
        sys.stderr = _CapturingStream(sys.stderr, logging.WARNING)

        logger = logging.getLogger(ROOT_LOGGER)
        if file_error is not None:
            logger.warning("Cannot write the log file %s: %s. Logging only to the console.", log_file, file_error)
        else:
            logger.info("Logging at level %s%s", logging.getLevelName(root.level),
                        f" to the console and to {log_file}" if log_file else " to the console")


def get_logger(name: str) -> logging.Logger:
    """Logger of a service or plugin, under the nocument root (e.g. get_logger("plugins.sample-data"))."""
    return logging.getLogger(f"{ROOT_LOGGER}.{name}")


@contextmanager
def capture_output(logger: logging.Logger):
    """Turns what the code in the block writes with print() (stdout and stderr) into records of logger."""
    token = _capture_target.set(logger)
    try:
        yield
    finally:
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, _CapturingStream):
                stream.flush_pending()
        _capture_target.reset(token)


class _CapturingStream(io.TextIOBase):
    """
    Replaces sys.stdout or sys.stderr: inside capture_output the text becomes log records (one per complete line),
    otherwise it goes to the original stream unchanged.
    """

    def __init__(self, original, level: int):
        self._original = original
        self._level = level
        # Text not yet ending with a newline (print writes the text and the "\n" separately), per thread.
        self._pending = threading.local()

    def write(self, text: str) -> int:
        logger = _capture_target.get()
        if logger is None or getattr(self._pending, "emitting", False):
            return self._original.write(text) if self._original is not None else len(text)
        buffer = getattr(self._pending, "text", "") + text
        *lines, self._pending.text = buffer.split("\n")
        for line in lines:
            self._emit(logger, line)
        return len(text)

    def flush_pending(self) -> None:
        """Logs the last line without a newline, if any (end of a capture)."""
        logger = _capture_target.get()
        text = getattr(self._pending, "text", "")
        self._pending.text = ""
        if logger is not None and text:
            self._emit(logger, text)

    def _emit(self, logger: logging.Logger, line: str) -> None:
        """One record per line; a handler writing to stderr meanwhile goes to the original stream (no loops)."""
        line = line.rstrip("\r")
        if not line.strip():
            return
        self._pending.emitting = True
        try:
            logger.log(self._level, line)
        finally:
            self._pending.emitting = False

    def flush(self) -> None:
        if self._original is not None:
            self._original.flush()

    def isatty(self) -> bool:
        return bool(self._original is not None and self._original.isatty())

    def fileno(self) -> int:
        if self._original is None:
            raise io.UnsupportedOperation("fileno")
        return self._original.fileno()

    @property
    def encoding(self):
        return getattr(self._original, "encoding", "utf-8")

    def writable(self) -> bool:
        return True


def _level(value: str, default: int) -> int:
    """Level from its name (e.g. "debug"), or default if unknown."""
    level = logging.getLevelName(value.strip().upper())
    return level if isinstance(level, int) else default


def _int_env(name: str, default: int) -> int:
    """Integer environment variable, or default if missing or not valid."""
    try:
        return int(os.getenv(name, ""))
    except ValueError:
        return default
