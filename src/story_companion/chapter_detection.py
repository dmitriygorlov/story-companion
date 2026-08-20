"""Deterministic chapter boundary detection for plain-text books."""

import re
from dataclasses import dataclass

_CHAPTER_HEADING = re.compile(
    r"^chapter\s+(?P<label>\d+|[ivxlcdm]+|[a-z]+(?:-[a-z]+)*)"
    r"(?P<suffix>\s*[:.\-—]\s*.*)?$",
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


@dataclass(frozen=True, slots=True)
class _HeadingCandidate:
    offset: int
    title: str
    marker: str


def _match_probable_heading(line: str) -> re.Match[str] | None:
    candidate = line.strip()
    if not candidate or len(candidate) > _MAX_HEADING_LENGTH:
        return None
    return _CHAPTER_HEADING.fullmatch(candidate) or _SPECIAL_HEADING.fullmatch(candidate)


def _heading_marker(candidate: str, match: re.Match[str]) -> str:
    label = match.groupdict().get("label")
    return f"chapter:{label.lower()}" if label else candidate.lower()


def _heading_title(lines: list[str], index: int, candidate: str) -> str:
    """Join a Gutenberg-style bare ``CHAPTER I.`` with its next-line title."""

    if not re.search(r"[:.\-—]\s*$", candidate) or index + 1 >= len(lines):
        return candidate

    following = lines[index + 1].strip()
    if not following or len(following) > _MAX_HEADING_LENGTH or _match_probable_heading(following):
        return candidate

    return f"{candidate.rstrip(':.-— ')}: {following}"


def _remove_repeated_contents_block(
    headings: list[_HeadingCandidate],
) -> list[_HeadingCandidate]:
    """Drop a dense leading table of contents repeated later in the book."""

    longest_repeated_prefix = 0
    for split in range(3, len(headings)):
        prefix = headings[:split]
        later_markers = {heading.marker for heading in headings[split:]}
        is_dense = all(
            right.offset - left.offset <= 500
            for left, right in zip(prefix, prefix[1:], strict=False)
        )
        if is_dense and all(heading.marker in later_markers for heading in prefix):
            longest_repeated_prefix = split

    return headings[longest_repeated_prefix:]


def detect_chapters(text: str) -> tuple[DetectedChapter, ...]:
    """Detect probable chapter headings using line-based rules.

    Headings must be on their own line and look like ``Chapter 1``,
    ``Chapter III: A Title``, ``Prologue``, or ``Epilogue``. If no heading is
    found, the entire text is exposed as one chapter so every accepted book has
    a selectable spoiler boundary.
    """

    headings: list[_HeadingCandidate] = []
    offset = 0
    lines = text.splitlines(keepends=True)

    for index, line in enumerate(lines):
        candidate = line.strip()
        match = _match_probable_heading(candidate)
        if match:
            headings.append(
                _HeadingCandidate(
                    offset=offset,
                    title=_heading_title(lines, index, candidate),
                    marker=_heading_marker(candidate, match),
                )
            )
        offset += len(line)

    headings = _remove_repeated_contents_block(headings)

    if not headings:
        return (DetectedChapter(1, "Full text", 0, len(text)),)

    chapters = []
    for index, heading in enumerate(headings):
        end_offset = headings[index + 1].offset if index + 1 < len(headings) else len(text)
        chapters.append(
            DetectedChapter(
                number=index + 1,
                title=heading.title,
                start_offset=heading.offset,
                end_offset=end_offset,
            )
        )

    return tuple(chapters)
