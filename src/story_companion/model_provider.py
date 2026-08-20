"""Narrow model-provider boundary for character extraction."""

from collections.abc import Callable
from typing import Protocol

from story_companion.extraction_schemas import CharacterExtractionResult
from story_companion.processing_context import SpoilerSafeBookContext


class CharacterProvider(Protocol):
    """Extract structured characters from an already spoiler-safe context."""

    async def extract_characters(
        self,
        context: SpoilerSafeBookContext,
    ) -> CharacterExtractionResult: ...


class CharacterProviderError(RuntimeError):
    """Raised when a configured provider cannot produce a usable result."""


class CharacterProviderInputTooLargeError(CharacterProviderError):
    """Raised before a provider call when the allowed context is too large."""


class FakeCharacterProvider:
    """Deterministic injectable provider for tests and local contract checks."""

    def __init__(
        self,
        result_factory: Callable[[SpoilerSafeBookContext], CharacterExtractionResult],
    ) -> None:
        self._result_factory = result_factory

    async def extract_characters(
        self,
        context: SpoilerSafeBookContext,
    ) -> CharacterExtractionResult:
        return self._result_factory(context)
