"""API request and response schemas."""

from pydantic import BaseModel, Field


class ChapterMetadata(BaseModel):
    """A detected chapter exposed to API clients."""

    number: int
    title: str


class BookMetadata(BaseModel):
    """Metadata for an uploaded plain-text book."""

    id: str
    filename: str
    title: str
    encoding: str = "utf-8"
    size_bytes: int
    character_count: int
    chapter_count: int


class BookResponse(BaseModel):
    """An uploaded book and its detected chapter list."""

    book: BookMetadata
    chapters: list[ChapterMetadata]
    spoiler_boundary: int | None


class SpoilerBoundarySelection(BaseModel):
    """The last chapter that downstream processing may access."""

    chapter_number: int = Field(ge=1)


class SpoilerBoundaryResponse(BaseModel):
    """Confirmation of the active spoiler boundary."""

    book_id: str
    chapter_number: int
    chapter_title: str


class SpoilerSafeContextResponse(BaseModel):
    """Text made available to future processing stages."""

    book_id: str
    through_chapter: int
    text: str
