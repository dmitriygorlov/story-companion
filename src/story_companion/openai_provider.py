"""OpenAI-backed character extraction adapter."""

import os
from importlib.resources import files
from typing import Protocol

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from story_companion.extraction_schemas import (
    Character,
    CharacterExtractionResult,
    EpistemicCategory,
)
from story_companion.model_provider import (
    CharacterProviderError,
    CharacterProviderInputTooLargeError,
)
from story_companion.processing_context import SpoilerSafeBookContext

DEFAULT_MODEL = "gpt-5.6-luna"
MAX_INPUT_CHARACTERS = 200_000
MAX_OUTPUT_TOKENS = 5_000


class ProviderEvidenceSpan(BaseModel):
    """Constraint-light evidence shape compatible with Structured Outputs."""

    book_id: str
    chapter_number: int
    start_offset: int
    end_offset: int
    excerpt: str


class ProviderCharacterClaim(BaseModel):
    """Constraint-light claim shape compatible with Structured Outputs."""

    attribute: str
    value: str
    category: EpistemicCategory
    evidence: list[ProviderEvidenceSpan]


class ProviderCharacter(BaseModel):
    """Constraint-light character shape compatible with Structured Outputs."""

    id: str
    display_name: str
    aliases: list[str]
    claims: list[ProviderCharacterClaim]


class CharacterExtractionPayload(BaseModel):
    """The model-owned portion of a character extraction result."""

    characters: list[ProviderCharacter]


class ParsedResponse(Protocol):
    """Minimal response surface used by this adapter."""

    output_parsed: CharacterExtractionPayload | None


class ResponsesClient(Protocol):
    """Minimal structured-response surface used by this adapter."""

    async def parse(self, **kwargs: object) -> ParsedResponse: ...


class OpenAIClient(Protocol):
    """Minimal client surface used by this adapter."""

    responses: ResponsesClient


class OpenAICharacterProvider:
    """Extract structured characters through the OpenAI Responses API."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        client: OpenAIClient | None = None,
    ) -> None:
        self._model = model
        self._client = client if client is not None else AsyncOpenAI(api_key=api_key)
        self._instructions = (
            files("story_companion.prompts")
            .joinpath("character_extraction_v1.txt")
            .read_text(encoding="utf-8")
        )

    async def extract_characters(
        self,
        context: SpoilerSafeBookContext,
    ) -> CharacterExtractionResult:
        input_text = _format_context(context)
        if len(input_text) > MAX_INPUT_CHARACTERS:
            raise CharacterProviderInputTooLargeError(
                "Selected spoiler-safe context is too large for the current extraction pass"
            )

        try:
            response = await self._client.responses.parse(
                model=self._model,
                instructions=self._instructions,
                input=input_text,
                text_format=CharacterExtractionPayload,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                reasoning={"effort": "none"},
            )
        except OpenAIError as error:
            raise CharacterProviderError("OpenAI request failed") from error

        payload = response.output_parsed
        if payload is None:
            raise CharacterProviderError("OpenAI returned no parsed character result")

        try:
            characters = [
                Character.model_validate(character.model_dump()) for character in payload.characters
            ]
            return CharacterExtractionResult(
                book_id=context.book_id,
                through_chapter=context.through_chapter,
                characters=characters,
            )
        except ValidationError as error:
            raise CharacterProviderError("OpenAI returned invalid character data") from error


def openai_provider_from_environment() -> OpenAICharacterProvider | None:
    """Configure the hosted provider only when a local API key is present."""

    load_dotenv(override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("STORY_COMPANION_OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return OpenAICharacterProvider(api_key=api_key, model=model)


def _format_context(context: SpoilerSafeBookContext) -> str:
    sections = [
        f"BOOK_ID: {context.book_id}",
        f"SPOILER_BOUNDARY: chapter {context.through_chapter} inclusive",
        "Offsets below are Python character offsets in the normalized source text.",
    ]
    for chapter in context.chapters:
        sections.append(
            "\n".join(
                [
                    (
                        f"--- CHAPTER {chapter.number} | {chapter.title} | "
                        f"START_OFFSET {chapter.start_offset} | END_OFFSET {chapter.end_offset} ---"
                    ),
                    chapter.text,
                ]
            )
        )
    return "\n\n".join(sections)
