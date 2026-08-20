"""Character extraction orchestration with mandatory evidence validation."""

from story_companion.book_workspace import BookWorkspace
from story_companion.extraction_schemas import (
    CharacterExtractionResult,
    validate_extraction_evidence,
)
from story_companion.model_provider import CharacterProvider


class CharacterExtractionService:
    """Run one provider only on spoiler-safe text and validate its output."""

    def __init__(self, workspace: BookWorkspace, provider: CharacterProvider) -> None:
        self._workspace = workspace
        self._provider = provider

    async def extract(self, book_id: str) -> CharacterExtractionResult:
        context = self._workspace.build_processing_context(book_id)
        result = await self._provider.extract_characters(context)
        validate_extraction_evidence(result, context)
        return result
