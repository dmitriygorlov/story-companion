"""Tests for the hosted provider without making network calls."""

import asyncio

import pytest

from story_companion.extraction_schemas import (
    EpistemicCategory,
)
from story_companion.model_provider import (
    CharacterProviderError,
    CharacterProviderInputTooLargeError,
)
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
                                chapter_number=1,
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
    evidence = result.characters[0].claims[0].evidence[0]
    assert evidence.book_id == context.book_id
    assert evidence.start_offset == 0
    assert evidence.end_offset == len(excerpt)
    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["text_format"] is CharacterExtractionPayload
    assert call["reasoning"] == {"effort": "none"}
    assert "BOOK_ID" not in str(call["input"])
    assert "Mara arrived." in str(call["input"])


@pytest.mark.parametrize(
    ("chapter_text", "excerpt", "message"),
    [
        ("Mara arrived.", "Mara left.", "not found"),
        ("Mara arrived. Mara arrived.", "Mara arrived.", "ambiguous"),
    ],
)
def test_provider_rejects_unresolvable_evidence(
    chapter_text: str,
    excerpt: str,
    message: str,
) -> None:
    context = SpoilerSafeBookContext(
        book_id="book-1",
        through_chapter=1,
        chapters=(
            ChapterContext(
                number=1,
                title="Chapter 1",
                start_offset=10,
                end_offset=10 + len(chapter_text),
                text=chapter_text,
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
                                chapter_number=1,
                                excerpt=excerpt,
                            )
                        ],
                    )
                ],
            )
        ]
    )
    provider = OpenAICharacterProvider(
        api_key="test-key",
        client=StubOpenAIClient(payload),
    )

    with pytest.raises(CharacterProviderError, match=message):
        asyncio.run(provider.extract_characters(context))


def test_provider_resolves_wrapped_source_text_to_exact_offsets() -> None:
    chapter_text = "Mara arrived before\nsunrise."
    model_excerpt = "Mara arrived before sunrise."
    context = SpoilerSafeBookContext(
        book_id="book-1",
        through_chapter=1,
        chapters=(
            ChapterContext(
                number=1,
                title="Chapter 1",
                start_offset=20,
                end_offset=20 + len(chapter_text),
                text=chapter_text,
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
                        value="Arrived before sunrise",
                        category=EpistemicCategory.BOOK_FACT,
                        evidence=[
                            ProviderEvidenceSpan(
                                chapter_number=1,
                                excerpt=model_excerpt,
                            )
                        ],
                    )
                ],
            )
        ]
    )
    provider = OpenAICharacterProvider(
        api_key="test-key",
        client=StubOpenAIClient(payload),
    )

    result = asyncio.run(provider.extract_characters(context))

    evidence = result.characters[0].claims[0].evidence[0]
    assert evidence.start_offset == 20
    assert evidence.end_offset == 20 + len(chapter_text)
    assert evidence.excerpt == chapter_text


def test_provider_recovers_long_unique_exact_subspan_from_changed_edge() -> None:
    chapter_text = (
        "The dog belongs to a farmer, you know, and he says it is very useful in the quiet fields."
    )
    model_excerpt = (
        "The dog will belong to a farmer, you know, and he says it is very useful "
        "in the quiet fields."
    )
    context = SpoilerSafeBookContext(
        book_id="book-1",
        through_chapter=1,
        chapters=(
            ChapterContext(
                number=1,
                title="Chapter 1",
                start_offset=0,
                end_offset=len(chapter_text),
                text=chapter_text,
            ),
        ),
    )
    payload = CharacterExtractionPayload(
        characters=[
            ProviderCharacter(
                id="dog",
                display_name="the dog",
                aliases=[],
                claims=[
                    ProviderCharacterClaim(
                        attribute="owner",
                        value="Belongs to a farmer",
                        category=EpistemicCategory.BOOK_FACT,
                        evidence=[
                            ProviderEvidenceSpan(
                                chapter_number=1,
                                excerpt=model_excerpt,
                            )
                        ],
                    )
                ],
            )
        ]
    )
    provider = OpenAICharacterProvider(
        api_key="test-key",
        client=StubOpenAIClient(payload),
    )

    result = asyncio.run(provider.extract_characters(context))

    evidence = result.characters[0].claims[0].evidence[0]
    assert evidence.excerpt in chapter_text
    assert len(evidence.excerpt) >= 40
    assert "will belong" not in evidence.excerpt
    assert chapter_text[evidence.start_offset : evidence.end_offset] == evidence.excerpt


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
