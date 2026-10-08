from flask import Blueprint, Response, jsonify, request
from werkzeug.utils import secure_filename

from ..i18n import t
from .plugin_interface import CONTENT_TYPES, PluginError
from .registry import README_FILE, UI_FILE, PluginRegistry, read_package


def create_plugins_blueprint(registry: PluginRegistry, upload_enabled: bool = True) -> Blueprint:
    """
    REST routes of the plugins on /api/plugins: list, parameters and contents of a plugin, installation and removal.
    upload_enabled: False to forbid installing and removing plugins from the web app (only by hand in the folder).
    """
    blueprint = Blueprint("plugins", __name__, url_prefix="/api/plugins")

    @blueprint.errorhandler(ValueError)
    def invalid_request(error):
        """Invalid data: 400."""
        return jsonify(error=str(error)), 400

    @blueprint.get("")
    def list_plugins():
        """
        Installed plugins, by name; query type=heading|paragraph|image|table for only the compatible ones.
        Response: {"plugins": [{"id", "name", "description", "version", "file" (package folder), "compatibilities",
        "has_ui", "has_readme", "legacy"}], "errors": [{"file", "error"}] (packages that could not be loaded),
        "upload_enabled": bool}.
        """
        content_type = request.args.get("type") or None
        if content_type is not None and content_type not in CONTENT_TYPES:
            raise ValueError(t("errors.unsupportedContentType", type=content_type))
        return jsonify(
            plugins=[info.to_dict() for info in registry.plugins(content_type)],
            errors=registry.errors(),
            upload_enabled=upload_enabled,
        )

    @blueprint.get("/<plugin_id>")
    def get_plugin(plugin_id):
        """A plugin with its parameters for each compatible type: {..., "parameters": {"table": [...], ...}}."""
        plugin, info = _plugin(plugin_id)
        parameters = {}
        for content_type in info.compatibilities:
            parameters[content_type] = [parameter.to_dict() for parameter in _run(plugin, registry.parameters, plugin, content_type)]
        return jsonify(**info.to_dict(), parameters=parameters)

    @blueprint.get("/<plugin_id>/ui")
    def get_ui(plugin_id):
        """Svelte source of the custom interface of the plugin's package (ui.svelte), compiled by the web app."""
        return _package_file(plugin_id, UI_FILE, "text/plain; charset=utf-8")

    @blueprint.get("/<plugin_id>/readme")
    def get_readme(plugin_id):
        """README of the plugin's package (Markdown)."""
        return _package_file(plugin_id, README_FILE, "text/markdown; charset=utf-8")

    def _package_file(plugin_id, name, mimetype):
        """A file of the package as text; 404 if the plugin is not installed or its package does not have it."""
        _plugin(plugin_id)
        text = registry.package_file(plugin_id, name)
        if text is None:
            return jsonify(error=t("errors.pluginPackageFileMissing", id=plugin_id, file=name)), 404
        # Not cached: a reinstalled package must be shown at once.
        return Response(text, content_type=mimetype, headers={"Cache-Control": "no-store"})

    @blueprint.get("/<plugin_id>/parameters")
    def get_parameters(plugin_id):
        """Parameters of the plugin for the content type in the query (type): {"parameters": [...]}."""
        plugin, _ = _plugin(plugin_id)
        parameters = _run(plugin, registry.parameters, plugin, request.args.get("type", ""))
        return jsonify(parameters=[parameter.to_dict() for parameter in parameters])

    @blueprint.post("/<plugin_id>/compile")
    def compile_content(plugin_id):
        """
        Creates a content with the plugin. Body JSON: {"type": "table", "values": {"<parameter>": value, ...}}.
        Response: {"content": <content in the JSON of content_from_dict>}, ready for the Builder and the blocks.
        """
        plugin, _ = _plugin(plugin_id)
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ValueError(t("errors.invalidJson"))
        content = _run(plugin, registry.compile, plugin, payload.get("type", ""), payload.get("values"))
        return jsonify(content=content)

    @blueprint.post("")
    def install_plugin():
        """
        Installs a plugin package in a folder of its own (multipart, field "files", repeatable): a .zip with
        plugin.py, ui.svelte and README.md, or the three files; "replace": "true" to overwrite the package with the
        same name. Response 201: {"package": folder, "plugins": [...]}; 409 if the package exists.
        """
        if not upload_enabled:
            return jsonify(error=t("errors.pluginUploadDisabled")), 403
        uploads = {}
        for uploaded in request.files.getlist("files") or request.files.getlist("file"):
            name = secure_filename(uploaded.filename or "")
            if name:
                uploads[name] = uploaded.read()
        if not uploads:
            raise ValueError(t("errors.pluginFileType"))
        try:
            package, infos = registry.install(read_package(uploads), request.form.get("replace") == "true")
        except FileExistsError as error:
            return jsonify(error=t("errors.pluginExists", file=str(error)), file=str(error)), 409
        return jsonify(package=package, plugins=[info.to_dict() for info in infos]), 201

    @blueprint.delete("/files/<filename>")
    def remove_plugin(filename):
        """Deletes a plugin package (its folder, with all its plugins) or a loose script. 204, or 404 if missing."""
        if not upload_enabled:
            return jsonify(error=t("errors.pluginUploadDisabled")), 403
        if not registry.remove(filename):
            return jsonify(error=t("errors.pluginFileNotFound", file=filename)), 404
        return "", 204

    def _plugin(plugin_id):
        """Plugin and its description; aborts with 404 if it is not installed."""
        plugin = registry.get(plugin_id)
        info = registry.info(plugin_id) if plugin else None
        if plugin is None or info is None:
            raise _NotFound(t("errors.pluginNotFound", id=plugin_id))
        return plugin, info

    def _run(plugin, function, *args):
        """
        Calls the plugin through function: ValueError (invalid request) passes through, PluginError becomes 502 with
        its message, any other error 502 with a generic message (the details go in the log).
        """
        try:
            return function(*args)
        except ValueError:
            raise
        except PluginError as error:
            plugin.logger.warning("Failed: %s", error)
            raise _PluginFailure(t("errors.pluginFailed", name=plugin.name, error=error)) from error
        except Exception as error:
            plugin.logger.exception("Unexpected error")
            raise _PluginFailure(t("errors.pluginCrashed", name=plugin.name)) from error

    @blueprint.errorhandler(_NotFound)
    def not_found(error):
        """Plugin not installed: 404."""
        return jsonify(error=str(error)), 404

    @blueprint.errorhandler(_PluginFailure)
    def plugin_failure(error):
        """Error of the plugin (e.g. external data not reachable): 502."""
        return jsonify(error=str(error)), 502

    return blueprint


class _NotFound(Exception):
    """Plugin not installed."""


class _PluginFailure(Exception):
    """The plugin raised an error while answering."""
