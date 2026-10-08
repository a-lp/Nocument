import base64
import re

from bson.binary import Binary
from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DocumentTooLarge, PyMongoError

from ..i18n import t
from .content_block import ContentBlock, ContentBlockSummary
from .repository import ContentBlockFilter, IContentBlockRepository, RepositoryError

DEFAULT_COLLECTION = "content_blocks"


class MongoContentBlockRepository(IContentBlockRepository):
    """
    ContentBlocks saved in MongoDB, one document per block: the block ID is _id, the contents stay in order in the
    contents array. Image bytes are saved as BSON binary (not base64).
    A MongoDB document cannot exceed 16 MB: a block with larger images is rejected.
    """

    def __init__(self, collection: Collection):
        """collection: collection of the blocks. It does not connect to the database: the first operation does."""
        self.collection = collection
        # The indexes are created at the first save, not at startup:
        # the database may not be reachable yet when the backend starts.
        self._indexes_created = False

    @classmethod
    def from_uri(cls, uri: str, database: str, collection: str = DEFAULT_COLLECTION,
                 timeout_ms: int = 5000) -> "MongoContentBlockRepository":
        """Repository sul database indicato dall'URI (es. mongodb://mongo:27017)."""
        client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
        return cls(client[database][collection])

    def get(self, block_id: str) -> ContentBlock | None:
        """Block with the given ID, or None."""
        document = self._run(lambda: self.collection.find_one({"_id": block_id}))
        return self._to_block(document) if document is not None else None

    def search(self, criteria: ContentBlockFilter | None = None, skip: int = 0, limit: int = 50) -> list[ContentBlock]:
        """Complete blocks matching the criteria, from the most recent."""
        documents = self._run(lambda: list(
            self.collection.find(self._query(criteria)).sort("updated_at", DESCENDING).skip(skip).limit(limit)
        ))
        return [self._to_block(document) for document in documents]

    def list_summaries(self, criteria: ContentBlockFilter | None = None, skip: int = 0,
                       limit: int = 50) -> list[ContentBlockSummary]:
        """Summaries from the most recent; only the type of the contents is read, without the image data."""
        pipeline = [
            {"$match": self._query(criteria)},
            {"$sort": {"updated_at": DESCENDING}},
            {"$skip": skip},
            {"$limit": limit},
            {"$project": {
                "title": 1, "description": 1, "source": 1, "created_at": 1, "updated_at": 1,
                "content_types": "$contents.type",
            }},
        ]
        documents = self._run(lambda: list(self.collection.aggregate(pipeline)))
        return [
            ContentBlockSummary(
                document["_id"], document.get("title", ""), document.get("description", ""), document.get("source"),
                document.get("content_types", []), document["created_at"], document["updated_at"],
            )
            for document in documents
        ]

    def count(self, criteria: ContentBlockFilter | None = None) -> int:
        """Number of blocks matching the criteria."""
        return self._run(lambda: self.collection.count_documents(self._query(criteria)))

    def sources(self) -> list[str]:
        """File di origine distinti, in ordine alfabetico."""
        return sorted(source for source in self._run(lambda: self.collection.distinct("source")) if source)

    def save(self, block: ContentBlock) -> None:
        """Creates or replaces the document of the block."""
        if not self._indexes_created:
            self._run(lambda: self.collection.create_index([("updated_at", DESCENDING)]))
            self._run(lambda: self.collection.create_index("source"))
            self._indexes_created = True
        document = self._to_document(block)
        try:
            self._run(lambda: self.collection.replace_one({"_id": block.id}, document, upsert=True))
        except RepositoryError as error:
            if isinstance(error.__cause__, DocumentTooLarge):
                raise ValueError(t("errors.blockTooLarge")) from error
            raise

    def delete(self, block_id: str) -> bool:
        """Deletes the document of the block."""
        return self._run(lambda: self.collection.delete_one({"_id": block_id})).deleted_count == 1

    @staticmethod
    def _query(criteria: ContentBlockFilter | None) -> dict:
        """MongoDB filter of the criteria: text as a literal regular expression, case insensitive."""
        criteria = criteria or ContentBlockFilter()
        query = {}
        if criteria.title:
            query["title"] = {"$regex": re.escape(criteria.title), "$options": "i"}
        if criteria.description:
            query["description"] = {"$regex": re.escape(criteria.description), "$options": "i"}
        if criteria.filters_origin:
            # Created by hand: source missing, null or empty ($in with None also matches a missing field).
            query["source"] = {"$in": [*criteria.sources, *([None, ""] if criteria.manual else [])]}
        return query

    @staticmethod
    def _to_document(block: ContentBlock) -> dict:
        """MongoDB document of the block: id becomes _id and the image data goes from base64 to binary."""
        document = block.to_dict()
        document["_id"] = document.pop("id")
        for content in document["contents"]:
            if content["type"] == "image":
                content["data"] = Binary(base64.b64decode(content["data"]))
        return document

    @staticmethod
    def _to_block(document: dict) -> ContentBlock:
        """Block rebuilt from the MongoDB document (inverse of _to_document)."""
        document = dict(document)
        document["id"] = document.pop("_id")
        for content in document.get("contents", []):
            if content.get("type") == "image" and isinstance(content.get("data"), bytes):
                content["data"] = base64.b64encode(content["data"]).decode("ascii")
        return ContentBlock.from_dict(document)

    @staticmethod
    def _run(operation):
        """Runs an operation on the database converting pymongo errors into RepositoryError."""
        try:
            return operation()
        except PyMongoError as error:
            raise RepositoryError(f"Database error: {error}") from error
