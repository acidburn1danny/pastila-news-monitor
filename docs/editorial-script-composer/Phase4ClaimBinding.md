# Phase 4.2 — Deterministic Claim Binding

## Purpose and boundary

Phase 4.2 binds normalized-input-owned claim references to frozen Phase 4.1 draft
sections. It records assignment, required/optional classification, structural role,
and explicit order. It does not generate or rewrite text, select or bind evidence,
score claims, assess truth or support, calculate aggregate coverage, determine
readiness, invoke providers, persist state, or perform runtime orchestration.

Phases 1 through 4.1 and Module 2.8 remain frozen.

## Public models

`ClaimBinding` represents one assignment and contains its identity, fingerprint,
caller-facing binding reference, draft and section references, claim reference,
requirement, structural role, and ordinal. It contains no metadata because Phase
4.2 has no necessary metadata semantics beyond those explicit fields.

`SectionClaimBindingSet` groups the emitted bindings for one section. Its fields
are identity, fingerprint, binding-set reference, draft reference, section
reference, and ordered bindings. A binding set is always nonempty.

`DraftClaimBindingPlan` binds one exact draft identity and fingerprint to its
normalized input and ordered section binding sets. It deliberately has no status.

`ClaimBindingValidationContext` contains one or more frozen `DraftStructure`
objects and the existing Phase 4.1 `DraftValidationContext`. A dedicated wrapper is
required to resolve complete drafts; claim ownership remains delegated to the
existing normalized-input scopes rather than duplicated.

The public validator is `validate_draft_claim_binding_plan`. Identity helpers for
the three artifacts and `claim_binding_semantic_fingerprint` are public so callers
can seal immutable artifacts. Reconstruction and invariant helpers remain private.

## Requirement vocabulary

`ClaimBindingRequirement` is closed: `required` and `optional`. A binding must use
`required` exactly when its claim occurs in the section's
`required_claim_references`; it must use `optional` exactly when it occurs in
`optional_claim_references`.

Every required claim must have exactly one binding. Optional claims may have zero
or one. Undeclared claims cannot be bound. A claim cannot occur twice in one
section.

## Role vocabulary

- `section_anchor`: the claim establishes the section's primary factual anchor.
- `section_context`: the claim supplies structural context for other assignments.
- `section_development`: the claim advances the section after its anchor/context.
- `section_counterpoint`: the claim occupies an explicitly contrasting position.
- `section_conclusion`: the claim supplies the section's concluding factual point.

Extensions use `custom:<slug>`, where the slug is lowercase ASCII alphanumeric
segments separated by single hyphens. Whitespace, Unicode, slash, underscore,
uppercase, empty segments, leading/trailing hyphens, and provider/execution prose
are invalid. Role validation is structural; Phase 4.2 does not rank suitability.

## Ordinals and ordering

Binding ordinals start at zero, are strict non-negative integers, are unique and
contiguous, and must match tuple order. They—not lexical claim order or insertion
order—define meaningful order.

Section binding sets follow `DraftStructure.section_references`. Only sections
with emitted bindings appear. A section with required claims must appear. A
section containing only optional claims may be absent when all are omitted.

## Empty representation

The sole canonical representation for a draft with no emitted bindings is an empty
`section_binding_sets` tuple. Explicit empty section binding sets are invalid. Thus
a no-claim draft and an optional-only draft with all optionals omitted use the same
empty plan shape; a draft with any required claim cannot use it.

## Ownership and linkage

The plan draft reference resolves to exactly one context draft, and its stored
fingerprint and normalized-input reference must match that draft. Each binding set
and binding must reference that same draft. Each section must resolve inside it.

Claims are checked only against the draft's selected normalized-input scope in the
frozen `DraftValidationContext`. Global existence in another scope does not confer
ownership. Unknown, foreign, mixed-scope, stale-draft, cross-draft, and cross-section
substitutions are invalid.

A claim may be reused across sections only when every section independently
declares it. Reuse never permits a duplicate inside one section.

## Identity and fingerprint contracts

`ClaimBinding` identity bears its binding reference, draft reference, section
reference, claim reference, requirement, role, and ordinal.

`SectionClaimBindingSet` identity bears its reference, draft and section references,
and ordinally encoded ordered binding semantics. `DraftClaimBindingPlan` identity
bears its plan reference, draft identity and fingerprint, normalized-input
reference, and ordinally encoded ordered binding-set semantics.

Fingerprints include every semantic field except their own fingerprint. Identity
is therefore fingerprint-bearing. Derivation uses the frozen canonical UTF-8
serialization and SHA-256 mechanisms. Ordered collections are encoded with
explicit ordinal keys without changing the frozen global canonical configuration.
There are no timestamps, random values, process state, or object representations.

## Validation, reconstruction, and duplicates

Every explicit validation call rebuilds both the complete plan and context through
their Pydantic contracts. Reconstruction findings stop semantic validation. All
seals, lookups, ownership, linkage, completeness, and ordering checks use only the
fresh immutable reconstructed values. No mutable lookup or snapshot is retained.

This prevents unvalidated `model_copy()` representations from bypassing nested
types, vocabulary, strict scalar types, or context ownership. Valid list or
mapping-shaped representations may normalize through reconstruction; malformed
values produce deterministic controlled findings without raw conversion errors.
Reconstruction diagnostics never expose raw unreconstructed values. A valid,
bounded reference token is NFC-normalized and retained; an invalid, missing,
non-string, multiline, or unbounded plan reference uses the stable contract-level
artifact reference `draft-claim-binding-plan`. Raw object representations, memory
addresses, exception text, and input snapshots never enter public issues. Issue
codes, artifact references, structural paths, and ordering are consequently stable
across repeated calls, processes, and platforms.
The public reconstruction boundary contains every ordinary `Exception` raised by
hostile plan or context serialization and converts it into the existing stable
reconstruction finding. Process-control exceptions (`KeyboardInterrupt`,
`SystemExit`, and `GeneratorExit`) remain outside that boundary and propagate
unchanged.

Duplicate binding references, identities, claims, and ordinals; duplicate binding
set references, identities, and section references; and duplicate context draft
identities are rejected before lookup semantics can overwrite them. Issue ordering
is deterministic and duplicate rejection is independent of input permutation.

## Completeness boundary

Phase 4.2 enforces exact required-reference completeness because that is a direct
referential invariant. It does not calculate percentages, qualitative coverage,
support, evidence sufficiency, section completeness scores, draft eligibility, or
readiness. Those aggregate coverage and integrity responsibilities are deferred to
Phase 4.3.
