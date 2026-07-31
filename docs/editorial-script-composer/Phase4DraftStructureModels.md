# Phase 4.1 — Draft Structure Models

## Purpose and boundary

Phase 4.1 describes draft structure before provider execution. It models ordered
sections, explicit claim and evidence references, transition slots, and controlled
structural metadata. It does not generate, render, summarize, paraphrase, bind
claims, select evidence, assess coverage, execute providers, or publish language.
It owns no provider, runtime, persistence, network, timestamp, or mutable state.

Empty drafts are invalid. A draft contains at least one section.

## Public models

- `DraftStructure` is the complete structural aggregate.
- `DraftSection` is one ordered section without paragraphs, sentences, or wording.
- `TransitionSlot` is one directed structural edge without transition text.
- `StructuralMetadataEntry` is one controlled structural token.
- `DraftStatus` contains `planned`, `validated`, and `ineligible`.
- `DraftSectionKind` contains the built-in kinds; `custom:<slug>` is the only
  extension form.
- `DraftExecutionPlanReference` binds one plan reference to its exact fingerprint.
- `NormalizedInputDraftScope` owns the claims, evidence, and plans available to
  exactly one normalized input.
- `DraftValidationContext` contains immutable normalized-input scopes.

The public validators are `validate_draft_structure`,
`require_valid_draft_structure`, and `construct_draft_structure`. Identity helpers
for draft, section, and transition artifacts and `draft_semantic_fingerprint` are
public because callers must seal immutable artifacts. Low-level invariant and
normalization helpers and the Phase 4.1 base model are internal.

## Identity and fingerprints

For `DraftStructure`, every field except its own `identity` and `fingerprint` is
identity-bearing. Its semantic fingerprint covers every field except its own
`fingerprint`; consequently the identity is fingerprint-bearing. Nested artifact
identities and fingerprints are included as lineage.

The same rule applies to `DraftSection` and `TransitionSlot`. Identity and
fingerprint derivation use the frozen Module 2.9 canonical SHA-256 algorithms.
Phase 4.1 adds an isolated semantic representation for `section_references` that
binds every reference to its ordinal. Reversing that sequence therefore changes
both the draft identity and fingerprint without changing frozen Phase 1–3 behavior.

All validated strings are NFC-normalized. Canonical bytes are UTF-8 and stable.
There are no timestamps, UUIDs, random values, process data, or locale inputs.

## Ordering and collection semantics

`sections` are ordered by `order_index`. Indexes start at zero, are unique and
contiguous, and `section_references` must exactly equal the embedded sections in
that order. Claim and evidence collections are semantically unordered, reject
duplicates, and are sorted canonically. Transitions and metadata collections are
also canonically ordered; metadata keys are unique within each collection.

## Transition integrity

A transition names distinct existing source and destination sections. The source
must name that exact transition in `transition_after`, and the destination must
name it in `transition_before`. Both endpoints must participate. Unreferenced,
one-sided, extra, reversed, self, unknown-endpoint, and wrong-endpoint transitions
are invalid. Only one transition may claim a directed source/destination slot.
Phase 4.1 does not require section adjacency and does not contain transition text.

## Scoped ownership context

Normal `DraftValidationContext` construction produces a deeply immutable Pydantic
contract. Caller lists, sets, and dictionaries are copied into typed, deterministic
tuples; no caller-owned mutable collection remains reachable. Duplicate
normalized-input, plan, claim, or evidence identities are rejected before lookup
construction.

Each `NormalizedInputDraftScope` owns its exact claims, evidence, and execution-plan
reference/fingerprint pairs. A draft may use only inventory from its selected
`normalized_input_reference`. Global existence in another scope does not confer
ownership or compatibility. Plan reference and fingerprint must match the same
plan in the selected scope.

## Structural metadata

Metadata is semantically unordered and uses unique keys. Allowed keys are:

- `structural_label`
- `structural_category`
- `structural_note_code`
- `schema_extension_identifier`

Keys are lowercase underscore identifiers of at most 64 characters. Values are
NFC-normalized immutable string tokens of at most 80 characters and cannot contain
whitespace. Arbitrary dictionaries, nested values, prose, prompt text, provider or
model settings, generated copy, timestamps, runtime state, database/network data,
and persistence handles are outside the contract.

## Validation and copied models

Normal construction produces immutable typed contracts. In contrast, Pydantic's
unvalidated `model_copy()` may carry caller-injected runtime representations that
do not satisfy those field types.

Every explicit validation call therefore reconstructs a fresh authoritative,
immutable semantic snapshot of both the complete draft aggregate and its context.
All seal, transition, duplicate, linkage, lookup, and ownership checks use only
those rebuilt objects. The validator neither mutates nor freezes the caller's copied
object, and it retains no reconstructed object or mutable lookup between calls.
Later caller mutation can affect only a later validation call, which performs a new
reconstruction.

Malformed copied structures produce stable reconstruction findings and stop unsafe
semantic or ownership validation; they do not expose raw conversion exceptions.
Valid mutable representations such as lists or mapping-shaped nested records may be
accepted only through their equivalent immutable reconstructed snapshot. Therefore
`model_copy()` cannot bypass field, nested-model, vocabulary, type, metadata, or
context constraints even after correct resealing. A fully rebuilt, semantically
valid mutation remains valid. Issues have stable codes and deterministic ordering.

## Deferred responsibilities

Later phases may consume a validated structure. Text generation, provider
execution, prompt construction, claim binding, evidence selection, coverage and
quality analysis, rendering, readiness, revision, persistence, and publication are
not part of Phase 4.1 and may not mutate these contracts.
