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

This repository contains only the project foundation: a small FastAPI service,
a health endpoint, tests, linting, container configuration, and initial design
documentation. Book processing, AI integrations, persistence, caching, image
generation, and a user interface are intentionally not implemented yet.

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

The health check is available at <http://localhost:8000/health>.

Run the quality checks:

```bash
make lint
make test
```

## Docker

Copy the example environment file if you want to change the exposed port or log
level, then start the service:

```bash
cp .env.example .env
docker compose up --build
```

The default address is <http://localhost:8000>.
