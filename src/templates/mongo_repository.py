import re

from bson.binary import Binary
from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DocumentTooLarge, PyMongoError

from ..i18n import t
from .repository import ITemplateRepository, RepositoryError, TemplateFilter
from .template import DocumentTemplate, DocumentTemplateSummary

DEFAULT_COLLECTION = "document_templates"
SUMMARY_FIELDS = {"docx": 0}


class MongoTemplateRepository(ITemplateRepository):
    """
    DocumentTemplates saved in MongoDB, one document per template: the ID is _id and the Word file is BSON binary,
    left out of the summaries. A MongoDB document cannot exceed 16 MB: a larger Word file is rejected.
    """

    def __init__(self, collection: Collection):
        """collection: collection of the templates. It does not connect to the database: the first operation does."""
        self.collection = collection
        # Created at the first save: the database may not be reachable yet when the backend starts.
        self._indexes_created = False

    @classmethod
    def from_uri(cls, uri: str, database: str, collection: str = DEFAULT_COLLECTION,
                 timeout_ms: int = 5000) -> "MongoTemplateRepository":
        """Repository on the database of the URI (e.g. mongodb://mongo:27017)."""
        client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
        return cls(client[database][collection])

    def get(self, template_id: str) -> DocumentTemplate | None:
        document = self._run(lambda: self.collection.find_one({"_id": template_id}))
        if document is None:
            return None
        return DocumentTemplate(
            bytes(document["docx"]), document.get("name", ""), document.get("description", ""),
            document.get("version", ""), document.get("origin", ""), document.get("source"), document["_id"],
            document["created_at"], document["updated_at"],
        )

    def list_summaries(self, criteria: TemplateFilter | None = None, skip: int = 0,
                       limit: int = 50) -> list[DocumentTemplateSummary]:
        documents = self._run(lambda: list(
            self.collection.find(self._query(criteria), SUMMARY_FIELDS)
            .sort("updated_at", DESCENDING).skip(skip).limit(limit)
        ))
        return [
            DocumentTemplateSummary(
                document["_id"], document.get("name", ""), document.get("description", ""),
                document.get("version", ""), document.get("origin", ""), document.get("source"),
                document["created_at"], document["updated_at"],
            )
            for document in documents
        ]

    def count(self, criteria: TemplateFilter | None = None) -> int:
        return self._run(lambda: self.collection.count_documents(self._query(criteria)))

    def save(self, template: DocumentTemplate) -> None:
        if not self._indexes_created:
            self._run(lambda: self.collection.create_index([("updated_at", DESCENDING)]))
            self._indexes_created = True
        document = {
            "_id": template.id,
            "name": template.name,
            "description": template.description,
            "version": template.version,
            "origin": template.origin,
            "source": template.source,
            "docx": Binary(template.docx),
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }
        try:
            self._run(lambda: self.collection.replace_one({"_id": template.id}, document, upsert=True))
        except RepositoryError as error:
            if isinstance(error.__cause__, DocumentTooLarge):
                raise ValueError(t("errors.templateTooLarge")) from error
            raise

    def delete(self, template_id: str) -> bool:
        return self._run(lambda: self.collection.delete_one({"_id": template_id})).deleted_count == 1

    @staticmethod
    def _query(criteria: TemplateFilter | None) -> dict:
        """MongoDB filter of the criteria: text as a literal regular expression, case insensitive."""
        criteria = criteria or TemplateFilter()
        query = {}
        if criteria.text:
            pattern = {"$regex": re.escape(criteria.text), "$options": "i"}
            query["$or"] = [{"name": pattern}, {"description": pattern}]
        if criteria.origins:
            query["origin"] = {"$in": criteria.origins}
        return query

    @staticmethod
    def _run(operation):
        """Runs an operation on the database converting pymongo errors into RepositoryError."""
        try:
            return operation()
        except PyMongoError as error:
            raise RepositoryError(f"Database error: {error}") from error
