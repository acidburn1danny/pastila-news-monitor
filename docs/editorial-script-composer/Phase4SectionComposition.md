# Phase 4.3 — Deterministic Section Composition

## Purpose and architectural position

Phase 4.3 materializes a valid Phase 4.2 `DraftClaimBindingPlan` into the final
immutable structural plan before future language generation:

`DraftStructure` → `DraftClaimBindingPlan` → `DraftSectionCompositionPlan`

The phase preserves upstream structure exactly. It does not select, rank, omit,
merge, split, or reinterpret claims or sections, and it generates no language.

## Public contracts

`ComposedClaim` is a one-to-one structural projection of one `ClaimBinding`. It
retains the source binding reference, identity, fingerprint, draft, section,
claim, requirement, role, and ordinal.

`ComposedSection` is a nonempty one-to-one projection of one
`SectionClaimBindingSet`. Its ordered claims correspond exactly to the source
binding tuple.

`DraftSectionCompositionPlan` identifies one source binding plan and preserves its
draft fingerprint, normalized-input lineage, and ordered emitted sections.

`SectionCompositionValidationContext` contains authoritative Phase 4.2 plans and
the frozen `ClaimBindingValidationContext`. It introduces no ownership graph.

## Construction

`build_draft_section_composition_plan` reconstructs the supplied Phase 4.2 plan
and context and validates them authoritatively before materialization. Invalid
upstream inputs raise the repository-standard aggregate `DomainValidationError`.

Artifact references derive deterministically from complete upstream identities.
They contain no timestamps, UUIDs, random values, process identifiers, or memory
locations. One composed claim is emitted per source binding, one composed section
per source binding set, and one composition plan per source binding plan.
The builder and validator share the same canonical derivation functions. During
validation, every caller-facing plan, section, and claim reference is independently
recomputed from authoritative upstream lineage and must match exactly. Correctly
resealed alternative, foreign, URL-shaped, or path-shaped references remain
invalid.

## Ordering and empty representation

Composed sections preserve source binding-set order. Composed claims preserve
source binding order and zero-based contiguous ordinals. Validation never sorts a
malformed ordered artifact into validity.

The sole empty representation is `composed_sections=()`, corresponding to
`section_binding_sets=()`. A `ComposedSection` is always nonempty; explicit empty
sections are invalid.

## Identity and fingerprints

Public identity functions cover every semantic field except identity and
fingerprint. Public fingerprint functions cover identity and every other semantic
field except fingerprint. Nested order is encoded with explicit ordinal keys.

Both reuse canonical NFC-normalized UTF-8 serialization and SHA-256 and are stable
across equivalent reconstructions and Python processes.

## Validation and reconstruction safety

`validate_draft_section_composition_plan` reconstructs the complete plan and
context for every call. Semantic validation uses only fresh immutable snapshots.
It verifies seals, upstream lineage, exact projection, enclosing linkage,
requirement, role, ordinal, ordering, duplicates, and canonical emptiness.

Every ordinary `Exception` raised by hostile serialization or reconstruction
becomes a bounded deterministic issue. Diagnostics contain no exception message,
raw input snapshot, object representation, memory address, traceback, or path.
`KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` propagate unchanged.

No snapshot, lookup, identity, fingerprint, or validation result is cached.

## Public API and non-goals

The phase exports four immutable models, six seal functions, the deterministic
builder, and the validator. Reconstruction results and helpers remain private.

Phase 4.3 implements no text generation, rewriting, summary, transition, rhetoric,
tone, humor, prompt, template, provider, evidence, scoring, readiness, execution,
network, persistence, scheduling, publication, moderation, or rendering behavior.
Those responsibilities remain deferred.
