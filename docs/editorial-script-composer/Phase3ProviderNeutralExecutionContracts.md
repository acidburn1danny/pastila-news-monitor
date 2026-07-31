# Module 2.9 Phase 3 Provider-neutral Execution Contracts

## Purpose and boundary

Phase 3 describes future editorial generation execution as immutable values. It
does not execute a provider, select an adapter, assemble a prompt, generate
language, assemble a draft, derive editorial readiness, revise content, render,
persist, schedule, or orchestrate work. Phase 1 domain semantics and Phase 2
compatibility semantics remain frozen.

## Contract inventory

`GenerationExecutionIntent` binds one compatible normalized Phase 2 input to a
controlled operation, output scope, targets, profile, policy, authority,
instruction, constraint, and evidence references. `GenerationExecutionPlan`
contains ordered `GenerationExecutionUnit` values, dependency declarations,
expected output bindings, capability sets, and embedded retry and failure
policies. These are plans, not mutable jobs.

`GenerationCapabilityRequirement` and `GenerationCapabilitySet` describe
provider-neutral requirements. The closed vocabulary includes structured and
constrained output, context, instruction following, citation preservation,
tool-free and multilingual generation, revision, and partial-regeneration
support. `custom:<slug>` is the only extension form. No matching or ranking is
performed.

`GenerationExecutionRequest` is the future Phase 8 adapter boundary. It contains
no prompt, provider, model, endpoint, credentials, sampling parameters, HTTP
fields, or SDK values. It links exactly one plan unit to its profile, policy,
targets, capabilities, output binding, and policies.

## Lifecycle and outcomes

`GenerationExecutionState` is vocabulary only. Immutable
`GenerationExecutionStateObservation` values use sequence numbers and prior
fingerprints rather than clocks or mutable state transitions.

Lifecycle payloads use a closed matrix. Planned, eligible, blocked, submitted,
accepted, and running observations carry no terminal payload. Success and
partial success require the corresponding outcome and forbid failure or
supersession. Failure requires a failure outcome or reference and forbids
supersession. Cancellation has an empty terminal payload. Supersession carries
only a non-self superseding execution reference. Sequence zero has no previous
fingerprint; later observations require one, and contextual validation confirms
the immediately preceding observation from the same request.

`GenerationExecutionOutcome` discriminates successful, partial, and failed
shapes. It retains only artifact and binding references, stable failure
classifications and codes, bounded diagnostic issues, retry eligibility, and a
provider-neutral usage summary. Raw provider responses, exceptions, and stack
traces are prohibited.

Failure type and failure code are paired metadata: both are absent or both are
present. Success forbids the pair. With request context, applied profile and
policy fingerprints must match the request, and affected targets are an exact
subset of the request targets.

## Retry, failure, and output policy

`GenerationRetryPolicy` declares attempt limits, disjoint retryable and
non-retryable classifications, retry scope, replacement permission,
preservation references, and semantic backoff classification. It performs no
sleep or scheduling. `GenerationFailurePolicy` classifies required and optional
bindings and declares propagation, dependency, supersession, cancellation, and
retry linkage without executing any policy.

With plan context, every outcome failure type must be explicitly classified by
the retry policy. Retryable failures require `retry_eligible=true`,
non-retryable failures require false, and unclassified failures are invalid.

`GenerationOutputBinding` describes the required artifact type, target, scope,
unit, cardinality, and ordering expectation. It does not assemble outputs into
a `ScriptDraft`; that responsibility starts in Phase 4.

Binding identities deliberately exclude the owning unit back-reference. Unit
identities include the expected binding identity, while plan identities project
binding ownership through stable unit ordinals. Required and optional binding
classifications are canonical unique sets in the plan identity seed. This
breaks the plan/unit/binding identity cycle without discarding semantics.

## Validation and deterministic graphs

Public explicit validators verify semantic fingerprints, deterministic
identities, normalized-input/profile/policy linkage, reference uniqueness,
request-plan-unit linkage, intent target/evidence/revision linkage, output
binding ownership and artifact compatibility, policies, lifecycle shapes, and
outcomes. Parent intent validation guarantees canonical non-self references;
resolution is additionally enforced only when an immutable parent collection
is supplied. Constructor and explicit validation share pure invariants, so a
`model_copy()` followed by correct resealing cannot bypass structural checks.

Contextual unit validation requires operation equality with the intent. Unit
instruction, constraint, authority, and evidence references are explicit
subsets of the applicable intent collections and must independently resolve in
the normalized Phase 2 input. Source input references name either the normalized
generation bundle or a composition bundle/plan owning one of the unit targets.

The intent policy reference and fingerprint select exactly one authoritative
policy. Instructions and constraints are resolved only from that policy, never
from a global multi-policy union. Intent and unit authorities must be explicitly
permitted by the selected policy and satisfy the authority levels of selected
instructions. Policy-derived targets likewise come only from selected-policy
members; direct composition and revision targets retain their existing rules.
Unit validation enforces these ownership rules independently, and eligibility
blocks cross-policy substitutions.

For example, a bundle may contain policies A and B deterministically. An intent
selecting A may use A's members even if B is ordered first in the bundle. It may
not use a B-only instruction, constraint, authority, or target merely because B
is present in the same normalized input.

Plan policy references equal the canonical union of selected policies from the
intent and units. Plan authority and evidence references likewise equal the
canonical union of intent and unit projections. Missing and unrelated aggregate
references are both invalid.

Plan graph validation reports duplicate identities and ordinals, missing or
self dependencies, and canonical cycles in deterministic order. It neither
schedules nor executes the graph. Ordered execution units retain their declared
ordinal order; unordered references are canonicalized. Unit dependency
references are authoritative; typed dependency declarations are their public,
auditable mirror and must contain exactly the same directed edges.

## Identity and serialization

All first-class artifacts use the frozen canonical UTF-8 serializer and
semantic SHA-256 implementation. Identities use the frozen
`scout:<artifact-type>:<sha256>` derivation. Seeds exclude only self identity
and fingerprint fields or structural back-references necessary to avoid cyclic
identity derivation. They contain no timestamps, UUIDs, randomness, object
hashes, environment values, or runtime resources.

## Structural eligibility

`GenerationExecutionEligibility` reports whether a plan is structurally
eligible for a future executor. It carries blocking structural/input issues,
required capabilities, unresolved authority conflicts, and eligible or blocked
units. Optional intent, request, and normalized-input context lets the same
derivation include all available Phase 3 linkage defects. It is explicitly not
publication, factual, editorial, draft, or script readiness.
Lifecycle observations and outcomes are not eligibility inputs; their separate
validators remain authoritative without introducing runtime state.

## Examples

A valid two-unit plan uses unique contiguous ordinals, makes the second unit
depend on the first, resolves both output bindings and capability sets, and
links one retry and failure policy. Invalid structures include missing unit
dependencies, dependency cycles, repeated references, mixed success/failure
outcomes, unresolved required bindings, or a request whose unit fingerprint no
longer matches the plan.

## Public API

The package exposes typed validators for intent, units, plans, requests,
outcomes, policies, and observations; a strict plan construction boundary; a
strict plan requirement; and structural eligibility derivation. Internal graph
and invariant helpers remain private.
