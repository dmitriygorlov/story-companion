# Story Companion Product Specification

## Product promise

Story Companion helps a reader remember a book without revealing anything beyond
their current position. Its answers are useful because they are inspectable:
canon, interpretation, and invention never share the same label.

The project began with two concrete readers in mind. One is a young reader who
loves large casts but does not want a character guide to spoil the next chapter.
The other is a map-minded reader who wants to reconstruct routes, distances, and
travel time without quietly filling gaps with unsupported certainty.

## Problem

Search results, fan wikis, and general-purpose assistants usually know the whole
story. Even a short character lookup can reveal a later identity, death,
relationship, or destination. They also tend to flatten three different kinds of
information into one confident answer:

- what the book explicitly states;
- what a reader or model can reasonably infer;
- what an illustrator or map-maker must invent to complete a visual.

Story Companion treats both spoiler scope and epistemic provenance as product
data, not presentation hints.

## Users

The primary user is a reader of fiction or narrative non-fiction who:

- is returning to a complex book after a break;
- wants a cast refresher without a full chapter summary;
- follows clues, relationships, locations, or journeys;
- benefits from structured or visual notes;
- is willing to provide a legally obtained local text file.

The current release is intended for local, single-user use. It is not yet a
hosted service for storing a personal library.

## Released MVP: version 0.2.0

A reader can:

1. Open a responsive local web application.
2. Upload a non-empty UTF-8 `.txt` file up to 5 MB.
3. Review probable chapter headings found by deterministic Python logic.
4. Select the last chapter they have completed.
5. Generate character profiles from only the text at or before that boundary
   when an extraction provider is configured.
6. Inspect the exact passage supporting every book fact or model inference.
7. See each claim labeled as `book_fact`, `model_inference`, or
   `creative_choice`.
8. Try an original three-chapter sample without configuring a model provider.

The sample uses the real upload, chapter, and boundary flow. Its precomputed
character result is validated against the original sample text in automated
tests. It is a product demonstration, not a substitute for live extraction.

## Spoiler-safe behavior

The selected chapter is a hard, inclusive information boundary.

- A boundary must be selected before text can enter semantic processing.
- The workspace constructs a new context containing only allowed chapters.
- Model adapters receive that context, never the unrestricted book.
- There is no public API endpoint for retrieving unrestricted uploaded text.
- Evidence must identify the same book, an allowed chapter, valid source
  offsets, and an exact excerpt from the normalized text.
- Unsupported or future-chapter evidence causes the whole provider result to be
  rejected rather than partially trusted.
- If a requested fact needs later text, the product should omit it. It must not
  confirm or deny guesses about future identities, events, or relationships.

Front matter before the first detected chapter is excluded from the processing
context. This reduces the risk that a table of contents leaks future chapter
titles at an early boundary.

## Provenance language

- **Book fact** — explicitly supported by one or more permitted source passages.
- **Model inference** — an interpretation grounded in permitted passages but not
  directly stated as canon.
- **Creative choice** — a detail introduced for a map or illustration. It must
  not masquerade as book evidence.

Book facts and model inferences require evidence. Creative choices must be
visually and structurally separate from claims about the text.

## Next product slices

The evidence model should next support:

1. Relationship edges and changes through the selected chapter
2. An event timeline with explicit ordering confidence
3. Journey legs with stated distances, inferred estimates, and unknown gaps
4. A map view that distinguishes book geography from cartographic choices
5. Optional illustration briefs built only from spoiler-safe character evidence

These are planned features, not part of the released MVP.

## Non-goals

The current MVP does not:

- replace reading the book or generate exhaustive chapter summaries;
- answer from text beyond the selected boundary;
- claim that model interpretation is canon;
- train a model on uploaded books;
- provide book discovery, file sharing, or a public book library;
- support EPUB, PDF, OCR, or scanned pages;
- provide accounts, collaboration, billing, durable storage, or production
  moderation;
- generate relationship graphs, timelines, maps, or illustrations yet;
- guarantee one correct interpretation of ambiguous literature.

## Success criteria for the current release

- A new contributor can run the demo from the README without an API key.
- Every automated test and Ruff check passes on Python 3.12.
- A synthetic future-chapter phrase cannot appear in the sample result.
- Invalid evidence never reaches an API client as a successful extraction.
- Repository examples contain only original or synthetic text and no secrets.
