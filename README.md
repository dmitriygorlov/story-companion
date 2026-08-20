# Story Companion

Story Companion is a spoiler-safe AI reading companion for user-provided books.
It is intended to turn a reader's current progress into evidence-grounded
character profiles, relationships, timelines, and optional illustrations.

The central product rule is provenance: the application must clearly separate
facts stated in the book from model inferences and creative visual choices.

## Planned features

- Book upload and text processing for supported formats
- Reader-controlled progress boundaries to prevent future events from leaking
- Character profiles with citations to the source text
- Relationship maps and event timelines
- Explicit labels for stated facts, model inferences, and creative choices
- Optional, spoiler-safe character illustrations

See [the product specification](docs/product-spec.md) and
[the planned architecture](docs/architecture.md) for more detail.

## Current status

The first thin vertical slice is implemented. The API accepts a UTF-8 TXT book,
stores it in a process-local temporary workspace, detects probable chapter
headings, and lets the client select an inclusive spoiler boundary. Text exposed
for subsequent processing is restricted to the selected chapter and everything
before it.

The current slice deliberately has no database. Uploads and boundary selections
are lost when the API process stops and are not shared across multiple workers.
The evidence and character-result schemas are defined and validated against
spoiler-safe source offsets. A provider-neutral character extraction endpoint,
deterministic fake provider, and optional OpenAI adapter exercise the full
contract. There is still no image generation, database, background worker, or
user interface.

## API workflow

Upload a UTF-8 `.txt` file of up to 5 MB:

```bash
curl -F "book_file=@path/to/book.txt;type=text/plain" \
  http://localhost:8000/books
```

The response contains a generated book ID, file metadata, and a numbered list of
probable chapters. Chapter detection is deterministic and recognizes headings on
their own line such as `Chapter 1`, `Chapter III: Return`, `Prologue`, and
`Epilogue`. A book with no recognized headings is treated as one chapter.

Select the last chapter that processing may access:

```bash
curl -X PUT -H "Content-Type: application/json" \
  -d '{"chapter_number": 2}' \
  http://localhost:8000/books/BOOK_ID/spoiler-boundary
```

Retrieve the spoiler-safe context that future processing stages will consume:

```bash
curl http://localhost:8000/books/BOOK_ID/context
```

The context endpoint returns `409 Conflict` until a boundary is selected. There
is intentionally no API endpoint for retrieving the unrestricted full text.

`POST /books/{book_id}/characters` runs the provider-neutral extraction path.
Without `OPENAI_API_KEY`, the endpoint returns `503 Service Unavailable`. With a
key, the application uses `gpt-5.6-luna` by default and validates every returned
evidence span before exposing the result. The one-pass adapter currently rejects
contexts over 200,000 characters instead of silently truncating a book. It uses
`reasoning.effort=none` for this bounded extraction task to limit latency and cost.

## Optional OpenAI provider

Create a dedicated OpenAI Platform project and project-scoped key for Story
Companion. Copy `.env.example` to `.env`, set the key locally, and do not commit
that file or paste the key into issues or chat:

```dotenv
OPENAI_API_KEY=your_key_here
STORY_COMPANION_OPENAI_MODEL=gpt-5.6-luna
```

The model setting is deliberately configurable. Automated tests never make
network calls and do not need an API key.

## Local setup

Prerequisites:

- Python 3.12
- `make` (optional; the underlying Python commands can be run directly)

Create and activate a virtual environment, then install the project:

```bash
python -m venv .venv
source .venv/bin/activate
make setup
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
make setup
```

Run the API:

```bash
make run
```

The health check is available at <http://localhost:8000/health>. Interactive API
documentation is available at <http://localhost:8000/docs>.

Run the quality checks:

```bash
make lint
make test
```

## Docker

Copy the example environment file if you want to configure the hosted provider,
exposed port, or log level, then start the service:

```bash
cp .env.example .env
docker compose up --build
```

The default address is <http://localhost:8000>.
