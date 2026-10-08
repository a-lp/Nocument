# Localization

All the texts shown in the web app, including the backend's error and warning messages, are in one file per language in `locales/` (`en.json`, `it.json`), shared by frontend and backend. Each file maps keys to texts in the same nested structure, e.g. `{"builder": {"savePdf": "Save PDF"}}` is the key `builder.savePdf`. Texts may contain `{name}` placeholders and plurals are objects `{"one": "...", "other": "..."}` chosen by the `count` parameter.

- **Frontend** (`web/src/i18n.js`): components use `$t("key", { name: value })`, which updates the page when the language changes; plain JavaScript modules use `tr("key")`. The chosen language is the `language` store. All the calls to the backend go through `apiFetch` (`web/src/api.js`), which sends the language in `Accept-Language`.
- **Backend** (`src/i18n.py`): `t("key", name=value)` gives the text in the language of the current request (chosen from `Accept-Language`, English if not supported), so messages raised anywhere (e.g. a `ValueError` of `DocumentBuilder`) reach the user in their language. A text missing in a language falls back to English; a missing key shows the key itself.

To add a language, copy `locales/en.json` to `locales/<code>.json`, translate it (including `language.name`, the name of the language in itself), add the code to `settings.language.options` in every file and import the file in `TRANSLATIONS` in `web/src/i18n.js`; the backend loads all the files in `locales/` by itself. After changing translations or code, check that every language has the same keys and placeholders and that every key used in the code exists:

```bash
python scripts/check_locales.py
```

Old links to `/documenti/builder` and `/documenti/analyzer` (the paths before the translation) are redirected to `/documents/...`, and `/documents/analyzer` (the Compiler before it was renamed) to `/documents/compiler`.
