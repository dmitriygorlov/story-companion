# Planned Architecture

## Principles

- Enforce the spoiler boundary before retrieval or generation.
- Preserve source location and provenance through every processing stage.
- Store book facts, model inferences, and creative choices as distinct data types.
- Prefer deterministic validation around probabilistic model output.
- Keep uploaded text private and make deletion behavior explicit.

## Processing pipeline

The planned pipeline is intentionally not implemented in the current foundation.

1. **Upload and validation**
   - Accept a supported user-provided book format.
   - Validate type, size, and extraction safety.
   - Assign an internal book identifier without exposing the original file.

2. **Text extraction and normalization**
   - Extract text and structural markers such as chapters and sections.
   - Normalize formatting while retaining offsets into the source.
   - Record extraction warnings instead of silently dropping content.

3. **Segmentation and evidence indexing**
   - Divide the book into addressable evidence spans.
   - Attach chapter, section, and source-location metadata to every span.
   - Build retrieval data without changing the text's reading order.

4. **Spoiler-boundary resolution**
   - Convert the reader's progress into an inclusive set of allowed spans.
   - Reject ambiguous or invalid progress markers.
   - Ensure all later stages can access only the allowed evidence set.

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
None of those components is included in the initial repository foundation.

## Core provenance model

Future domain models should represent at least:

- The claim or creative detail
- Its classification: `book_fact`, `model_inference`, or `creative_choice`
- Supporting evidence span identifiers, when applicable
- The reader progress boundary used to produce it
- The processing version and confidence or validation state

This separation should be enforced in schemas and storage rather than expressed
only through user-interface text or model prompts.
