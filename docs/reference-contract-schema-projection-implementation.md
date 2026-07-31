# Part 7G — Invocation-Specific Exact-Reference Schema Projection

## Executive Summary

Part 7G implements the Part 7F decision `C2_DYNAMIC_EXACT_SCHEMA`. Each OpenAI
Controlled Revision request now carries a fresh strict JSON Schema whose component
branches contain only the canonical references authorized by that invocation. DTO
validation, exact authorization, and deterministic reconstruction remain separate,
active trust boundaries. No provider or benchmark request was executed.

## Part 7F Decision

Both Part 7F artifacts were checked before implementation. They select
`C2_DYNAMIC_EXACT_SCHEMA`, conclude `SCHEMA_REMEDIATION_RECOMMENDED`, and recommend
`IMPLEMENT_SELECTED_REFERENCE_CONTRACT`. They do not authorize weaker authorization,
reconstruction changes, aliases, normalization, or provider-output repair.

## Repository Inspection

The production path is:

1. `ControlledRevisionTarget` validates target identity and canonical ordering.
2. `ControlledRevisionRequest.revision_targets` is the immutable authorized target set.
3. `OpenAIControlledRevisionProjector` builds the provider input and Responses payload.
4. `OpenAIResponsesPayload.request_arguments()` serializes the strict schema unchanged.
5. `OpenAIControlledRevisionProviderOutput` validates the response DTO.
6. `OpenAIControlledRevisionReconstructor` independently compares returned references
   with the invocation targets, then performs deterministic reconstruction.

Benchmark-only instrumentation remains under `scripts/` and its tests. It was not used
as a reference source and was not modified.

## Previous Production Flow

The provider received the static DTO schema. Story and transition references were
constrained only by broad patterns, while opening, closing, and CTA used fixed values.
The prompt requested exact references and downstream authorization enforced them, but
the generation-time schema did not express invocation-specific identity.

## Implemented Production Flow

`ControlledRevisionTarget.canonical_reference` is the sole formatter for a validated
target. The request projector passes the immutable canonical target tuple to
`projected_controlled_revision_schema_json()`. That pure function deep-loads a new base
DTO schema, selects the matching DTO branch for every target, replaces only the
reference constraint with an exact `const`, and binds array cardinality to the target
count. The request payload contains the canonical serialized result and exposes its
SHA-256 fingerprint for safe diagnostics.

## Source-of-Truth Analysis

The source of truth remains `ControlledRevisionRequest.revision_targets`. Projection
does not inspect stories, prompt text, fixtures, provider output, or a separate schema
registry. Provider input, schema projection, and final authorization all consume the
same target objects and their canonical reference property. Authorization is not
derived from the schema.

## Reference-Field Inventory

| DTO path | Schema path | Cardinality | Required | Previous behavior | Projected behavior | Authorized source | Downstream behavior |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `revised_components[].component_reference` on text DTO | each opening/transition/closing branch | one per object | yes | opening/closing const; transition pattern | invocation-specific const | request target | exact set comparison |
| `revised_components[].component_reference` on story DTO | story branch | one per object | yes | broad story pattern | invocation-specific const | request target | exact set comparison |
| `revised_components[].component_reference` on CTA DTO | CTA branch | one per object | yes | static const | invocation-specific const | request target | exact set comparison |

The response union has five target categories across three DTO variants. All three
structural reference-field variants are projected. No optional structural-reference
location exists.

## Projection Design

Projection is deterministic, stateless, and mutation-free. It rejects an empty tuple,
non-canonical ordering, duplicate canonical values, unsupported targets, and internal
projection mismatches. Empty targets are already invalid at the request contract
(`min_length=1`); the projector repeats the invariant fail-closed. A single target uses
the same branch structure as multiple targets.

The base DTO schema and all non-reference constraints are retained. Only `$defs` are
specialized into one complete DTO branch per authorized target, and array `minItems`
and `maxItems` are set to the authorized count. DTO duplicate validation and exact set
authorization still prevent omission or repetition.

## Provider Adapter Integration

The existing OpenAI strict-schema transport supports `const`, `$ref`, `anyOf`, required
properties, and fixed array bounds. Serialization parses the immutable canonical JSON
document into a fresh SDK argument object without rewriting exact values. The schema
name stays stable because the complete schema travels with every request; effective
schema identity is available through `schema_fingerprint`.

The prompt was not changed. It already truthfully describes the now schema-enforced
contract. Provider-neutral domain models contain no OpenAI schema concepts.

## Authorization and Reconstruction Preservation

Final exact authorization remains in the reconstructor and is always executed after
DTO validation. Unknown, unauthorized, cross-invocation, missing, duplicate, changed-
case, whitespace-mutated, and delimiter-mutated values remain fail-closed. Valid
authorized DTOs reconstruct through the existing immutable domain path. The only
shared refactor was replacing duplicate formatting code with the canonical target
property; reference formats and behavior are unchanged.

## Failure Behavior

Projection raises explicit `ValueError` failures before transport. There is no broad-
schema fallback, prompt-only fallback, stale-schema reuse, aliasing, normalization,
repair, retry, or fallback-policy change.

## Concurrency and Security

Every projection starts from a newly decoded base schema and uses deep copies of the
selected DTO definitions. Sequential and concurrent tests prove isolation and base-
schema immutability. References are assigned as structured JSON values, preventing
schema injection through string interpolation. No global mutable schema state, cross-
invocation leakage, privilege expansion, or authorization bypass was introduced.

## Performance and Schema Size

The contract permits at most 50 targets. An offline 50-story projection produced a
41,601-byte UTF-8 schema in approximately 2.119 ms on the validation workstation. This
is bounded and negligible relative to provider latency. No truncation, partitioning,
cache, or provider call was used.

## Testing Strategy

Focused tests cover single and multiple values, all structural categories, exact
canonical strings, empty/duplicate/non-canonical input rejection, deterministic
serialization, base-constraint preservation, sequential and concurrent isolation, DTO
compatibility, real request assembly, adapter serialization, unchanged reconstruction,
final authorization, and maximum contract size. Existing Controlled Revision,
authorization, reconstruction, runtime, architecture, and benchmark-compatibility
tests remain authoritative regression coverage.

## Files Modified

- `revision/contracts.py`: central canonical-reference property (production behavior
  is unchanged).
- `openai/models.py`: pure projection and effective-schema fingerprint (production).
- `openai/projector.py`: invocation-specific request schema assembly (production).
- `openai/reconstructor.py`: consumes the shared canonical-reference property
  (production refactor; authorization/reconstruction semantics unchanged).
- `openai/__init__.py`: exports the projection entrypoint (production API).
- `tests/test_invocation_specific_reference_schema.py`: focused offline coverage.
- This report and its structured artifact: implementation evidence.

## Regression Results

The final quality-gate results are recorded in the structured artifact and completion
report. No provider request, benchmark execution, or replay occurred. The benchmark
corpus, prior artifacts, and history remain unchanged.

## Known Limitations and Rollback

Schema enforcement improves generation-time conformance but does not prove provider
effectiveness; Part 7C.2 must measure that separately. JSON Schema alone does not make
array members unique, so the unchanged DTO uniqueness validator and exact authorization
remain essential. Rollback is code-only: no data, registry, authorization,
reconstruction, corpus, or history migration exists.

## Architecture Compliance

The implementation follows C2: one immutable authorization source, pure projection,
exact finite provider constraints, unchanged final authorization, deterministic
reconstruction, provider-bound serialization, no repair, and no permissive fallback.

## Root Conclusion

`EXACT_REFERENCE_SCHEMA_PROJECTION_IMPLEMENTED`

## Recommended Next Milestone

Part 7C.2 — Controlled Provider Quality Baseline After Reference Contract
Remediation, using the unchanged corpus and frozen execution configuration.
