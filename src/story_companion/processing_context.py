"""Spoiler-safe input types for future processing stages."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChapterContext:
    """Allowed chapter text with offsets in the normalized source book."""

    number: int
    title: str
    start_offset: int
    end_offset: int
    text: str


@dataclass(frozen=True, slots=True)
class SpoilerSafeBookContext:
    """The complete and only input exposed to future semantic processing."""

    book_id: str
    through_chapter: int
    chapters: tuple[ChapterContext, ...]

    @property
    def text(self) -> str:
        """Return the contiguous allowed detected chapter text."""

        return "".join(chapter.text for chapter in self.chapters)
