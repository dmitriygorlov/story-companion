"""Unit tests for spoiler-scoped workspace access."""

from pathlib import Path

import pytest

from story_companion.book_workspace import BookWorkspace, SpoilerBoundaryNotSetError


def test_workspace_never_returns_text_without_a_boundary(tmp_path: Path) -> None:
    workspace = BookWorkspace(tmp_path)
    text = "Chapter 1\nCafé is allowed.\n\nChapter 2\nСекрет is not allowed yet.\n"
    record = workspace.create_book("example.txt", text, len(text.encode("utf-8")))

    with pytest.raises(SpoilerBoundaryNotSetError):
        workspace.read_spoiler_safe_text(record.book_id)

    workspace.set_spoiler_boundary(record.book_id, 1)

    assert workspace.read_spoiler_safe_text(record.book_id) == "Chapter 1\nCafé is allowed.\n\n"
