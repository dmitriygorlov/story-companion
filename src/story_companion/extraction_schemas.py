"""Structured character extraction and evidence contracts."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from story_companion.processing_context import SpoilerSafeBookContext


class EpistemicCategory(StrEnum):
    """How a claim relates to the source book."""

    BOOK_FACT = "book_fact"
    MODEL_INFERENCE = "model_inference"
    CREATIVE_CHOICE = "creative_choice"


class EvidenceSpan(BaseModel):
    """A precise supporting span in the normalized source text."""

    book_id: str = Field(min_length=1)
    chapter_number: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    excerpt: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_offsets(self) -> "EvidenceSpan":
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class CharacterClaim(BaseModel):
    """One character attribute with an explicit epistemic category."""

    attribute: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)
    category: EpistemicCategory
    evidence: list[EvidenceSpan] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_requirements(self) -> "CharacterClaim":
        if (
            self.category
            in {
                EpistemicCategory.BOOK_FACT,
                EpistemicCategory.MODEL_INFERENCE,
            }
            and not self.evidence
        ):
            raise ValueError(f"{self.category.value} claims require evidence")
        if self.category is EpistemicCategory.CREATIVE_CHOICE and self.evidence:
            raise ValueError("creative_choice claims must not present book evidence as support")
        return self


class Character(BaseModel):
    """A provisional character extracted within one spoiler boundary."""

    id: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    aliases: list[str] = Field(default_factory=list)
    claims: list[CharacterClaim] = Field(default_factory=list)


class CharacterExtractionResult(BaseModel):
    """Validated character candidates for one spoiler-scoped context."""

    schema_version: Literal["1.0"] = "1.0"
    book_id: str = Field(min_length=1)
    through_chapter: int = Field(ge=1)
    characters: list[Character] = Field(default_factory=list)


class EvidenceValidationError(ValueError):
    """Raised when extraction evidence is outside its processing context."""


def validate_extraction_evidence(
    result: CharacterExtractionResult,
    context: SpoilerSafeBookContext,
) -> None:
    """Ensure every evidence span is exact and inside the allowed context."""

    if result.book_id != context.book_id:
        raise EvidenceValidationError("extraction book_id does not match its context")
    if result.through_chapter != context.through_chapter:
        raise EvidenceValidationError("extraction boundary does not match its context")

    chapters = {chapter.number: chapter for chapter in context.chapters}
    for character in result.characters:
        for claim in character.claims:
            for evidence in claim.evidence:
                if evidence.book_id != context.book_id:
                    raise EvidenceValidationError("evidence book_id does not match its context")

                chapter = chapters.get(evidence.chapter_number)
                if chapter is None:
                    raise EvidenceValidationError(
                        f"evidence references disallowed chapter {evidence.chapter_number}"
                    )
                if (
                    evidence.start_offset < chapter.start_offset
                    or evidence.end_offset > chapter.end_offset
                ):
                    raise EvidenceValidationError(
                        f"evidence offsets are outside chapter {evidence.chapter_number}"
                    )

                relative_start = evidence.start_offset - chapter.start_offset
                relative_end = evidence.end_offset - chapter.start_offset
                source_excerpt = chapter.text[relative_start:relative_end]
                if source_excerpt != evidence.excerpt:
                    raise EvidenceValidationError("evidence excerpt does not match source text")
