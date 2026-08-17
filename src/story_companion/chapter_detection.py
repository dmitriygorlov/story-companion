"""Deterministic chapter boundary detection for plain-text books."""

import re
from dataclasses import dataclass

_CHAPTER_HEADING = re.compile(
    r"^chapter\s+(?:\d+|[ivxlcdm]+|[a-z]+(?:-[a-z]+)*)"
    r"(?:\s*[:.\-—]\s*.+)?$",
    re.IGNORECASE,
)
_SPECIAL_HEADING = re.compile(
    r"^(?:prologue|epilogue)(?:\s*[:.\-—]\s*.+)?$",
    re.IGNORECASE,
)
_MAX_HEADING_LENGTH = 120


@dataclass(frozen=True, slots=True)
class DetectedChapter:
    """A probable chapter and its character offsets in the source text."""

    number: int
    title: str
    start_offset: int
    end_offset: int


def _is_probable_heading(line: str) -> bool:
    candidate = line.strip()
    if not candidate or len(candidate) > _MAX_HEADING_LENGTH:
        return False
    return bool(_CHAPTER_HEADING.fullmatch(candidate) or _SPECIAL_HEADING.fullmatch(candidate))


def detect_chapters(text: str) -> tuple[DetectedChapter, ...]:
    """Detect probable chapter headings using line-based rules.

    Headings must be on their own line and look like ``Chapter 1``,
    ``Chapter III: A Title``, ``Prologue``, or ``Epilogue``. If no heading is
    found, the entire text is exposed as one chapter so every accepted book has
    a selectable spoiler boundary.
    """

    headings: list[tuple[int, str]] = []
    offset = 0

    for line in text.splitlines(keepends=True):
        if _is_probable_heading(line):
            headings.append((offset, line.strip()))
        offset += len(line)

    if not headings:
        return (DetectedChapter(1, "Full text", 0, len(text)),)

    chapters = []
    for index, (start_offset, title) in enumerate(headings):
        end_offset = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        chapters.append(
            DetectedChapter(
                number=index + 1,
                title=title,
                start_offset=start_offset,
                end_offset=end_offset,
            )
        )

    return tuple(chapters)
