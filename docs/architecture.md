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
   - A spoiler-safe processing context now carries allowed chapter text and
     stable character offsets in the normalized source.
   - Claim-level evidence schemas and deterministic provenance validation are
     implemented; fine-grained retrieval indexes remain planned.

4. **Spoiler-boundary resolution**
   - Implemented as an inclusive detected-chapter number.
   - Missing and out-of-range boundaries are rejected.
   - The workspace reads only the UTF-8 byte prefix ending at the selected
     chapter. This spoiler-safe context is the only text interface intended for
     subsequent processing stages.

5. **Entity and event extraction**
   - Character, claim, epistemic-category, evidence, and extraction-result
     schemas are defined.
   - An async provider protocol and extraction service are implemented. The
     provider receives only `SpoilerSafeBookContext`, and every result passes
     deterministic evidence validation before it can leave the service.
   - A fake provider covers the end-to-end contract in tests.
   - An optional OpenAI Responses API adapter uses Pydantic structured output.
     It defaults to `gpt-5.6-luna`, ships a versioned extraction prompt, caps
     output tokens, uses no reasoning effort for the bounded extraction task,
     and rejects oversized one-pass contexts before a paid call.
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

The choice of database, task queue, and frontend is deferred. OpenAI is the first
hosted extraction adapter, but the core service remains provider-neutral.

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

For the current TXT adapter, front matter before the first detected heading is
excluded from processing context. This prevents a table of contents from leaking
future chapter titles through an early spoiler boundary. All evidence offsets are
Python character offsets in the normalized UTF-8 text, not byte positions in the
originally uploaded file.

## Core provenance model

The initial character extraction contract represents:

- The provisional character and aliases
- Each individual claim or creative detail
- Its classification: `book_fact`, `model_inference`, or `creative_choice`
- Exact supporting book, chapter, character offsets, and excerpt when applicable
- The reader progress boundary and schema version used to produce the result

Book facts and model inferences require evidence. Creative choices cannot present
book evidence as if it directly supported the invented detail. A deterministic
validator rejects evidence from another book, a later chapter, outside its
chapter offsets, or with an excerpt that does not exactly match source text.
