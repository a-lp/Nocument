# Logging

The whole backend logs through Python's `logging`, configured once by `src/logging_setup.py` (`configure_logging`, called by `src/app.py` before creating the Flask app): Flask and its requests, the services outside Flask (renderers, repositories, plugin registry) and the plugins. Every record goes to the console and to the rotating file `instance/logs/nocument.log` (in Docker production in the `nocument-settings` volume, with the settings), in the format:

```text
2026-10-07 10:57:05,403 INFO     [1498] nocument.plugins.registry: Running noisy (Noisy) for a table with {'token': '***', 'q': 'ok'}
```

- **Loggers**: the services use `logging.getLogger(__name__)` or `get_logger("<name>")` (logger `nocument.<name>`); each plugin has `self.logger` (`nocument.plugins.<id>`).
- **`print()` in plugins**: while the registry loads or runs a plugin (loading of the file, `__init__`, `parameters`, `compile_*`), what it prints becomes records of its logger, one per line: stdout at `INFO`, stderr at `WARNING`. The capture is per thread, so the output of concurrent requests does not mix; `print()` elsewhere goes to the console as usual.
- **What is logged**: plugin files loaded and unloaded, every plugin run with its parameters (values of `password` parameters as `***`) and duration, `PluginError` messages (`WARNING`) and unexpected errors with their traceback (`ERROR`); LibreOffice conversions and table of contents updates with their duration, and the output of LibreOffice at `DEBUG`.
- **Configuration** (see `.env.example`): `NOCUMENT_LOG_LEVEL` (default `INFO`), `NOCUMENT_LOG_LEVELS` for single loggers (e.g. `nocument.plugins.azure-devops-query=DEBUG,werkzeug=WARNING`), `NOCUMENT_LOG_FILE` (empty: console only), `NOCUMENT_LOG_MAX_BYTES` and `NOCUMENT_LOG_BACKUPS` for the rotation.

With `python -m src.app` the Flask reloader runs two processes: only the one serving the requests writes the file (on Windows an open file cannot be rotated). With several gunicorn workers all write the same file: lines are not lost, but at the moment of a rotation a worker may keep writing to the renamed file until its next record.
