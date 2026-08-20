"""Unit tests for character extraction and evidence contracts."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from story_companion.book_workspace import BookWorkspace
from story_companion.extraction_schemas import (
    Character,
    CharacterClaim,
    CharacterExtractionResult,
    EpistemicCategory,
    EvidenceSpan,
    EvidenceValidationError,
    validate_extraction_evidence,
)


def build_context(tmp_path: Path):
    text = "Chapter 1\nMara carries a lantern.\n\nChapter 2\nMara learns the future secret.\n"
    workspace = BookWorkspace(tmp_path)
    book = workspace.create_book("synthetic.txt", text, len(text.encode("utf-8")))
    workspace.set_spoiler_boundary(book.book_id, 1)
    return text, workspace.build_processing_context(book.book_id)


def test_accepts_exact_evidence_inside_allowed_context(tmp_path: Path) -> None:
    text, context = build_context(tmp_path)
    excerpt = "Mara carries a lantern."
    start_offset = text.index(excerpt)
    evidence = EvidenceSpan(
        book_id=context.book_id,
        chapter_number=1,
        start_offset=start_offset,
        end_offset=start_offset + len(excerpt),
        excerpt=excerpt,
    )
    result = CharacterExtractionResult(
        book_id=context.book_id,
        through_chapter=1,
        characters=[
            Character(
                id="mara",
                display_name="Mara",
                claims=[
                    CharacterClaim(
                        attribute="possessions",
                        value="Carries a lantern",
                        category=EpistemicCategory.BOOK_FACT,
                        evidence=[evidence],
                    )
                ],
            )
        ],
    )

    validate_extraction_evidence(result, context)


def test_rejects_evidence_from_a_future_chapter(tmp_path: Path) -> None:
    text, context = build_context(tmp_path)
    excerpt = "Mara learns the future secret."
    start_offset = text.index(excerpt)
    future_evidence = EvidenceSpan(
        book_id=context.book_id,
        chapter_number=2,
        start_offset=start_offset,
        end_offset=start_offset + len(excerpt),
        excerpt=excerpt,
    )
    result = CharacterExtractionResult(
        book_id=context.book_id,
        through_chapter=1,
        characters=[
            Character(
                id="mara",
                display_name="Mara",
                claims=[
                    CharacterClaim(
                        attribute="knowledge",
                        value="Knows the future secret",
                        category=EpistemicCategory.BOOK_FACT,
                        evidence=[future_evidence],
                    )
                ],
            )
        ],
    )

    with pytest.raises(EvidenceValidationError, match="disallowed chapter 2"):
        validate_extraction_evidence(result, context)


def test_rejects_an_excerpt_that_does_not_match_source_text(tmp_path: Path) -> None:
    text, context = build_context(tmp_path)
    source_excerpt = "Mara carries a lantern."
    start_offset = text.index(source_excerpt)
    evidence = EvidenceSpan(
        book_id=context.book_id,
        chapter_number=1,
        start_offset=start_offset,
        end_offset=start_offset + len(source_excerpt),
        excerpt="Mara carries a sword....",
    )
    result = CharacterExtractionResult(
        book_id=context.book_id,
        through_chapter=1,
        characters=[
            Character(
                id="mara",
                display_name="Mara",
                claims=[
                    CharacterClaim(
                        attribute="possessions",
                        value="Carries a sword",
                        category=EpistemicCategory.BOOK_FACT,
                        evidence=[evidence],
                    )
                ],
            )
        ],
    )

    with pytest.raises(EvidenceValidationError, match="does not match source text"):
        validate_extraction_evidence(result, context)


def test_book_facts_require_evidence() -> None:
    with pytest.raises(ValidationError, match="book_fact claims require evidence"):
        CharacterClaim(
            attribute="appearance",
            value="Dark hair",
            category=EpistemicCategory.BOOK_FACT,
        )
