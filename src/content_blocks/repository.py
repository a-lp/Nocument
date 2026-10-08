from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field

from .content_block import ContentBlock, ContentBlockSummary


class RepositoryError(Exception):
    """The database is not reachable or refused the operation."""


@dataclass
class ContentBlockFilter:
    """
    Search criteria of the blocks, all optional and combined together:
    title and description look for the text in the title and in the description (case insensitive);
    sources and manual choose the origin: the blocks imported from one of the given files or, with manual, those
    created by hand (without source file). Without sources nor manual the origin is not filtered.
    """
    title: str = ""
    description: str = ""
    sources: list[str] = field(default_factory=list)
    manual: bool = False

    @property
    def filters_origin(self) -> bool:
        """True if the filter restricts the origin of the blocks."""
        return bool(self.sources) or self.manual

    def matches(self, block: dict) -> bool:
        """True if the block (JSON of ContentBlock.to_dict) matches the criteria."""
        source = block.get("source")
        return (
            self.title.lower() in (block.get("title") or "").lower()
            and self.description.lower() in (block.get("description") or "").lower()
            and (not self.filters_origin or source in self.sources or (self.manual and not source))
        )


class IContentBlockRepository(ABC):
    """Access to the saved ContentBlocks, independent of the database (repository pattern)."""

    @abstractmethod
    def get(self, block_id: str) -> ContentBlock | None:
        """Block with the given ID, or None if it does not exist."""

    @abstractmethod
    def search(self, criteria: ContentBlockFilter | None = None, skip: int = 0, limit: int = 50) -> list[ContentBlock]:
        """Complete blocks matching the criteria, from the most recent (updated_at) to the least recent."""

    @abstractmethod
    def list_summaries(self, criteria: ContentBlockFilter | None = None, skip: int = 0,
                       limit: int = 50) -> list[ContentBlockSummary]:
        """Summaries of the blocks matching the criteria, in the same order as search."""

    @abstractmethod
    def count(self, criteria: ContentBlockFilter | None = None) -> int:
        """Number of blocks matching the criteria."""

    @abstractmethod
    def sources(self) -> list[str]:
        """Names of the Word files blocks were imported from, in alphabetical order."""

    @abstractmethod
    def save(self, block: ContentBlock) -> None:
        """Saves the block, creating it or replacing the one with the same ID."""

    @abstractmethod
    def delete(self, block_id: str) -> bool:
        """Deletes the block; returns False if it did not exist."""


class InMemoryContentBlockRepository(IContentBlockRepository):
    """In-memory repository: for tests or to run the backend without a database (the data is lost on restart)."""

    def __init__(self):
        """Inizializza l'archivio vuoto."""
        self._documents: dict[str, dict] = {}

    def get(self, block_id: str) -> ContentBlock | None:
        """Block rebuilt from the saved copy."""
        document = self._documents.get(block_id)
        return ContentBlock.from_dict(deepcopy(document)) if document is not None else None

    def search(self, criteria: ContentBlockFilter | None = None, skip: int = 0, limit: int = 50) -> list[ContentBlock]:
        """Blocks filtered and sorted by descending modification date."""
        return [ContentBlock.from_dict(deepcopy(document)) for document in self._matching(criteria)[skip:skip + limit]]

    def list_summaries(self, criteria: ContentBlockFilter | None = None, skip: int = 0,
                       limit: int = 50) -> list[ContentBlockSummary]:
        """Summaries filtered and sorted by descending modification date."""
        return [
            ContentBlockSummary(
                document["id"], document["title"], document.get("description", ""), document.get("source"),
                [content["type"] for content in document["contents"]], document["created_at"], document["updated_at"],
            )
            for document in self._matching(criteria)[skip:skip + limit]
        ]

    def count(self, criteria: ContentBlockFilter | None = None) -> int:
        """Number of blocks in memory matching the criteria."""
        return len(self._matching(criteria))

    def sources(self) -> list[str]:
        """File di origine distinti."""
        return sorted({document["source"] for document in self._documents.values() if document.get("source")})

    def save(self, block: ContentBlock) -> None:
        """Saves a serialized copy, as a database would."""
        self._documents[block.id] = block.to_dict()

    def delete(self, block_id: str) -> bool:
        """Deletes the block if it exists."""
        return self._documents.pop(block_id, None) is not None

    def _matching(self, criteria: ContentBlockFilter | None) -> list[dict]:
        """Documents matching the criteria, from the most recent."""
        criteria = criteria or ContentBlockFilter()
        documents = [document for document in self._documents.values() if criteria.matches(document)]
        return sorted(documents, key=lambda document: document["updated_at"], reverse=True)
