# Phase 6.2 — Deterministic Provider Request Mapping

Status: **Implemented — awaiting independent verification**

## Purpose and architectural position

Phase 6.2 transforms a validated Phase 6.1 `DraftLLMExecutionPlan` into an
immutable typed provider-request plan. The authority path remains:

`Phase 5.2 rendering → Phase 6.1 execution planning → Phase 6.2 provider mapping`

Phase 6.1 is frozen authority. Phase 6.2 validates that authority through the
public Phase 6.1 validator, reconstructs expected mappings from it, and never
treats submitted provider fields as authority.

Phase 6.2 maps requests but does not execute them.

## Contracts

The common layer provides `ProviderRequestPlanDescriptor`,
`DraftProviderRequestPlan`, and `ProviderMappingValidationContext`. The generic
plan contains a typed `openai_request_plan`; it never stores `Any`, an arbitrary
dictionary, an SDK object, or a serialized HTTP body.

The first and only supported descriptor is:

```text
provider: openai
mapping_contract_version: phase-6.2-openai-v1
provider_descriptor_reference:
  provider-mapping-descriptor:openai:phase-6.2-openai-v1
```

The OpenAI mapping layer provides `OpenAIProviderMessage`,
`OpenAIProviderRequest`, and `OpenAIProviderRequestPlan`. These DTOs contain
structural request content and lineage only. They contain no model, sampling,
endpoint, authentication, retry, timeout, tool, response, usage, or billing
configuration.

## Exact projection and role mapping

Projection is one-to-one and tuple order is authoritative:

```text
DraftLLMExecutionPlan → OpenAIProviderRequestPlan
LLMExecutionRequest  → OpenAIProviderRequest
LLMExecutionMessage  → OpenAIProviderMessage
```

The centralized closed role mapping is:

```text
instruction → developer
context     → user
generation  → user
```

`content` is copied exactly from authoritative Phase 6.1 `execution_text`.
Nothing is trimmed, escaped, concatenated, labelled, templated, or rewritten.

## Canonical references and seals

Private shared derivations produce:

- `provider-mapping-descriptor:<provider>:<mapping-contract-version>`
- `provider-request-plan:<provider>:<execution-plan-identity>`
- `openai-request-plan:<execution-plan-identity>`
- `openai-request:<execution-request-identity>`
- `openai-message:<execution-message-identity>`

All non-seal semantic fields participate in repository-standard deterministic
identity derivation. Fingerprints include identity and all remaining semantic
fields, excluding only the fingerprint itself. Nested tuple position and order
are explicit, and canonical UTF-8 serialization plus SHA-256 is used throughout.

## Reconstruction and validation

Builders reconstruct submitted plans, descriptors, and contexts on every call,
resolve exactly one authoritative execution plan and descriptor, invoke frozen
Phase 6.1 validation, and create fresh immutable projections. Validators rebuild
the expected mapping from authority and compare the submitted artifact against
it.

Validation covers seals, canonical references, descriptor and execution lineage,
roles, exact content, ordinals, completeness, ordering, duplicates, generic to
concrete linkage, and canonical empty state. Duplicate dimensions are inspected
before lookup construction. Ordering is never repaired.

For an authoritative empty execution plan, the only valid provider projection is
`requests == ()`. A request with `messages == ()` is a supported contract shape
only if frozen Phase 6.1 supplies such an authoritative request; current valid
Phase 5.2/6.1 production input does not make that shape reachable.

Ordinary reconstruction failures become bounded deterministic domain findings.
Process-control exceptions propagate. Diagnostic references are sanitized using
the repository's bounded deterministic policy without changing semantic duplicate
detection.

## Execution boundary and future ownership

This phase has no OpenAI SDK, HTTP client, credentials, environment access,
endpoint, model selection, inference parameters, retry logic, streaming,
responses, generated output, usage accounting, persistence, or caching.

Future providers may add typed adapters and descriptors without changing frozen
Phase 6.1. Phase 6.3 owns any later runtime configuration or execution boundary;
none is implemented here.
