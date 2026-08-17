# Planned Architecture

## Principles

- Enforce the spoiler boundary before retrieval or generation.
- Preserve source location and provenance through every processing stage.
- Store book facts, model inferences, and creative choices as distinct data types.
- Prefer deterministic validation around probabilistic model output.
- Keep uploaded text private and make deletion behavior explicit.

## Processing pipeline

The current thin slice implements the deterministic path through upload,
normalization, chapter detection, and spoiler-boundary enforcement. Later
model-backed stages remain planned.

1. **Upload and validation**
   - Implemented for UTF-8 `.txt` files up to 5 MB.
   - Reject invalid encodings, empty files, and other file extensions.
   - Assign an opaque book identifier and save a normalized UTF-8 copy in a
     process-local temporary workspace.

2. **Text extraction and normalization**
   - TXT decoding and UTF-8 normalization are implemented.
   - A deterministic line-based detector recognizes probable `Chapter ...`,
     `Prologue`, and `Epilogue` headings and retains character offsets.
   - Rich document extraction and extraction warnings remain planned.

3. **Segmentation and evidence indexing**
   - Chapter-level segmentation is implemented.
   - Fine-grained evidence spans, source-location metadata, and retrieval indexes
     remain planned.

4. **Spoiler-boundary resolution**
   - Implemented as an inclusive detected-chapter number.
   - Missing and out-of-range boundaries are rejected.
   - The workspace reads only the UTF-8 byte prefix ending at the selected
     chapter. This spoiler-safe context is the only text interface intended for
     subsequent processing stages.

5. **Entity and event extraction**
   - Extract character mentions, aliases, relationships, and events.
   - Require evidence-span identifiers for every proposed book fact.
   - Keep extraction results provisional until validation and reconciliation.

6. **Reconciliation and provenance validation**
   - Merge aliases and repeated mentions without losing evidence links.
   - Detect contradictions and unsupported claims.
   - Classify each item as a book fact or a model inference.

7. **Reader views**
   - Assemble spoiler-safe profiles, relationship data, and timelines.
   - Return citations and provenance labels with each item.
   - Omit or qualify claims that do not pass evidence checks.

8. **Optional illustration planning**
   - Build a visual brief only from allowed facts.
   - Label additions such as clothing details or lighting as creative choices.
   - Generate images in a separate, optional stage.

## Planned components

- **FastAPI service:** HTTP API, validation, and orchestration boundaries.
- **Background workers:** file processing and model-backed stages that should not
  block API requests.
- **Persistent store:** book metadata, progress boundaries, structured results,
  evidence links, and processing state.
- **Object storage:** uploaded books and generated assets with lifecycle controls.
- **Retrieval layer:** spoiler-scoped evidence lookup.
- **Model adapters:** isolated interfaces for extraction, inference, and optional
  illustration providers.

The choice of database, task queue, model providers, and frontend is deferred.
None of those components is included in the current slice.

## Current runtime boundaries

Book metadata and spoiler selections live in process memory, while uploaded text
lives in an operating-system temporary directory owned by the API process. The
temporary directory is cleaned up when the process exits under normal conditions.
This design is suitable only for the first single-process slice: restarts lose
state, multiple API workers do not share books, and there is no user isolation or
durable deletion workflow yet.

The chapter detector is a transparent heuristic, not a parser for every possible
book layout. Its output is returned to the client for review before the spoiler
boundary is selected. Future formats can add dedicated extraction adapters while
keeping the same spoiler-scoped workspace interface.

## Core provenance model

Future domain models should represent at least:

- The claim or creative detail
- Its classification: `book_fact`, `model_inference`, or `creative_choice`
- Supporting evidence span identifiers, when applicable
- The reader progress boundary used to produce it
- The processing version and confidence or validation state

This separation should be enforced in schemas and storage rather than expressed
only through user-interface text or model prompts.
