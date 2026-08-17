"""FastAPI application entry point."""

from typing import Annotated, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from story_companion import __version__
from story_companion.book_workspace import (
    BookNotFoundError,
    BookRecord,
    BookWorkspace,
    SpoilerBoundaryNotSetError,
)
from story_companion.schemas import (
    BookMetadata,
    BookResponse,
    ChapterMetadata,
    SpoilerBoundaryResponse,
    SpoilerBoundarySelection,
    SpoilerSafeContextResponse,
)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: Literal["ok"]


def create_app(book_workspace: BookWorkspace | None = None) -> FastAPI:
    """Create the API with an isolated temporary book workspace."""

    workspace = book_workspace or BookWorkspace()
    application = FastAPI(
        title="Story Companion",
        description="Spoiler-safe, evidence-grounded reading companion API.",
        version=__version__,
    )

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        """Report whether the API process is ready to serve requests."""

        return HealthResponse(status="ok")

    @application.post(
        "/books",
        response_model=BookResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["books"],
    )
    async def upload_book(book_file: Annotated[UploadFile, File()]) -> BookResponse:
        """Accept one UTF-8 TXT file and detect probable chapter boundaries."""

        filename = _safe_filename(book_file.filename)
        if not filename.lower().endswith(".txt"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only .txt files are accepted",
            )

        try:
            content = await book_file.read(MAX_UPLOAD_BYTES + 1)
        finally:
            await book_file.close()

        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="TXT file exceeds the 5 MB limit",
            )

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TXT file must be valid UTF-8",
            ) from error

        if not text.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "TXT file must not be empty")

        record = workspace.create_book(filename, text, len(content))
        return _book_response(record)

    @application.get("/books/{book_id}", response_model=BookResponse, tags=["books"])
    def get_book(book_id: str) -> BookResponse:
        """Return metadata and detected chapters for an uploaded book."""

        return _book_response(_get_book_or_404(workspace, book_id))

    @application.put(
        "/books/{book_id}/spoiler-boundary",
        response_model=SpoilerBoundaryResponse,
        tags=["books"],
    )
    def set_spoiler_boundary(
        book_id: str,
        selection: SpoilerBoundarySelection,
    ) -> SpoilerBoundaryResponse:
        """Set an inclusive chapter boundary for all later text access."""

        try:
            record = workspace.set_spoiler_boundary(book_id, selection.chapter_number)
        except BookNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found") from error
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error

        chapter = record.chapters[selection.chapter_number - 1]
        return SpoilerBoundaryResponse(
            book_id=book_id,
            chapter_number=chapter.number,
            chapter_title=chapter.title,
        )

    @application.get(
        "/books/{book_id}/context",
        response_model=SpoilerSafeContextResponse,
        tags=["books"],
    )
    def get_spoiler_safe_context(book_id: str) -> SpoilerSafeContextResponse:
        """Expose the only text surface available to future processing stages."""

        try:
            record = workspace.get_book(book_id)
            text = workspace.read_spoiler_safe_text(book_id)
        except BookNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found") from error
        except SpoilerBoundaryNotSetError as error:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Select a spoiler boundary before requesting processing context",
            ) from error

        return SpoilerSafeContextResponse(
            book_id=book_id,
            through_chapter=record.spoiler_boundary,
            text=text,
        )

    return application


def _safe_filename(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file must have a filename")
    return filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]


def _get_book_or_404(workspace: BookWorkspace, book_id: str) -> BookRecord:
    try:
        return workspace.get_book(book_id)
    except BookNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found") from error


def _book_response(record: BookRecord) -> BookResponse:
    return BookResponse(
        book=BookMetadata(
            id=record.book_id,
            filename=record.filename,
            title=record.title,
            size_bytes=record.size_bytes,
            character_count=record.character_count,
            chapter_count=len(record.chapters),
        ),
        chapters=[
            ChapterMetadata(number=chapter.number, title=chapter.title)
            for chapter in record.chapters
        ],
        spoiler_boundary=record.spoiler_boundary,
    )


app = create_app()
