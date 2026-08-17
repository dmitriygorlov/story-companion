# Story Companion Product Specification

## Problem

Readers often need help remembering characters, relationships, and past events,
especially in long or complex books. Existing search results, fan wikis, and AI
assistants can reveal events beyond the reader's current position. They also tend
to mix source facts with interpretation without showing supporting evidence.

Story Companion should help a reader understand only what the book has revealed
so far. Its output should be traceable to the text and explicit about uncertainty.

## Users

The primary user is a reader working through a fiction or narrative non-fiction
book who wants a quick refresher without spoilers. This includes readers returning
after a break, readers following a large cast, and readers who benefit from visual
or structured summaries.

## MVP

The first usable product should let a reader:

1. Provide a legally obtained book file for personal processing.
2. Select a spoiler boundary, such as a chapter or location in the book.
3. View character profiles, relationships, and a timeline derived only from text
   at or before that boundary.
4. Open citations that support factual claims.
5. See clear labels that distinguish:
   - **Book fact:** explicitly supported by text within the allowed boundary.
   - **Model inference:** a reasoned interpretation that is not directly stated.
   - **Creative choice:** a visual or descriptive decision added for illustration.
6. Optionally request character illustrations constrained by spoiler-safe evidence.

## Spoiler-safe behavior

The selected reading position is a hard information boundary, not merely a prompt
preference. Retrieval and downstream processing must exclude later text before any
model creates reader-visible output.

Every reader-visible factual claim should link to one or more evidence spans from
the permitted text. Inferences must be labeled and must identify their supporting
evidence. Creative choices must never be presented as book facts.

If the system cannot support a claim without material from beyond the boundary, it
should omit the claim. It should avoid confirming or denying whether a guessed
future event, identity, or relationship is correct. When the user's progress is
unclear, the system should ask for a boundary before producing a guide.

## Non-goals

The MVP will not:

- Replace reading the book or generate exhaustive chapter summaries.
- Answer questions using text beyond the selected reading position.
- Present model inference as canon.
- Train models on uploaded books.
- Provide a public library, book-sharing service, or piracy workflow.
- Offer collaborative annotations, social features, or authoring tools.
- Guarantee a single correct interpretation of ambiguous literature.
- Support production-scale infrastructure, billing, or moderation workflows.
