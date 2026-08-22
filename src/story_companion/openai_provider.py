"""OpenAI-backed character extraction adapter."""

import os
from difflib import SequenceMatcher
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
MIN_RECOVERABLE_EXCERPT_CHARACTERS = 40


class ProviderEvidenceSpan(BaseModel):
    """Model-supplied evidence reference resolved against source text by Python."""

    chapter_number: int
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
                _resolve_character(character, context) for character in payload.characters
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
        f"SPOILER_BOUNDARY: chapter {context.through_chapter} inclusive",
    ]
    for chapter in context.chapters:
        sections.append(
            "\n".join(
                [
                    f"--- CHAPTER {chapter.number} | {chapter.title} ---",
                    chapter.text,
                ]
            )
        )
    return "\n\n".join(sections)


def _resolve_character(
    character: ProviderCharacter,
    context: SpoilerSafeBookContext,
) -> Character:
    """Attach trusted provenance fields and deterministic offsets to model output."""

    character_data = character.model_dump()
    for claim in character_data["claims"]:
        claim["evidence"] = [_resolve_evidence(evidence, context) for evidence in claim["evidence"]]
    return Character.model_validate(character_data)


def _resolve_evidence(
    evidence: dict[str, object],
    context: SpoilerSafeBookContext,
) -> dict[str, object]:
    """Resolve one exact, unique excerpt inside its allowed chapter."""

    chapter_number = evidence["chapter_number"]
    excerpt = evidence["excerpt"]
    if not isinstance(chapter_number, int) or not isinstance(excerpt, str):
        raise CharacterProviderError("OpenAI returned invalid evidence data")

    chapter = next(
        (item for item in context.chapters if item.number == chapter_number),
        None,
    )
    if chapter is None:
        raise CharacterProviderError("OpenAI cited a chapter outside the spoiler boundary")

    relative_start, relative_end = _find_unique_source_span(chapter.text, excerpt)

    start_offset = chapter.start_offset + relative_start
    return {
        "book_id": context.book_id,
        "chapter_number": chapter_number,
        "start_offset": start_offset,
        "end_offset": chapter.start_offset + relative_end,
        "excerpt": chapter.text[relative_start:relative_end],
    }


def _find_unique_source_span(source: str, excerpt: str) -> tuple[int, int]:
    """Locate one excerpt, allowing only deterministic whitespace normalization."""

    exact_start = source.find(excerpt)
    if exact_start >= 0:
        if source.find(excerpt, exact_start + 1) >= 0:
            raise CharacterProviderError("OpenAI returned an ambiguous evidence excerpt")
        return exact_start, exact_start + len(excerpt)

    normalized_source, source_starts, source_ends = _normalize_whitespace_with_offsets(source)
    normalized_excerpt, _, _ = _normalize_whitespace_with_offsets(excerpt)
    normalized_excerpt = normalized_excerpt.strip()
    if not normalized_excerpt:
        raise CharacterProviderError("OpenAI returned an empty evidence excerpt")

    normalized_start = normalized_source.find(normalized_excerpt)
    if normalized_start >= 0:
        if normalized_source.find(normalized_excerpt, normalized_start + 1) >= 0:
            raise CharacterProviderError("OpenAI returned an ambiguous evidence excerpt")

        normalized_end = normalized_start + len(normalized_excerpt)
        return source_starts[normalized_start], source_ends[normalized_end - 1]

    return _find_long_unique_subspan(
        normalized_source,
        normalized_excerpt,
        source_starts,
        source_ends,
    )


def _find_long_unique_subspan(
    normalized_source: str,
    normalized_excerpt: str,
    source_starts: list[int],
    source_ends: list[int],
) -> tuple[int, int]:
    """Recover only a long, unique, still-verbatim portion of an altered excerpt."""

    match = SequenceMatcher(
        None,
        normalized_excerpt,
        normalized_source,
        autojunk=False,
    ).find_longest_match()
    normalized_start = match.b
    normalized_end = match.b + match.size

    if (
        normalized_start > 0
        and normalized_end > normalized_start
        and normalized_source[normalized_start - 1].isalnum()
        and normalized_source[normalized_start].isalnum()
    ):
        next_space = normalized_source.find(" ", normalized_start)
        normalized_start = next_space + 1 if next_space >= 0 else normalized_end
    if (
        normalized_end < len(normalized_source)
        and normalized_end > normalized_start
        and normalized_source[normalized_end - 1].isalnum()
        and normalized_source[normalized_end].isalnum()
    ):
        previous_space = normalized_source.rfind(" ", normalized_start, normalized_end)
        normalized_end = previous_space if previous_space >= 0 else normalized_start

    candidate = normalized_source[normalized_start:normalized_end].strip()
    if len(candidate) < MIN_RECOVERABLE_EXCERPT_CHARACTERS:
        raise CharacterProviderError("OpenAI returned an evidence excerpt not found in the source")

    leading_spaces = len(normalized_source[normalized_start:normalized_end]) - len(
        normalized_source[normalized_start:normalized_end].lstrip()
    )
    normalized_start += leading_spaces
    normalized_end = normalized_start + len(candidate)
    if (
        normalized_source.find(candidate) != normalized_start
        or normalized_source.find(candidate, normalized_start + 1) >= 0
    ):
        raise CharacterProviderError("OpenAI returned an ambiguous evidence excerpt")

    return source_starts[normalized_start], source_ends[normalized_end - 1]


def _normalize_whitespace_with_offsets(text: str) -> tuple[str, list[int], list[int]]:
    """Collapse whitespace runs while retaining their source character bounds."""

    characters: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    for index, character in enumerate(text):
        if character.isspace():
            if characters and characters[-1] == " ":
                ends[-1] = index + 1
            else:
                characters.append(" ")
                starts.append(index)
                ends.append(index + 1)
            continue

        characters.append(character)
        starts.append(index)
        ends.append(index + 1)

    return "".join(characters), starts, ends
