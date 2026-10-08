"""
Migrations of the ContentBlocks saved in MongoDB.

Usage (with the same environment variables as the backend):
    MONGODB_URI=mongodb://localhost:27017 python -m src.content_blocks.migrations
"""
import os
import re

from pymongo.collection import Collection

from ..logging_setup import configure_logging
from .mongo_repository import MongoContentBlockRepository

# Description the Word import gives to the blocks (see ImportContentsModal.svelte), in Italian for the blocks
# imported before the app was translated.
IMPORTED_DESCRIPTION = re.compile(r"^(?:Importato da|Imported from) (.+\.(?:docx|dotx))$", re.IGNORECASE)


def backfill_sources(collection: Collection) -> int:
    """
    Sets source on the blocks imported before the field existed, taking the file name from the description
    "Imported from <file>" ("Importato da <file>" in older blocks). Blocks with a source or another description
    do not change. Returns the number of updated blocks.
    """
    updated = 0
    for document in collection.find({"source": {"$in": [None, ""]}}, {"description": 1}):
        match = IMPORTED_DESCRIPTION.match((document.get("description") or "").strip())
        if match:
            collection.update_one({"_id": document["_id"]}, {"$set": {"source": match.group(1)}})
            updated += 1
    return updated


if __name__ == "__main__":
    configure_logging()
    repository = MongoContentBlockRepository.from_uri(os.environ["MONGODB_URI"], os.getenv("MONGODB_DATABASE", "nocument"))
    print(f"Blocks updated with their source file: {backfill_sources(repository.collection)}")
