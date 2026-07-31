# Phase 6.1 — Provider-Neutral LLM Execution Request Planning

Status: **VERIFIED / FROZEN**

## Purpose and position

Phase 6.1 transforms one validated Phase 5.2 `DraftRenderedPromptPlan` into one
immutable `DraftLLMExecutionPlan`:

`Phase 5.2 canonical rendering → Phase 6.1 execution planning → future Phase 6.2`

It describes what is eligible for later execution. It does not select a provider,
construct an HTTP payload, execute a model, or process generated output.

## Public contracts

- `LLMExecutionMessage` preserves one rendered message's role, text, ordinal, and
  complete message/section/plan lineage.
- `LLMExecutionRequest` preserves one rendered section as one ordered execution
  unit and carries draft lineage and its authoritative tuple position.
- `DraftLLMExecutionPlan` preserves rendered-plan, Phase 5.1 request-plan, draft,
  and normalized-input lineage.
- `LLMExecutionValidationContext` contains immutable authoritative Phase 5.2
  snapshots and their frozen validation context.

All contracts are strict, frozen, Unicode-normalized domain models. Ordered
collections are tuples. They contain no timestamps, runtime state, arbitrary
metadata, provider configuration, or generated language.

## Projection and ordering

The projection is exactly one-to-one:

```text
DraftRenderedPromptPlan → DraftLLMExecutionPlan
RenderedPromptSection  → LLMExecutionRequest
RenderedPromptMessage  → LLMExecutionMessage
```

Counts and tuple order are preserved. Roles, text, and ordinals are copied
verbatim from authoritative Phase 5.2 artifacts. No filtering, merging, splitting,
sorting, repair, role mapping, or content rewriting occurs.

The canonical empty plan uses `execution_requests == ()`. A hypothetical valid
empty rendered section maps to `execution_messages == ()`; frozen Phase 5.2
currently requires rendered sections to contain messages.

## Canonical references and seals

Shared private derivations produce:

- `llm-execution-plan:<rendered-plan-identity>`
- `llm-execution-request:<rendered-section-identity>`
- `llm-execution-message:<rendered-message-identity>`

Every semantic field participates in deterministic identity derivation. Semantic
fingerprints additionally include the identity and exclude only the fingerprint
field itself. Canonical repository serialization provides NFC normalization,
UTF-8 encoding, stable tuple order, and SHA-256 hashing.

Frozen Phase 5.2 exposes only `normalized_input_reference`. It is the sole
authoritative normalized-input lineage value supplied to Phase 6.1. Phase 6.1
derives the compatibility fields `normalized_input_identity` and
`normalized_input_fingerprint` deterministically and exclusively from that
reference, using a Phase 6.1-owned lineage seed. These values are local
execution-planning lineage seals: they are not upstream-issued identities, are
not lookup authority, do not assert that an upstream normalized-input artifact
exists, and must never be used to resolve one.

The local identity namespace is explicitly:

`scout:llm-execution-normalized-input-lineage:<sha256>`

This namespace distinguishes the seal from every Phase 4.x, Phase 5.1, Phase 5.2,
and normalized-input artifact identity.

## Authority and reconstruction

The builder and validator reconstruct fresh immutable inputs. Before projection,
the builder invokes `validate_draft_rendered_prompt_plan`; Phase 6.1 does not
duplicate Phase 5.2 validation authority. Submitted execution fields are never
trusted as authority: expected execution state is rebuilt from the validated
rendered plan.

Ordinary reconstruction failures become bounded deterministic domain findings.
`KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` propagate unchanged.

## Validation, duplicates, and diagnostics

Validation covers canonical references, identities, fingerprints, all upstream
lineage, exact role and text, ordinals, completeness, ordering, and canonical
empty representations.

Duplicate dimensions are inspected before lookup construction, including request
and message references, identities, upstream references and identities, and
ordinals. Malformed tuples are not sorted or repaired before validation.

One centralized diagnostic-safe reference policy protects artifact and related
references. Credentials, query strings, fragments, paths, controls, multiline or
oversized strings, exception-like text, memory-address-like values, environment
assignments, and unsafe Unicode are replaced by stable bounded placeholders.
Duplicate detection still operates on original semantic values.

## Provider boundary and exclusions

Phase 6.1 contains no provider, SDK, endpoint, credential, model name, inference
parameter, token limit, retry policy, HTTP request, streaming behavior, tool call,
response DTO, usage data, billing data, persistence, generated output, or editorial
interpretation. Provider mapping and execution belong to a future phase.
