"""Temporary local storage with spoiler-scoped text access."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from uuid import uuid4

from story_companion.chapter_detection import DetectedChapter, detect_chapters
from story_companion.processing_context import ChapterContext, SpoilerSafeBookContext


class BookNotFoundError(KeyError):
    """Raised when a book identifier is unknown to this process."""


class SpoilerBoundaryNotSetError(RuntimeError):
    """Raised when text is requested before a spoiler boundary is selected."""


@dataclass(frozen=True, slots=True)
class BookRecord:
    """Public metadata and processing state for a temporarily stored book."""

    book_id: str
    filename: str
    title: str
    size_bytes: int
    character_count: int
    chapters: tuple[DetectedChapter, ...]
    spoiler_boundary: int | None = None


@dataclass(frozen=True, slots=True)
class _StoredBook:
    """Internal storage details unavailable to downstream processing."""

    record: BookRecord
    path: Path
    chapter_end_bytes: tuple[int, ...]


class BookWorkspace:
    """Own uploaded files and expose text only through a spoiler boundary."""

    def __init__(self, root: Path | None = None) -> None:
        self._temporary_directory: TemporaryDirectory[str] | None = None
        if root is None:
            self._temporary_directory = TemporaryDirectory(prefix="story-companion-")
            root = Path(self._temporary_directory.name)

        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._books: dict[str, _StoredBook] = {}
        self._lock = RLock()

    def create_book(self, filename: str, text: str, uploaded_size_bytes: int) -> BookRecord:
        """Persist one normalized UTF-8 book and return its metadata."""

        book_id = uuid4().hex
        book_directory = self._root / book_id
        book_directory.mkdir()
        book_path = book_directory / "book.txt"
        encoded_text = text.encode("utf-8")
        book_path.write_bytes(encoded_text)

        chapters = detect_chapters(text)
        chapter_end_bytes = _byte_offsets(
            text,
            (chapter.end_offset for chapter in chapters),
        )
        record = BookRecord(
            book_id=book_id,
            filename=filename,
            title=Path(filename).stem,
            size_bytes=uploaded_size_bytes,
            character_count=len(text),
            chapters=chapters,
        )
        with self._lock:
            self._books[book_id] = _StoredBook(
                record=record,
                path=book_path,
                chapter_end_bytes=chapter_end_bytes,
            )
        return record

    def get_book(self, book_id: str) -> BookRecord:
        """Return metadata without reading the stored book text."""

        with self._lock:
            return self._get_stored_book(book_id).record

    def set_spoiler_boundary(self, book_id: str, chapter_number: int) -> BookRecord:
        """Select the last chapter that downstream processing may access."""

        with self._lock:
            stored_book = self._get_stored_book(book_id)
            record = stored_book.record
            if chapter_number < 1 or chapter_number > len(record.chapters):
                raise ValueError(f"chapter_number must be between 1 and {len(record.chapters)}")

            updated_record = replace(record, spoiler_boundary=chapter_number)
            self._books[book_id] = replace(stored_book, record=updated_record)
            return updated_record

    def read_spoiler_safe_text(self, book_id: str) -> str:
        """Read detected chapter text at or before the selected boundary."""

        with self._lock:
            stored_book = self._get_stored_book(book_id)
            allowed_text = self._read_allowed_text(stored_book)
            first_chapter_offset = stored_book.record.chapters[0].start_offset
            return allowed_text[first_chapter_offset:]

    def build_processing_context(self, book_id: str) -> SpoilerSafeBookContext:
        """Build chapter-scoped input without exposing unrestricted storage."""

        with self._lock:
            stored_book = self._get_stored_book(book_id)
            record = stored_book.record
            allowed_text = self._read_allowed_text(stored_book)
            boundary = record.spoiler_boundary
            if boundary is None:
                raise SpoilerBoundaryNotSetError(book_id)

            chapter_contexts = []
            for chapter in record.chapters[:boundary]:
                chapter_contexts.append(
                    ChapterContext(
                        number=chapter.number,
                        title=chapter.title,
                        start_offset=chapter.start_offset,
                        end_offset=chapter.end_offset,
                        text=allowed_text[chapter.start_offset : chapter.end_offset],
                    )
                )

            return SpoilerSafeBookContext(
                book_id=book_id,
                through_chapter=boundary,
                chapters=tuple(chapter_contexts),
            )

    def _read_allowed_text(self, stored_book: _StoredBook) -> str:
        record = stored_book.record
        if record.spoiler_boundary is None:
            raise SpoilerBoundaryNotSetError(record.book_id)

        allowed_bytes = stored_book.chapter_end_bytes[record.spoiler_boundary - 1]
        with stored_book.path.open("rb") as book_file:
            return book_file.read(allowed_bytes).decode("utf-8")

    def _get_stored_book(self, book_id: str) -> _StoredBook:
        try:
            return self._books[book_id]
        except KeyError as error:
            raise BookNotFoundError(book_id) from error


def _byte_offsets(text: str, character_offsets: Iterable[int]) -> tuple[int, ...]:
    """Convert ordered character offsets to UTF-8 byte offsets in one pass."""

    byte_offsets = []
    previous_character_offset = 0
    previous_byte_offset = 0

    for character_offset in character_offsets:
        segment = text[previous_character_offset:character_offset]
        previous_byte_offset += len(segment.encode("utf-8"))
        byte_offsets.append(previous_byte_offset)
        previous_character_offset = character_offset

    return tuple(byte_offsets)
