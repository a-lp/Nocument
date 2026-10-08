"""
Checks the translations in locales/: every language must define the same keys (and the same {placeholders}),
and every key used in the code with t("...") / $t("...") must exist.

Usage: python scripts/check_locales.py   (exit code 1 if something is missing)
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
# t("key"), $t("key"), tr("key"): literal keys only (dynamic ones are listed below); i18n.js only documents them.
KEY_USE = re.compile(r"""(?:\$t|\bt|\btr)\(\s*["'`]([A-Za-z0-9_.]+)["'`]""")
PLACEHOLDER = re.compile(r"\{(\w+)\}")
# Keys built at runtime (e.g. t(f"settings.renderer.names.{id}")): their prefixes must exist.
DYNAMIC_PREFIXES = ("settings.renderer.names.", "settings.language.options.", "settings.environment.groups.",
                    "settings.environment.variables.", "contentTypes.", "alignments.",
                    "templates.origins.", "templates.fields.",
                    "settings.appearance.")


def flatten(value, prefix=""):
    """Dotted key -> text (plural objects {"one", "other"} count as one key)."""
    if isinstance(value, dict) and not set(value) <= {"one", "other"}:
        for key, child in value.items():
            yield from flatten(child, f"{prefix}{key}.")
    else:
        yield prefix[:-1], value


def placeholders(text) -> set:
    texts = text.values() if isinstance(text, dict) else [text]
    return {name for item in texts for name in PLACEHOLDER.findall(item)}


def main() -> int:
    locales = {path.stem: dict(flatten(json.loads(path.read_text(encoding="utf-8")))) for path in sorted((ROOT / "locales").glob("*.json"))}
    problems = []
    all_keys = set().union(*(set(keys) for keys in locales.values()))
    for language, keys in locales.items():
        for key in sorted(all_keys - set(keys)):
            problems.append(f"{language}: missing key {key}")
    reference = locales["en"]
    for language, keys in locales.items():
        for key, text in keys.items():
            if key in reference and placeholders(text) != placeholders(reference[key]):
                problems.append(f"{language}: placeholders of {key} differ from en")

    sources = [*ROOT.glob("src/**/*.py"), *ROOT.glob("web/src/**/*.svelte"), *ROOT.glob("web/src/**/*.js")]
    used = {}
    for source in sources:
        for key in ([] if source.name == "i18n.js" else KEY_USE.findall(source.read_text(encoding="utf-8"))):
            used.setdefault(key, source.relative_to(ROOT))
    for key, source in sorted(used.items()):
        if key not in reference and not any(other.startswith(f"{key}.") for other in reference):
            problems.append(f"{source}: unknown key {key}")
    for prefix in DYNAMIC_PREFIXES:
        if not any(key.startswith(prefix) for key in reference):
            problems.append(f"no keys with the dynamic prefix {prefix}")

    print("\n".join(problems) or f"OK: {len(reference)} keys in {', '.join(locales)}; {len(used)} keys used in the code.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
