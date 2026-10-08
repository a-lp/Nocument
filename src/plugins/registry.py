"""
Registry of the installed plugins: it discovers them in the plugins folder, knows their compatibilities and runs them.

A plugin package is a folder of the plugins folder with:
- plugin.py: the Python script, loaded as a module; each IPlugin subclass defined in it is created once;
- ui.svelte: the custom interface of the package, compiled and shown by the web app on the page of its plugins;
- README.md: the explanation of the package, shown on the same page.
Packages installed from the web app always have the three files (see install). Loose .py files of the plugins folder
(the format before packages) are still loaded, without interface and README. Names starting with "_" or "." are
ignored (free for shared helpers and temporary files). The folder is read again when scripts are added, changed or
removed (also by hand, or by another worker process of the server): refresh compares their modification times.
"""
from dataclasses import dataclass
import importlib.util
import inspect
import io
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import threading
import time
import uuid
import zipfile

from ..builder.contents import content_from_dict
from ..i18n import t
from ..logging_setup import capture_output, get_logger
from .plugin_interface import CONTENT_CLASSES, CONTENT_TYPES, PLUGIN_ID, IPlugin, PluginError, PluginInfo

logger = get_logger("plugins.registry")

MODULE_PREFIX = "nocument_plugins."
MAX_PLUGIN_SIZE = 1024 * 1024
# Files of a plugin package (see the module docstring), all required when installing from the web app.
SCRIPT_FILE = "plugin.py"
UI_FILE = "ui.svelte"
README_FILE = "README.md"
PACKAGE_FILES = (SCRIPT_FILE, UI_FILE, README_FILE)


@dataclass
class _LoadedFile:
    """
    Plugins of a package (or of a loose script), with the state of its script when it was loaded. folder: the folder
    of the package, None for a loose script.
    """
    signature: tuple[int, int]
    plugins: list[IPlugin]
    error: str | None = None
    folder: Path | None = None


class PluginRegistry:
    """Plugins of a folder, by id."""

    def __init__(self, directory: str | os.PathLike):
        """Registry of the plugins in directory (created if missing); they are loaded at the first refresh."""
        self.directory = Path(directory)
        self._files: dict[str, _LoadedFile] = {}
        self._lock = threading.RLock()

    # ---- Discovery ----

    def refresh(self) -> None:
        """Loads new and changed packages (and loose scripts) and forgets removed ones."""
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            # Key: name of the package folder, or of the loose script.
            current = {
                path.name: (path / SCRIPT_FILE, path) for path in self.directory.iterdir()
                if path.is_dir() and _is_plugin_file(path.name) and (path / SCRIPT_FILE).is_file()
            }
            current.update({
                path.name: (path, None) for path in self.directory.glob("*.py") if _is_plugin_file(path.name)
            })
            for name in set(self._files) - set(current):
                self._forget(name)
            for name, (script, folder) in sorted(current.items()):
                signature = _signature(script)
                loaded = self._files.get(name)
                if loaded is None or loaded.signature != signature:
                    self._forget(name)
                    self._files[name] = self._load(script, signature, filename=name)
                    self._files[name].folder = folder

    def plugins(self, content_type: str | None = None) -> list[PluginInfo]:
        """Loaded plugins, by name; with content_type only those compatible with it."""
        self.refresh()
        with self._lock:
            infos = [
                PluginInfo(plugin.id, plugin.name, plugin.description, str(plugin.version), name,
                           plugin.compatibilities(), loaded.folder is not None and (loaded.folder / UI_FILE).is_file(),
                           loaded.folder is not None and (loaded.folder / README_FILE).is_file(), loaded.folder is None)
                for name, loaded in self._files.items() for plugin in loaded.plugins
            ]
        infos = [info for info in infos if content_type is None or content_type in info.compatibilities]
        return sorted(infos, key=lambda info: info.name.lower())

    def errors(self) -> list[dict]:
        """Files that could not be loaded: [{"file", "error"}]."""
        self.refresh()
        with self._lock:
            return [{"file": name, "error": loaded.error} for name, loaded in sorted(self._files.items()) if loaded.error]

    def get(self, plugin_id: str) -> IPlugin | None:
        """Plugin with the given id, or None."""
        self.refresh()
        with self._lock:
            return next(
                (plugin for loaded in self._files.values() for plugin in loaded.plugins if plugin.id == plugin_id), None
            )

    def info(self, plugin_id: str) -> PluginInfo | None:
        """Description of the plugin with the given id, or None."""
        return next((info for info in self.plugins() if info.id == plugin_id), None)

    def package_file(self, plugin_id: str, name: str) -> str | None:
        """Text of a file of the package of the plugin (UI_FILE, README_FILE), None if missing (or a loose script)."""
        self.refresh()
        with self._lock:
            folder = next(
                (loaded.folder for loaded in self._files.values() if any(plugin.id == plugin_id for plugin in loaded.plugins)),
                None,
            )
        path = folder / name if folder is not None else None
        return path.read_text(encoding="utf-8") if path is not None and path.is_file() else None

    # ---- Use ----

    def parameters(self, plugin: IPlugin, content_type: str) -> list:
        """Parameters of plugin for content_type; raises ValueError if the plugin does not support it."""
        _check_compatible(plugin, content_type)
        with capture_output(plugin.logger):
            return list(plugin.parameters(content_type))

    def compile(self, plugin: IPlugin, content_type: str, values) -> dict:
        """
        Content of content_type created by plugin with the given parameter values, in the JSON of the contents
        (content_from_dict). Raises ValueError for invalid values, PluginError (or any exception) if the plugin fails.
        """
        _check_compatible(plugin, content_type)
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ValueError(t("errors.parameterValuesNotObject"))
        with capture_output(plugin.logger):
            parameters = plugin.parameters(content_type)
            parsed = {parameter.name: parameter.parse(values.get(parameter.name)) for parameter in parameters}
            # Secrets (e.g. tokens) never end up in the log.
            logged = {
                parameter.name: "***" if parameter.type == "password" and parsed[parameter.name] else parsed[parameter.name]
                for parameter in parameters
            }
            logger.info("Running %s (%s) for a %s with %s", plugin.id, type(plugin).__name__, content_type, logged)
            started = time.perf_counter()
            content = getattr(plugin, f"compile_{content_type}")(parsed)
        logger.info("%s created a %s in %.2f s", plugin.id, content_type, time.perf_counter() - started)
        if not isinstance(content, CONTENT_CLASSES[content_type]):
            raise PluginError(t("errors.pluginWrongContent", name=plugin.name, type=content_type))
        # The round trip through the JSON validates the content as if it came from the web app.
        try:
            return content_from_dict(content.serialize()).serialize()
        except ValueError as error:
            raise PluginError(t("errors.pluginInvalidContent", name=plugin.name, error=error)) from error

    # ---- Installation ----

    def install(self, files: dict[str, bytes], replace: bool = False) -> tuple[str, list[PluginInfo]]:
        """
        Installs a plugin package: files maps the names PACKAGE_FILES (all required) to their content (see
        read_package for a .zip). The script is checked (syntax, loading, at least one plugin, ids not used by other
        packages) in a hidden folder before replacing anything; the package folder is named after the id of its
        first plugin. Returns the name of the folder and its plugins.
        Raises FileExistsError (with the folder name) if the package exists and not replace, ValueError if the
        package is not valid.
        """
        missing = [name for name in PACKAGE_FILES if name not in files]
        if missing:
            raise ValueError(t("errors.pluginPackageFiles", files=", ".join(PACKAGE_FILES), missing=", ".join(missing)))
        unknown = sorted(set(files) - set(PACKAGE_FILES))
        if unknown:
            raise ValueError(t("errors.pluginPackageUnknown", files=", ".join(unknown)))
        for name, content in files.items():
            if len(content) > MAX_PLUGIN_SIZE:
                raise ValueError(t("errors.pluginFileTooLarge", file=name, size=MAX_PLUGIN_SIZE // 1024))
        for name in (UI_FILE, README_FILE):
            try:
                files[name].decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValueError(t("errors.pluginFileEncoding", file=name)) from error
        try:
            compile(files[SCRIPT_FILE], SCRIPT_FILE, "exec")
        except SyntaxError as error:
            raise ValueError(t("errors.pluginSyntax", line=error.lineno, error=error.msg)) from error
        except ValueError as error:
            raise ValueError(t("errors.pluginSyntax", line=0, error=error)) from error

        with self._lock:
            self.refresh()
            # Hidden staging folder (ignored by refresh) in the same folder, so the final rename is atomic.
            staging = self.directory / f".upload-{uuid.uuid4().hex}"
            staging.mkdir()
            try:
                for name, content in files.items():
                    (staging / name).write_bytes(content)
                script = staging / SCRIPT_FILE
                check_module = f"{MODULE_PREFIX}_check_{uuid.uuid4().hex}"
                # Checked as a new package: its own ids, if already installed, are checked against the others below.
                loaded = self._load(script, _signature(script), check_module, staging.name, check_owners=False)
                sys.modules.pop(check_module, None)
                if loaded.error:
                    raise ValueError(loaded.error)
                if not loaded.plugins:
                    raise ValueError(t("errors.pluginNoClass"))
                package = loaded.plugins[0].id
                duplicate = next((plugin.id for plugin in loaded.plugins if self._id_owner(plugin.id, package)), None)
                if duplicate:
                    raise ValueError(t("errors.pluginDuplicateId", id=duplicate))
                target = self.directory / package
                if target.exists() and not replace:
                    raise FileExistsError(package)
                if target.exists():
                    self._forget(package)
                    shutil.rmtree(target)
                os.replace(staging, target)
            finally:
                shutil.rmtree(staging, ignore_errors=True)
            self.refresh()
            loaded = self._files.get(package)
            if loaded is None or loaded.error:
                raise ValueError(loaded.error if loaded else t("errors.pluginNoClass"))
            return package, [info for info in self.plugins() if info.file == package]

    def remove(self, name: str) -> bool:
        """Deletes a plugin package (its folder) or a loose script; returns False if it does not exist."""
        if not _is_plugin_file(name) or Path(name).name != name:
            return False
        with self._lock:
            path = self.directory / name
            if path.is_dir() and (path / SCRIPT_FILE).is_file():
                self._forget(name)
                shutil.rmtree(path)
            elif path.is_file() and name.endswith(".py"):
                path.unlink()
            else:
                return False
            self.refresh()
            return True

    # ---- Loading ----

    def _load(self, path: Path, signature: tuple[int, int], module_name: str | None = None,
              filename: str | None = None, check_owners: bool = True) -> _LoadedFile:
        """
        Imports the script and creates its plugins; errors are kept in the result, not raised. filename is the key of
        the package (folder or loose script name): its own plugin ids are not duplicates. check_owners=False skips
        the check against the other packages (done by install, which knows the package being replaced).
        """
        filename = filename or path.name
        module_name = module_name or MODULE_PREFIX + Path(filename).stem
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            # Registered before running it: dataclasses and the like look the module up in sys.modules.
            sys.modules[module_name] = module
            # What the script prints while loading goes to the log of its file.
            with capture_output(get_logger(f"plugins.{Path(filename).stem}")):
                spec.loader.exec_module(module)
            classes = [
                cls for _, cls in inspect.getmembers(module, inspect.isclass)
                if issubclass(cls, IPlugin) and cls is not IPlugin and cls.__module__ == module_name
                and not inspect.isabstract(cls)
            ]
            plugins = []
            for cls in classes:
                with capture_output(get_logger(f"plugins.{getattr(cls, 'id', '') or cls.__name__}")):
                    plugins.append(cls())
            for plugin in plugins:
                _validate_plugin(plugin)
            ids = [plugin.id for plugin in plugins]
            duplicate = next(
                (plugin_id for plugin_id in ids
                 if ids.count(plugin_id) > 1 or (check_owners and self._id_owner(plugin_id, filename))),
                None,
            )
            if duplicate:
                raise ValueError(t("errors.pluginDuplicateId", id=duplicate))
            logger.info("Loaded %s: %s", filename, ", ".join(f"{plugin.id} {plugin.compatibilities()}" for plugin in plugins) or "no plugins")
            return _LoadedFile(signature, plugins)
        except Exception as error:
            sys.modules.pop(module_name, None)
            logger.warning("Cannot load the plugin file %s", filename, exc_info=True)
            # Checks of the definition (ValueError) are already readable; other errors come from running the script.
            if isinstance(error, (ValueError, PluginError)):
                return _LoadedFile(signature, [], str(error))
            return _LoadedFile(signature, [], t("errors.pluginLoad", error=f"{type(error).__name__}: {error}"))

    def _id_owner(self, plugin_id: str, filename: str) -> str | None:
        """Other file already defining a plugin with plugin_id, or None (the first file loaded keeps the id)."""
        return next(
            (name for name, loaded in self._files.items()
             if name != filename and any(plugin.id == plugin_id for plugin in loaded.plugins)),
            None,
        )

    def _forget(self, name: str) -> None:
        """Removes a file from the registry and its module from sys.modules."""
        loaded = self._files.pop(name, None)
        if loaded is not None:
            logger.info("Unloaded %s", name)
            sys.modules.pop(MODULE_PREFIX + Path(name).stem, None)


def read_package(uploads: dict[str, bytes]) -> dict[str, bytes]:
    """
    Files of a plugin package from the upload: a single .zip (its files at the root, or in one folder) or the files
    themselves. Returns {name: content} for the install; raises ValueError for a damaged zip.
    """
    zips = [name for name in uploads if name.lower().endswith(".zip")]
    if not zips:
        return dict(uploads)
    if len(uploads) > 1:
        raise ValueError(t("errors.pluginZipAlone"))
    try:
        archive = zipfile.ZipFile(io.BytesIO(uploads[zips[0]]))
        entries = [entry for entry in archive.infolist() if not entry.is_dir()
                   and not PurePosixPath(entry.filename).name.startswith(".")
                   and "__MACOSX" not in PurePosixPath(entry.filename).parts]
        if sum(entry.file_size for entry in entries) > len(PACKAGE_FILES) * MAX_PLUGIN_SIZE:
            raise ValueError(t("errors.pluginFileTooLarge", file=zips[0], size=len(PACKAGE_FILES) * MAX_PLUGIN_SIZE // 1024))
        # The files may be inside a single folder of the archive (e.g. created by compressing the folder).
        parents = {PurePosixPath(entry.filename).parent for entry in entries}
        if len(parents) > 1:
            raise ValueError(t("errors.pluginZipLayout", files=", ".join(PACKAGE_FILES)))
        return {PurePosixPath(entry.filename).name: archive.read(entry) for entry in entries}
    except zipfile.BadZipFile as error:
        raise ValueError(t("errors.pluginZipInvalid")) from error


def _is_plugin_file(name: str) -> bool:
    """True for the files the registry loads (not hidden, not private helpers)."""
    return not name.startswith(("_", "."))


def _signature(path: Path) -> tuple[int, int]:
    """Modification time and size of the file: they change when the file is replaced or edited."""
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def _validate_plugin(plugin: IPlugin) -> None:
    """Checks id, name and compatibilities of a plugin; raises ValueError for the developer."""
    if not isinstance(plugin.id, str) or not PLUGIN_ID.match(plugin.id):
        raise ValueError(t("errors.pluginInvalidId", plugin=type(plugin).__name__))
    if not isinstance(plugin.name, str) or not plugin.name.strip():
        raise ValueError(t("errors.pluginMissingName", plugin=type(plugin).__name__))
    if not plugin.compatibilities():
        raise ValueError(t("errors.pluginNoCompatibility", plugin=type(plugin).__name__))


def _check_compatible(plugin: IPlugin, content_type: str) -> None:
    """Raises ValueError if content_type is unknown or the plugin cannot create it."""
    if content_type not in CONTENT_TYPES:
        raise ValueError(t("errors.unsupportedContentType", type=content_type))
    if content_type not in plugin.compatibilities():
        raise ValueError(t("errors.pluginNotCompatible", name=plugin.name, type=content_type))
