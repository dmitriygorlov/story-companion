"""Integration tests for the Story Companion API."""

import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient, Response

from story_companion.book_workspace import BookWorkspace
from story_companion.extraction_schemas import (
    Character,
    CharacterClaim,
    CharacterExtractionResult,
    EpistemicCategory,
    EvidenceSpan,
)
from story_companion.main import create_app
from story_companion.model_provider import FakeCharacterProvider
from story_companion.processing_context import SpoilerSafeBookContext

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "synthetic_book.txt"


async def request(
    app,
    method: str,
    path: str,
    **kwargs,
) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_health_returns_ok(tmp_path: Path) -> None:
    app = create_app(BookWorkspace(tmp_path))

    response = asyncio.run(request(app, "GET", "/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_select_boundary_and_read_safe_context(tmp_path: Path) -> None:
    app = create_app(BookWorkspace(tmp_path))
    fixture_content = FIXTURE_PATH.read_bytes()

    upload = asyncio.run(
        request(
            app,
            "POST",
            "/books",
            files={"book_file": ("synthetic_book.txt", fixture_content, "text/plain")},
        )
    )

    assert upload.status_code == 201
    payload = upload.json()
    book_id = payload["book"]["id"]
    assert payload["book"] == {
        "id": book_id,
        "filename": "synthetic_book.txt",
        "title": "synthetic_book",
        "encoding": "utf-8",
        "size_bytes": len(fixture_content),
        "character_count": len(fixture_content.decode("utf-8")),
        "chapter_count": 3,
    }
    assert payload["chapters"] == [
        {"number": 1, "title": "CHAPTER 1: ARRIVAL"},
        {"number": 2, "title": "Chapter 2 - The Lantern"},
        {"number": 3, "title": "CHAPTER III: RETURN"},
    ]
    assert (tmp_path / book_id / "book.txt").read_bytes() == fixture_content

    context_without_boundary = asyncio.run(request(app, "GET", f"/books/{book_id}/context"))
    assert context_without_boundary.status_code == 409

    boundary = asyncio.run(
        request(
            app,
            "PUT",
            f"/books/{book_id}/spoiler-boundary",
            json={"chapter_number": 2},
        )
    )
    assert boundary.status_code == 200
    assert boundary.json() == {
        "book_id": book_id,
        "chapter_number": 2,
        "chapter_title": "Chapter 2 - The Lantern",
    }

    context = asyncio.run(request(app, "GET", f"/books/{book_id}/context"))
    assert context.status_code == 200
    assert context.json()["through_chapter"] == 2
    assert context.json()["text"].startswith("CHAPTER 1: ARRIVAL")
    assert "A Small Synthetic Story" not in context.json()["text"]
    assert "The lantern glowed beside the window." in context.json()["text"]
    assert "The final secret was written on the gate." not in context.json()["text"]


def test_upload_rejects_non_utf8_txt(tmp_path: Path) -> None:
    app = create_app(BookWorkspace(tmp_path))

    response = asyncio.run(
        request(
            app,
            "POST",
            "/books",
            files={"book_file": ("book.txt", b"\xff\xfe", "text/plain")},
        )
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "TXT file must be valid UTF-8"


def test_boundary_must_reference_a_detected_chapter(tmp_path: Path) -> None:
    app = create_app(BookWorkspace(tmp_path))
    fixture_content = FIXTURE_PATH.read_bytes()
    upload = asyncio.run(
        request(
            app,
            "POST",
            "/books",
            files={"book_file": ("synthetic_book.txt", fixture_content, "text/plain")},
        )
    )
    book_id = upload.json()["book"]["id"]

    response = asyncio.run(
        request(
            app,
            "PUT",
            f"/books/{book_id}/spoiler-boundary",
            json={"chapter_number": 4},
        )
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "chapter_number must be between 1 and 3"


def test_character_provider_receives_only_spoiler_safe_context(tmp_path: Path) -> None:
    received_contexts: list[SpoilerSafeBookContext] = []

    def result_factory(context: SpoilerSafeBookContext) -> CharacterExtractionResult:
        received_contexts.append(context)
        excerpt = "Mara arrived before sunrise."
        chapter = context.chapters[0]
        start_offset = chapter.start_offset + chapter.text.index(excerpt)
        return CharacterExtractionResult(
            book_id=context.book_id,
            through_chapter=context.through_chapter,
            characters=[
                Character(
                    id="mara",
                    display_name="Mara",
                    claims=[
                        CharacterClaim(
                            attribute="action",
                            value="Arrived before sunrise",
                            category=EpistemicCategory.BOOK_FACT,
                            evidence=[
                                EvidenceSpan(
                                    book_id=context.book_id,
                                    chapter_number=chapter.number,
                                    start_offset=start_offset,
                                    end_offset=start_offset + len(excerpt),
                                    excerpt=excerpt,
                                )
                            ],
                        )
                    ],
                )
            ],
        )

    provider = FakeCharacterProvider(result_factory)
    app = create_app(BookWorkspace(tmp_path), provider)
    upload = asyncio.run(
        request(
            app,
            "POST",
            "/books",
            files={"book_file": ("synthetic_book.txt", FIXTURE_PATH.read_bytes(), "text/plain")},
        )
    )
    book_id = upload.json()["book"]["id"]
    asyncio.run(
        request(
            app,
            "PUT",
            f"/books/{book_id}/spoiler-boundary",
            json={"chapter_number": 1},
        )
    )

    response = asyncio.run(request(app, "POST", f"/books/{book_id}/characters"))

    assert response.status_code == 200
    assert response.json()["characters"][0]["display_name"] == "Mara"
    assert response.json()["characters"][0]["claims"][0]["category"] == "book_fact"
    assert len(received_contexts) == 1
    assert received_contexts[0].through_chapter == 1
    assert "The lantern glowed beside the window." not in received_contexts[0].text


def test_character_endpoint_rejects_invalid_provider_evidence(tmp_path: Path) -> None:
    def invalid_result(context: SpoilerSafeBookContext) -> CharacterExtractionResult:
        excerpt = "The final secret was written on the gate."
        return CharacterExtractionResult(
            book_id=context.book_id,
            through_chapter=context.through_chapter,
            characters=[
                Character(
                    id="mara",
                    display_name="Mara",
                    claims=[
                        CharacterClaim(
                            attribute="knowledge",
                            value="Knows the final secret",
                            category=EpistemicCategory.BOOK_FACT,
                            evidence=[
                                EvidenceSpan(
                                    book_id=context.book_id,
                                    chapter_number=3,
                                    start_offset=300,
                                    end_offset=300 + len(excerpt),
                                    excerpt=excerpt,
                                )
                            ],
                        )
                    ],
                )
            ],
        )

    app = create_app(BookWorkspace(tmp_path), FakeCharacterProvider(invalid_result))
    upload = asyncio.run(
        request(
            app,
            "POST",
            "/books",
            files={"book_file": ("synthetic_book.txt", FIXTURE_PATH.read_bytes(), "text/plain")},
        )
    )
    book_id = upload.json()["book"]["id"]
    asyncio.run(
        request(
            app,
            "PUT",
            f"/books/{book_id}/spoiler-boundary",
            json={"chapter_number": 1},
        )
    )

    response = asyncio.run(request(app, "POST", f"/books/{book_id}/characters"))

    assert response.status_code == 502
    assert "disallowed chapter 3" in response.json()["detail"]


def test_character_endpoint_reports_unconfigured_provider(tmp_path: Path) -> None:
    app = create_app(BookWorkspace(tmp_path))
    upload = asyncio.run(
        request(
            app,
            "POST",
            "/books",
            files={"book_file": ("synthetic_book.txt", FIXTURE_PATH.read_bytes(), "text/plain")},
        )
    )
    book_id = upload.json()["book"]["id"]

    response = asyncio.run(request(app, "POST", f"/books/{book_id}/characters"))

    assert response.status_code == 503
    assert response.json()["detail"] == "No character extraction provider is configured"
