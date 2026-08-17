"""Unit tests for deterministic chapter detection."""

from pathlib import Path

from story_companion.chapter_detection import detect_chapters

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "synthetic_book.txt"


def test_detects_chapters_and_offsets() -> None:
    text = FIXTURE_PATH.read_text(encoding="utf-8")

    chapters = detect_chapters(text)

    assert [chapter.title for chapter in chapters] == [
        "CHAPTER 1: ARRIVAL",
        "Chapter 2 - The Lantern",
        "CHAPTER III: RETURN",
    ]
    assert text[chapters[0].start_offset : chapters[0].end_offset].startswith("CHAPTER 1: ARRIVAL")
    assert "Chapter 2 - The Lantern" not in text[chapters[0].start_offset : chapters[0].end_offset]


def test_uses_single_fallback_chapter_when_no_heading_is_found() -> None:
    text = "A short text without a structural heading."

    chapters = detect_chapters(text)

    assert len(chapters) == 1
    assert chapters[0].title == "Full text"
    assert chapters[0].start_offset == 0
    assert chapters[0].end_offset == len(text)
