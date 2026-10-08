from io import BytesIO
import os

from docx import Document
from flask import Blueprint, current_app, jsonify, request, url_for

from ..analyzers.style_analyzer import StyleAnalyzer
from ..builder.content_interface import CONTENT_ID
from ..builder.contents import content_from_dict
from ..builder.docx_files import template_to_document
from ..i18n import t
from .builder import ContentBlockBuilder
from .importer import import_contents
from .repository import ContentBlockFilter, IContentBlockRepository, RepositoryError

MAX_PAGE_SIZE = 100


def create_content_blocks_blueprint(repository: IContentBlockRepository) -> Blueprint:
    """
    REST routes of the ContentBlocks on /api/content-blocks, with the given repository.
    Create and update body: {"title": "...", "contents": [<content>, ...]} with the contents in the format of
    content_from_dict (heading, paragraph, image, table), each with an optional hexadecimal "id".
    """
    blueprint = Blueprint("content_blocks", __name__, url_prefix="/api/content-blocks")

    @blueprint.errorhandler(ValueError)
    def invalid_request(error):
        """Invalid data: 400."""
        return jsonify(error=str(error)), 400

    @blueprint.errorhandler(RepositoryError)
    def database_unavailable(error):
        """Database not reachable: 503."""
        current_app.logger.exception("Content block repository error")
        return jsonify(error=t("errors.databaseUnavailable")), 503

    @blueprint.get("")
    def list_blocks():
        """
        Blocks from the most recent. Query: skip (default 0), limit (default 50, at most 100), title and description
        filters (contained text) and origin: source (import file, repeatable) and/or manual=true (created by hand),
        as alternatives; full=true for the complete blocks instead of the summaries.
        Response: {"items": [...], "total": number of blocks matching the filters}.
        """
        skip = _query_int("skip", 0, 0, None)
        limit = _query_int("limit", 50, 1, MAX_PAGE_SIZE)
        criteria = ContentBlockFilter(
            title=request.args.get("title", "").strip(),
            description=request.args.get("description", "").strip(),
            sources=[source for source in request.args.getlist("source") if source],
            manual=_query_bool("manual"),
        )
        if _query_bool("full"):
            items = [block.to_dict() for block in repository.search(criteria, skip, limit)]
        else:
            items = [summary.to_dict() for summary in repository.list_summaries(criteria, skip, limit)]
        return jsonify(items=items, total=repository.count(criteria))

    @blueprint.get("/sources")
    def list_sources():
        """Word files blocks were imported from: {"sources": [...]} in alphabetical order."""
        return jsonify(sources=repository.sources())

    @blueprint.post("")
    def create_block():
        """Creates a block; with "id" in the body it uses that one (409 if it already exists). Response 201 with the block."""
        payload = _payload()
        builder = ContentBlockBuilder(payload.get("id"))
        block = _fill(builder, payload).build()
        if repository.get(block.id) is not None:
            return jsonify(error=t("errors.blockExists")), 409
        repository.save(block)
        response = jsonify(block.to_dict())
        response.headers["Location"] = url_for("content_blocks.get_block", block_id=block.id)
        return response, 201

    @blueprint.get("/styles")
    def default_styles():
        """
        Styles to offer for the contents of a block (StyleAnalyzer.to_dict): those of the default Word template,
        because a block does not belong to a document.
        """
        return jsonify(_styles(Document()))

    @blueprint.post("/import")
    def import_document():
        """
        Extracts the contents of a Word document (.docx) or template (.dotx) grouped by top level heading
        (see import_contents), without saving them: the frontend lets the user choose and creates the blocks with
        POST /api/content-blocks.
        Response: {"title": file name, "groups": [{"title": heading or null, "contents": [...]}],
        "styles": document styles, "warnings": [...]}.
        """
        uploaded_file = request.files.get("file")
        filename = uploaded_file.filename if uploaded_file else ""
        if not filename.lower().endswith((".docx", ".dotx")):
            raise ValueError(t("errors.uploadDocxOrDotx"))
        content = uploaded_file.read()
        try:
            if filename.lower().endswith(".dotx"):
                content = template_to_document(content)
            document = Document(BytesIO(content))
        except Exception as error:
            raise ValueError(t("errors.cannotOpenDocument")) from error
        result = import_contents(document)
        return jsonify(
            title=os.path.splitext(os.path.basename(filename))[0],
            groups=[
                {"title": group.title, "contents": [content.serialize() for content in group.contents]}
                for group in result.groups
            ],
            styles=_styles(document),
            warnings=result.warnings,
        )

    @blueprint.get("/<block_id>")
    def get_block(block_id):
        """Complete block, with its contents."""
        block = _find(block_id)
        return (jsonify(block.to_dict()), 200) if block else _not_found()

    @blueprint.put("/<block_id>")
    def update_block(block_id):
        """Replaces title (if in the body) and contents; ID and creation date stay."""
        block = _find(block_id)
        if block is None:
            return _not_found()
        block = _fill(ContentBlockBuilder.from_block(block).clear(), _payload()).build()
        repository.save(block)
        return jsonify(block.to_dict())

    @blueprint.delete("/<block_id>")
    def delete_block(block_id):
        """Deletes the block: 204, or 404 if it does not exist."""
        if not CONTENT_ID.match(block_id) or not repository.delete(block_id):
            return _not_found()
        return "", 204

    def _find(block_id: str):
        """Block with the given ID; None also if the ID is not hexadecimal."""
        return repository.get(block_id) if CONTENT_ID.match(block_id) else None

    return blueprint


def _styles(document) -> dict:
    """Styles of the document in the format of StyleAnalyzer.to_dict."""
    analyzer = StyleAnalyzer()
    analyzer.analyze(document)
    return analyzer.to_dict()


def _payload() -> dict:
    """JSON body of the request; raises ValueError if it is not an object."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError(t("errors.invalidJson"))
    return payload


def _fill(builder: ContentBlockBuilder, payload: dict) -> ContentBlockBuilder:
    """Applies title and contents of the body to the builder."""
    if "title" in payload:
        builder.with_title(payload["title"] or "")
    if "description" in payload:
        builder.with_description(payload["description"] or "")
    if "source" in payload:
        builder.with_source(payload["source"])
    contents = payload.get("contents", [])
    if not isinstance(contents, list):
        raise ValueError(t("errors.contentsNotList"))
    for content in contents:
        builder.add(content_from_dict(content))
    return builder


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


def _query_bool(name: str) -> bool:
    """Boolean query string parameter ("true", "1", "yes")."""
    return request.args.get(name, "").lower() in ("true", "1", "yes")


def _not_found():
    """404 response."""
    return jsonify(error=t("errors.blockNotFound")), 404
