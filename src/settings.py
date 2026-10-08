"""
Web app settings saved on the server and shared by all users, in a JSON file: NOCUMENT_SETTINGS if set, otherwise
instance/settings.json in the project root (in Docker, mount /app/instance as a volume to keep it).
Per-user preferences, such as the language, are saved in the browser instead.

The environment variables read by the backend, the plugins and Docker Compose are listed in ENVIRONMENT_VARIABLES
(same order and defaults as .env.example), shown read-only in the Settings page (environment_variables).
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import threading

SETTINGS_PATH = Path(os.getenv("NOCUMENT_SETTINGS") or Path(__file__).resolve().parent.parent / "instance" / "settings.json")
DEFAULTS = {"renderer": "libreoffice"}

_lock = threading.Lock()


def load_settings() -> dict:
    """Saved settings merged over DEFAULTS; a missing or unreadable file gives the defaults."""
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    return {**DEFAULTS, **{key: value for key, value in saved.items() if key in DEFAULTS}}


def save_settings(changes: dict) -> dict:
    """Saves changes over the current settings and returns the result."""
    with _lock:
        settings = {**load_settings(), **changes}
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = SETTINGS_PATH.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        # Replaced in one step: a concurrent reader never sees a half-written file.
        temporary_path.replace(SETTINGS_PATH)
    return settings


@dataclass(frozen=True)
class EnvironmentVariable:
    """
    Environment variable shown in the Settings page. group: section of .env.example ("compose", "database", "server",
    "logging", "renderers", "plugins", "azureDevOps"); default: value used when it is not set, None if found
    automatically (e.g. SOFFICE_PATH); secret: its value is never sent to the web app.
    """
    name: str
    group: str
    default: str | None
    secret: bool = False


# Keep in sync with .env.example; the description of each variable is in locales/ (settings.environment.variables).
ENVIRONMENT_VARIABLES = (
    EnvironmentVariable("NOCUMENT_PORT", "compose", "8080"),
    EnvironmentVariable("NOCUMENT_DEV_PORT", "compose", "5173"),
    EnvironmentVariable("NOCUMENT_DEV_ALLOWED_HOSTS", "compose", ""),
    EnvironmentVariable("MONGODB_DEV_PORT", "compose", "27017"),
    EnvironmentVariable("GUNICORN_WORKERS", "compose", "2"),
    EnvironmentVariable("MONGODB_URI", "database", ""),
    EnvironmentVariable("MONGODB_DATABASE", "database", "nocument"),
    EnvironmentVariable("NOCUMENT_DATABASE", "database", "instance/nocument.sqlite3"),
    EnvironmentVariable("NOCUMENT_STORAGE", "database", ""),
    EnvironmentVariable("NOCUMENT_SETTINGS", "server", "instance/settings.json"),
    EnvironmentVariable("NOCUMENT_BACKEND_PORT", "server", "5000"),
    EnvironmentVariable("NOCUMENT_BACKEND_HOST", "server", "127.0.0.1"),
    EnvironmentVariable("NOCUMENT_COMMIT", "server", None),
    EnvironmentVariable("NOCUMENT_COMMIT_DATE", "server", None),
    EnvironmentVariable("NOCUMENT_LOG_LEVEL", "logging", "INFO"),
    EnvironmentVariable("NOCUMENT_LOG_LEVELS", "logging", ""),
    EnvironmentVariable("NOCUMENT_LOG_FILE", "logging", "instance/logs/nocument.log"),
    EnvironmentVariable("NOCUMENT_LOG_MAX_BYTES", "logging", "5242880"),
    EnvironmentVariable("NOCUMENT_LOG_BACKUPS", "logging", "5"),
    EnvironmentVariable("SOFFICE_PATH", "renderers", None),
    EnvironmentVariable("SOFFICE_TIMEOUT", "renderers", "120"),
    EnvironmentVariable("UNO_PYTHON", "renderers", None),
    EnvironmentVariable("NOCUMENT_PLUGINS_DIR", "plugins", "plugins"),
    EnvironmentVariable("NOCUMENT_PLUGIN_UPLOAD", "plugins", "true"),
    EnvironmentVariable("AZURE_DEVOPS_URL", "azureDevOps", ""),
    EnvironmentVariable("AZURE_DEVOPS_TOKEN", "azureDevOps", "", secret=True),
)

# Password in a URI such as mongodb://user:password@host.
_URI_PASSWORD = re.compile(r"(//[^/:@]+:)[^/@]*@")


def environment_variables() -> list[dict]:
    """
    ENVIRONMENT_VARIABLES with their state in the backend process: [{"name", "group", "default", "set", "value",
    "secret"}]. set: the variable is defined (also when empty); value: its value, None if not set or secret
    (passwords in URIs are masked).
    """
    result = []
    for variable in ENVIRONMENT_VARIABLES:
        value = os.environ.get(variable.name)
        if value is not None and variable.secret:
            value = None
        elif value is not None:
            value = _URI_PASSWORD.sub(r"\1***@", value)
        result.append({
            "name": variable.name,
            "group": variable.group,
            "default": variable.default,
            "set": variable.name in os.environ,
            "value": value,
            "secret": variable.secret,
        })
    return result
