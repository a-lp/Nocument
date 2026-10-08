from io import BytesIO
import os
import re

from docx import Document
from flask import Blueprint, current_app, jsonify, request, send_file, url_for

from ..builder.docx_files import template_to_document
from ..content_blocks.content_block import utc_now
from ..i18n import t
from .repository import ITemplateRepository, RepositoryError, TemplateFilter
from .template import ORIGINS, DocumentTemplate, IMPORT

MAX_PAGE_SIZE = 100
TEMPLATE_ID = re.compile(r"^[0-9a-f]{32}$")
# Maximum length of the text fields of a template.
FIELD_LIMITS = {"name": 120, "description": 1000, "version": 40}
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def create_templates_blueprint(repository: ITemplateRepository) -> Blueprint:
    """REST routes of the DocumentTemplates on /api/templates, with the given repository."""
    blueprint = Blueprint("templates", __name__, url_prefix="/api/templates")

    @blueprint.errorhandler(ValueError)
    def invalid_request(error):
        """Invalid data: 400."""
        return jsonify(error=str(error)), 400

    @blueprint.errorhandler(RepositoryError)
    def database_unavailable(error):
        """Database not reachable: 503."""
        current_app.logger.exception("Template repository error")
        return jsonify(error=t("errors.templatesDatabaseUnavailable")), 503

    @blueprint.get("")
    def list_templates():
        """
        Templates from the most recent. Query: skip (default 0), limit (default 50, at most 100), search (text in the
        name or in the description) and origin ("builder" or "import", repeatable).
        Response: {"items": [<summary>, ...], "total": number of templates matching the filters}.
        """
        skip = _query_int("skip", 0, 0, None)
        limit = _query_int("limit", 50, 1, MAX_PAGE_SIZE)
        criteria = TemplateFilter(
            text=request.args.get("search", "").strip(),
            origins=[origin for origin in request.args.getlist("origin") if origin in ORIGINS],
        )
        items = [summary.to_dict() for summary in repository.list_summaries(criteria, skip, limit)]
        return jsonify(items=items, total=repository.count(criteria))

    @blueprint.post("")
    def create_template():
        """
        Saves a template. Multipart form: file (.docx or .dotx, converted to a document), name (required),
        description, version and origin ("builder" for a document saved from the Builder, otherwise "import").
        Response 201 with the summary.
        """
        content, filename = _uploaded_docx()
        if content is None:
            raise ValueError(t("errors.uploadDocxOrDotx"))
        fields = _text_fields()
        origin = request.form.get("origin", IMPORT)
        template = DocumentTemplate(
            content, fields["name"], fields["description"], fields["version"],
            origin if origin in ORIGINS else IMPORT, os.path.basename(filename) or None,
        )
        repository.save(template)
        current_app.logger.info("Template %s saved (%s, %d bytes)", template.id, template.origin, len(content))
        response = jsonify(template.summary().to_dict())
        response.headers["Location"] = url_for("templates.get_template", template_id=template.id)
        return response, 201

    @blueprint.get("/<template_id>")
    def get_template(template_id: str):
        """Summary of the template (without the Word file)."""
        template = _find(template_id)
        return jsonify(template.summary().to_dict()) if template else _not_found()

    @blueprint.put("/<template_id>")
    def update_template(template_id: str):
        """
        Changes a template. Multipart form: name (required), description and version, and optionally file (.docx or
        .dotx) replacing its Word file, e.g. after editing it in the Builder. Origin, source file and creation date
        do not change. Response: the updated summary; 404 if it does not exist.
        """
        template = _find(template_id)
        if template is None:
            return _not_found()
        content, _ = _uploaded_docx()
        fields = _text_fields()
        template.name, template.description, template.version = fields["name"], fields["description"], fields["version"]
        if content is not None:
            template.docx = content
        template.updated_at = utc_now()
        repository.save(template)
        current_app.logger.info("Template %s updated%s", template.id, " with a new file" if content is not None else "")
        return jsonify(template.summary().to_dict())

    @blueprint.get("/<template_id>/file")
    def download_template(template_id: str):
        """Word file of the template, named after it."""
        template = _find(template_id)
        if template is None:
            return _not_found()
        return send_file(
            BytesIO(template.docx), mimetype=DOCX_MIME_TYPE, as_attachment=True,
            download_name=docx_name(template.name),
        )

    @blueprint.delete("/<template_id>")
    def delete_template(template_id: str):
        """Deletes the template: 204, 404 if it does not exist."""
        if not TEMPLATE_ID.match(template_id) or not repository.delete(template_id):
            return _not_found()
        return "", 204

    def _find(template_id: str) -> DocumentTemplate | None:
        """Template with the given ID; None also if the ID is not hexadecimal."""
        return repository.get(template_id) if TEMPLATE_ID.match(template_id) else None

    return blueprint


def find_template(repository: ITemplateRepository, template_id: str) -> DocumentTemplate | None:
    """Template with the given ID (None if missing or the ID is not valid), for the routes outside the blueprint."""
    return repository.get(template_id) if TEMPLATE_ID.match(template_id) else None


def docx_name(name: str) -> str:
    """Name of a Word file from a free text (e.g. the name of a template), without characters unsafe in paths."""
    base_name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", name).strip(" .") or "document"
    return f"{base_name}.docx"


def _uploaded_docx() -> tuple[bytes | None, str]:
    """
    Word file of the form ("file") as a document (a .dotx is converted) and its name; (None, "") without a file.
    Raises ValueError if it is not a .docx/.dotx or cannot be opened.
    """
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return None, ""
    filename = uploaded_file.filename or ""
    if not filename.lower().endswith((".docx", ".dotx")):
        raise ValueError(t("errors.uploadDocxOrDotx"))
    content = uploaded_file.read()
    try:
        if filename.lower().endswith(".dotx"):
            content = template_to_document(content)
        Document(BytesIO(content))
    except Exception as error:
        current_app.logger.exception("Template file opening failed")
        raise ValueError(t("errors.cannotOpenDocument")) from error
    return content, filename


def _text_fields() -> dict:
    """
    name (required), description and version of the form, trimmed; raises ValueError if the name is missing or a
    field is too long.
    """
    fields = {}
    for name, limit in FIELD_LIMITS.items():
        value = (request.form.get(name) or "").strip()
        if len(value) > limit:
            raise ValueError(t("errors.templateFieldTooLong", field=t(f"templates.fields.{name}"), limit=limit))
        fields[name] = value
    if not fields["name"]:
        raise ValueError(t("errors.templateNameRequired"))
    return fields


def _query_int(name: str, default: int, minimum: int, maximum: int | None) -> int:
    """Integer query string parameter, clamped to the range; raises ValueError if it is not a number."""
    value = request.args.get(name)
    if value is None:
        return default
    try:
        number = int(value)
    except ValueError as error:
        raise ValueError(t("errors.queryNotInteger", name=name)) from error
    number = max(minimum, number)
    return min(maximum, number) if maximum is not None else number


def _not_found():
    """404 response."""
    return jsonify(error=t("errors.templateNotFound")), 404
