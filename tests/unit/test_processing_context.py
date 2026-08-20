"""Unit tests for spoiler-safe processing context construction."""

from pathlib import Path

from story_companion.book_workspace import BookWorkspace


def test_context_contains_only_allowed_chapters_with_source_offsets(tmp_path: Path) -> None:
    text = (
        "Synthetic front matter.\n\n"
        "Chapter 1\nMara arrives.\n\n"
        "Chapter 2\nA lantern glows.\n\n"
        "Chapter 3\nA future secret appears.\n"
    )
    workspace = BookWorkspace(tmp_path)
    book = workspace.create_book("synthetic.txt", text, len(text.encode("utf-8")))
    workspace.set_spoiler_boundary(book.book_id, 2)

    context = workspace.build_processing_context(book.book_id)

    assert context.book_id == book.book_id
    assert context.through_chapter == 2
    assert [chapter.number for chapter in context.chapters] == [1, 2]
    assert context.chapters[0].start_offset == text.index("Chapter 1")
    assert context.chapters[0].text.startswith("Chapter 1")
    assert context.chapters[1].start_offset == text.index("Chapter 2")
    assert context.text == workspace.read_spoiler_safe_text(book.book_id)
    assert "Synthetic front matter." not in context.text
    assert "A lantern glows." in context.text
    assert "A future secret appears." not in context.text
