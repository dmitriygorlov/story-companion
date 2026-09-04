# Story Companion Architecture

## Design rule

Spoiler safety is enforced before probabilistic processing begins. A prompt may
describe the rule, but the trusted control is the Python workspace that builds a
new context containing only chapters at or before the reader's boundary.

```text
Browser / API client
        |
        v
Upload validation -> deterministic chapter detection -> temporary UTF-8 file
        |                                                   |
        +-------- reader selects inclusive boundary --------+
                                                            |
                                                            v
                                            spoiler-safe byte-prefix read
                                                            |
                                                            v
                                            SpoilerSafeBookContext
                                                            |
                                      +---------------------+------------------+
                                      |                                        |
                                      v                                        v
                            character provider                    deterministic validator
                                      |                                        |
                                      +---------- structured result -----------+
                                                            |
                                                            v
                                            evidence-grounded API / UI
```

The unrestricted stored file is an implementation detail of `BookWorkspace`.
Semantic services receive `SpoilerSafeBookContext`, not a path and not the full
book.

## Implemented components

### FastAPI application

`story_companion.main` owns HTTP validation and assembles dependencies.

- `GET /` serves the bundled web client.
- `GET /config` exposes secret-free runtime capabilities.
- `GET /health` reports process readiness.
- `POST /books` validates and stores one UTF-8 TXT book.
- `GET /books/{book_id}` returns metadata and detected chapters.
- `PUT /books/{book_id}/spoiler-boundary` selects the inclusive boundary.
- `GET /books/{book_id}/context` exposes the spoiler-safe text surface.
- `POST /books/{book_id}/characters` runs extraction and validation.

Static responses include a restrictive Content Security Policy, denied framing,
no-referrer behavior, and MIME sniffing protection.

### Browser client

The client is plain HTML, CSS, and JavaScript packaged with the Python
application. It has no Node build step and no external runtime assets. It:

1. uploads a file;
2. renders the detected chapter list;
3. persists the chosen boundary through the API;
4. requests character extraction;
5. renders provenance categories and expandable evidence passages.

All book/model strings are inserted with DOM text APIs rather than HTML
interpolation.

### Chapter detection

`chapter_detection.py` uses deterministic, line-based rules for headings such
as `Chapter 1`, `Chapter III: Return`, `Prologue`, and `Epilogue`.
Character offsets are retained in the normalized source. If no heading is found,
the whole document becomes one chapter.

This is deliberately a transparent heuristic. The client shows its output before
the reader selects a boundary.

### Temporary book workspace

`BookWorkspace`:

- gives each upload an opaque UUID;
- writes a normalized UTF-8 copy under an OS temporary directory;
- keeps metadata and boundary state in process memory;
- converts chapter character endings to UTF-8 byte endings once at upload time;
- reads only the required byte prefix for later processing;
- excludes front matter before the first detected chapter from semantic context.

The context keeps source character offsets so evidence can be mapped back to the
normalized book.

### Extraction service and provider boundary

`CharacterExtractionService` has a narrow sequence:

1. build `SpoilerSafeBookContext`;
2. pass that object to a `CharacterProvider`;
3. validate the complete result;
4. return it only if validation succeeds.

The provider interface is independent of a vendor. Tests use deterministic fake
providers. The optional OpenAI adapter uses the Responses API with Pydantic
structured output, a versioned prompt, a 5,000-token output cap, and a
200,000-character input guard. The default model is configurable and currently
`gpt-5.6-luna`.

The model proposes chapter numbers and excerpts. Python finds a unique permitted
source span and derives trusted offsets; the model does not author those offsets.

### Provenance validator

Every `book_fact` and `model_inference` must have evidence. For each evidence
span, validation checks:

- the expected book ID;
- a chapter at or before the active boundary;
- offsets contained inside that chapter;
- an excerpt exactly equal to the normalized source slice.

Whitespace introduced by TXT line wrapping can be reconciled deterministically.
An altered quote boundary is recoverable only when a long, unique, contiguous
verbatim subspan remains. Changed words and punctuation are not accepted.

`creative_choice` is a separate schema category and cannot present book
evidence as direct support for invented detail.

### Offline demo

`web/demo/the-lantern-at-brambleford.txt` is a short original fixture. The
browser uploads it through the production endpoints and chooses chapter two.
It then displays `example-result.json` without a model call. A unit test loads
both package resources and runs the sample result through the production
provenance validator, including an assertion that the chapter-three reveal is
absent.

## Runtime and trust boundaries

The 0.2.0 runtime is local and single-process:

- uploaded text lives in an OS temporary directory;
- metadata and reader progress live in memory;
- process restart loses all state;
- multiple Uvicorn workers would not share books;
- there is no account or tenant isolation;
- normal temporary-directory cleanup happens on process shutdown, but there is
  not yet a user-facing deletion workflow.

The web demo is fully offline. Live extraction sends only the selected
spoiler-safe context to the configured provider. API keys are read from the
environment and never returned by `/config`.

## Planned pipeline

New stages should consume the same spoiler-safe context and emit the same
provenance primitives.

1. **Entity reconciliation** — merge aliases while preserving claim evidence.
2. **Relationships** — version edges by chapter and cite each change.
3. **Timeline** — retain stated ordering separately from inferred ordering.
4. **Journey model** — represent locations, legs, quoted distances, calculated
   estimates, and unknown gaps.
5. **Map assembly** — distinguish book geography from cartographic layout.
6. **Illustration brief** — derive visual facts from allowed evidence and label
   every added aesthetic detail as a creative choice.

Only after those contracts stabilize should the project add durable storage,
background jobs, object storage, authentication, or multi-user deployment.

## Deferred infrastructure

The release intentionally does not include:

- a database or migration system;
- Redis, queues, or background workers;
- object storage;
- a retrieval/vector index;
- a JavaScript framework or frontend build pipeline;
- image generation.

Keeping these decisions deferred makes the trust boundary and product behavior
easy to review before operational complexity is introduced.
