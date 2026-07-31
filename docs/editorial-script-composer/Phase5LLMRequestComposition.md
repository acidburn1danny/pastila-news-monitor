# Phase 5.1 — Deterministic LLM Request Composition

## Purpose and position

Phase 5.1 transforms one validated Phase 4.3 `DraftSectionCompositionPlan` into a
self-contained immutable `DraftLLMRequestPlan`:

`Section Composition → Semantic Request Composition → future Prompt Rendering`

It finalizes semantic request structure only. It renders no prompt, invokes no
provider, selects no model, and performs no inference.

## Public contracts

`LLMRequestClaim` projects one `ComposedClaim`. Its self-contained semantic payload
is exactly the payload frozen Phase 4.3 exposes: claim reference, requirement,
role, and ordinal. It also retains complete composed-claim, section, plan, draft,
and normalized-input lineage.

`LLMRequestSection` projects one nonempty `ComposedSection` and owns the ordered
tuple of request claims plus section and plan lineage. It does not duplicate claim
payload.

`DraftLLMRequestPlan` projects one composition plan and owns ordered request
sections and whole-plan lineage. It does not duplicate section or claim payload.

`LLMRequestValidationContext` contains authoritative Phase 4.3 plans and the
frozen `SectionCompositionValidationContext`; it creates no ownership inventory.

## Construction and self-containment

`build_draft_llm_request_plan` reconstructs and authoritatively validates its Phase
4.3 inputs before projection. It emits exactly one request claim per composed
claim, one request section per composed section, and one request plan per
composition plan. It never filters, merges, splits, invents, repairs, or sorts.

Downstream prompt rendering can inspect all semantic request data directly from
the Phase 5.1 plan. Phase 4.3 remains necessary only as validation authority.

## Constraint ownership

Constraints are enforced structurally rather than repeated as decorative fields.
Claim semantics remain on claims, section completeness and ordering remain on
sections, and whole-plan completeness and ordering remain on the plan.

## Canonical references, ordering, and empty plans

Private shared derivations produce and validate exactly:

- `llm-request-plan:<source-composition-plan-identity>`
- `llm-request-section:<source-composed-section-identity>`
- `llm-request-claim:<source-composed-claim-identity>`

Correctly resealed alternatives, foreign references, URLs, paths, multiline
values, and oversized values are invalid. Unsafe values do not enter diagnostics.

Section and claim tuples preserve authoritative order exactly. The sole empty
representation is `request_sections=()` and corresponds to an empty authoritative
composition plan. Explicit empty or placeholder request sections are invalid.

## Identity, fingerprints, and reconstruction

Public identity functions include every semantic field except identity and
fingerprint. Public fingerprint functions include identity and every other
semantic field except fingerprint. Nested order is explicit. Both mechanisms
reuse canonical NFC-normalized UTF-8 serialization and SHA-256.

Every builder and validator call reconstructs fresh immutable input snapshots.
Ordinary hostile serialization exceptions become bounded deterministic issues.
`KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` propagate unchanged.

Diagnostics contain no exception text, traceback, object representation, memory
address, unsafe URL, filesystem path, or raw caller snapshot.

## Public API and future boundary

Phase 5.1 exports four models, six seal functions, one builder, and one validator.
Reference derivations, reconstruction records, duplicate collectors, diagnostic
helpers, and seal validators remain private.

Phase 5.1 contains no prompt text or templates, provider identifiers or adapters,
model selection, inference parameters, token settings, retries, streaming,
networking, persistence, generated output, or response validation. Prompt
rendering is deferred to Phase 5.2; provider invocation remains a later phase.

## Adversarial freeze coverage

The committed regression suite independently exercises stale and forged seals at
all three artifact levels, every duplicate dimension, section and claim ordering,
foreign and extra claims, malformed authoritative Phase 4.3 inputs, Unicode/NFC
semantics, unsafe diagnostics, and complete diagnostic equality across separate
processes. This expanded coverage changes no production behavior.

Phase 5.1 is implemented but is not independently verified or frozen.
