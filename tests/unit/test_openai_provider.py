"""Tests for the hosted provider without making network calls."""

import asyncio

import pytest

from story_companion.extraction_schemas import (
    EpistemicCategory,
)
from story_companion.model_provider import CharacterProviderInputTooLargeError
from story_companion.openai_provider import (
    CharacterExtractionPayload,
    OpenAICharacterProvider,
    ProviderCharacter,
    ProviderCharacterClaim,
    ProviderEvidenceSpan,
    openai_provider_from_environment,
)
from story_companion.processing_context import ChapterContext, SpoilerSafeBookContext


class StubParsedResponse:
    def __init__(self, payload: CharacterExtractionPayload) -> None:
        self.output_parsed = payload


class StubResponsesClient:
    def __init__(self, payload: CharacterExtractionPayload) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    async def parse(self, **kwargs: object) -> StubParsedResponse:
        self.calls.append(kwargs)
        return StubParsedResponse(self.payload)


class StubOpenAIClient:
    def __init__(self, payload: CharacterExtractionPayload) -> None:
        self.responses = StubResponsesClient(payload)


def test_provider_uses_structured_output_and_wraps_context_metadata() -> None:
    excerpt = "Mara arrived."
    context = SpoilerSafeBookContext(
        book_id="book-1",
        through_chapter=1,
        chapters=(
            ChapterContext(
                number=1,
                title="Chapter 1",
                start_offset=0,
                end_offset=len(excerpt),
                text=excerpt,
            ),
        ),
    )
    payload = CharacterExtractionPayload(
        characters=[
            ProviderCharacter(
                id="mara",
                display_name="Mara",
                aliases=[],
                claims=[
                    ProviderCharacterClaim(
                        attribute="action",
                        value="Arrived",
                        category=EpistemicCategory.BOOK_FACT,
                        evidence=[
                            ProviderEvidenceSpan(
                                book_id=context.book_id,
                                chapter_number=1,
                                start_offset=0,
                                end_offset=len(excerpt),
                                excerpt=excerpt,
                            )
                        ],
                    )
                ],
            )
        ]
    )
    client = StubOpenAIClient(payload)
    provider = OpenAICharacterProvider(
        api_key="test-key",
        model="test-model",
        client=client,
    )

    result = asyncio.run(provider.extract_characters(context))

    assert result.book_id == context.book_id
    assert result.through_chapter == 1
    assert result.characters[0].display_name == "Mara"
    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["text_format"] is CharacterExtractionPayload
    assert call["reasoning"] == {"effort": "none"}
    assert "BOOK_ID: book-1" in str(call["input"])
    assert "Mara arrived." in str(call["input"])


def test_provider_rejects_oversized_context_before_call() -> None:
    text = "x" * 200_001
    context = SpoilerSafeBookContext(
        book_id="book-1",
        through_chapter=1,
        chapters=(
            ChapterContext(
                number=1,
                title="Chapter 1",
                start_offset=0,
                end_offset=len(text),
                text=text,
            ),
        ),
    )
    client = StubOpenAIClient(CharacterExtractionPayload(characters=[]))
    provider = OpenAICharacterProvider(api_key="test-key", client=client)

    with pytest.raises(CharacterProviderInputTooLargeError):
        asyncio.run(provider.extract_characters(context))

    assert client.responses.calls == []


def test_environment_factory_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")

    assert openai_provider_from_environment() is None
