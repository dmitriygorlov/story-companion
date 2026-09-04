"""Checks for the bundled original demo story and its sample extraction."""

import json
from importlib.resources import files
from pathlib import Path

from story_companion.book_workspace import BookWorkspace
from story_companion.extraction_schemas import (
    CharacterExtractionResult,
    validate_extraction_evidence,
)

DEMO_ROOT = files("story_companion").joinpath("web", "demo")


def test_sample_result_is_exactly_grounded_inside_chapter_two(tmp_path: Path) -> None:
    story = DEMO_ROOT.joinpath("the-lantern-at-brambleford.txt").read_text(encoding="utf-8")
    result_data = json.loads(DEMO_ROOT.joinpath("example-result.json").read_text(encoding="utf-8"))
    workspace = BookWorkspace(tmp_path)
    record = workspace.create_book(
        "the-lantern-at-brambleford.txt",
        story,
        len(story.encode("utf-8")),
    )
    workspace.set_spoiler_boundary(record.book_id, 2)
    context = workspace.build_processing_context(record.book_id)
    result_data["book_id"] = record.book_id
    for character in result_data["characters"]:
        for claim in character["claims"]:
            for evidence in claim["evidence"]:
                evidence["book_id"] = record.book_id
    result = CharacterExtractionResult.model_validate(result_data)

    validate_extraction_evidence(result, context)

    assert len(record.chapters) == 3
    assert result.through_chapter == 2
    assert all(
        evidence.chapter_number <= 2
        for character in result.characters
        for claim in character.claims
        for evidence in claim.evidence
    )
    assert "ruined observatory" not in json.dumps(result_data)
