"""
Translations of the texts shown in the web app. Each language has a file locales/<language>.json (shared with the
frontend) mapping keys to texts; nested objects group the keys, so "errors.invalidJson" is
{"errors": {"invalidJson": "..."}}. Texts may contain {name} placeholders and, for plurals, be an object
{"one": "...", "other": "..."} chosen by the "count" parameter.
"""
from contextvars import ContextVar
import json
from pathlib import Path

LOCALES_DIRECTORY = Path(__file__).resolve().parent.parent / "locales"
DEFAULT_LANGUAGE = "en"

TRANSLATIONS: dict[str, dict] = {
    path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(LOCALES_DIRECTORY.glob("*.json"))
}
LANGUAGES = list(TRANSLATIONS)

# Language of the request being served (see set_language): each request has its own context.
_current_language: ContextVar[str] = ContextVar("language", default=DEFAULT_LANGUAGE)


def set_language(language: str | None) -> None:
    """Uses language for the texts of the current request; unknown languages fall back to DEFAULT_LANGUAGE."""
    _current_language.set(language if language in TRANSLATIONS else DEFAULT_LANGUAGE)


def current_language() -> str:
    """Language of the current request."""
    return _current_language.get()


def t(key: str, **params) -> str:
    """
    Text of key in the current language (or in DEFAULT_LANGUAGE if missing there), with the placeholders replaced
    by params. Returns the key itself if no language defines it, so a missing translation stays visible.
    """
    value = _lookup(TRANSLATIONS.get(current_language(), {}), key)
    if value is None:
        value = _lookup(TRANSLATIONS.get(DEFAULT_LANGUAGE, {}), key)
    if value is None:
        return key
    if isinstance(value, dict):
        value = value["one"] if params.get("count") == 1 else value["other"]
    return value.format(**params) if params else value


def _lookup(translations: dict, key: str):
    """Value of a dotted key in the nested translations, or None."""
    value = translations
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value
