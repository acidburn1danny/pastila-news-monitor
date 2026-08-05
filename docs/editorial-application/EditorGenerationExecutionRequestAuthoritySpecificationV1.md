# Phase 4.2 — Editor Generation Execution Request Authority Specification V2

Status: **normative specification — implementation-ready**

Baseline: `phase-4.2-editor-operational-execution-r3d-verified` /
`e28aede67ed288589624b16096b75d19eb2d1f4e`

## 1. Scope

The words **MUST**, **MUST NOT**, **SHALL**, and **SHALL NOT** are normative.
This document specifies one additive, stateless, public authority that owns
construction and authoritative reconstruction of
`EditorGenerationExecutionRequestV1` from its existing public semantic inputs.

It performs no provider selection/execution, runtime composition, prompt or
controlled generation, retry, timeout enforcement, cancellation polling,
persistence, serialization, export, CLI, Producer, GUI, cleanup, or I/O.

## 2. Independently inspected frozen architecture

### 2.1 Frozen aggregate request

`pastila_scout.editor_generation_execution_v1.EditorGenerationExecutionRequestV1`
is a frozen, slotted, init-disabled dataclass. Its constructor accepts these
thirteen positional fields in this exact order:

```text
preparation
plan
flow_result
editorial_blueprint
commentary_blueprint
voice_plan
generation_configuration
runtime_options
provider
requested_at
request_reference
cancellation
request_fingerprint
```

It reconstructs exact nested inputs, validates configuration parity and
cross-object lineage, computes a private expected fingerprint, rejects a
mismatching supplied fingerprint, stores the expected value as both public
`request_fingerprint` and private seal, and supports validated copy/deepcopy.

The package exports only `EditorGenerationExecutionRequestV1`. Its
`reconstruct_execution_request`, `_semantics`, `_values`, configuration/lineage
validators and canonical imports are not public.

### 2.2 Exact frozen validation

The request requires:

- exact copied `EditorOperationalPreparationResultV1` and
  `EditorGenerationPlanV1`, with `preparation.plan == plan`;
- exact reconstructed `FlowOptimizationResult`, including exact
  `EditorAgentOutputV1` and `FlowDecisionTrace`;
- exact strict `EditorialBlueprint`, `EpisodeCommentaryBlueprint`,
  `EpisodeVoicePlan`, and `LanguageGenerationConfig`;
- reconstructed `EditorGenerationRuntimeOptionsV1`;
- exact `ProviderChoiceV1`, equal by identity to `runtime_options.provider`;
- exact aware `datetime`;
- exact nonempty stripped request reference of at most 120 characters;
- exact reconstructed `CancellationTokenV2`;
- generation configuration equal to runtime options for provider, model,
  model revision, type-tagged temperature/top-p/timeout, token limit, seed,
  structured-output mode, and empty stop sequences; and
- flow output validated against plan source/profile/context, a present episode
  proposal, blueprint report lineage, exact flow order, and event membership.

### 2.3 Existing fingerprints are different authorities

`EditorRequestFingerprintAuthorityV1` owns the fingerprint of
`EditorGenerationApplicationRequestV1`: provider, prompt, reference, timestamp,
runtime options, output schema and cancellation. It does not accept preparation,
plan, flow, blueprints, voice, or `LanguageGenerationConfig` and cannot produce
the aggregate execution-request fingerprint.

Application-provider, runtime, schema, Provider V2 request/envelope, and
operational-result fingerprints likewise bind different contracts. None is a
substitute.

## 3. Reproduced public-authority blocker

There is no production construction call site for the frozen aggregate request.
The only external construction found is test code, which imports a canonical
helper and duplicates the private `_semantics` projection. A public caller
currently must do at least one prohibited thing:

1. supply fingerprint text whose authority is outside the frozen constructor;
2. import underscore-private `_semantics` or reconstruction helpers;
3. duplicate the private payload/fingerprint algorithm; or
4. modify a frozen package to expose construction.

The missing public operation is:

```text
the twelve authoritative semantic fields
    -> authority-owned exact fingerprint
    -> frozen constructor
    -> validated EditorGenerationExecutionRequestV1
```

The blocker is therefore reproduced and this additive authority is necessary.

## 4. Existing, missing, and excluded

Existing and frozen:

- all deterministic preparation/artifact contracts;
- `LanguageGenerationConfig`, runtime options, provider, timestamp/reference,
  cancellation and timeout authorities;
- the aggregate request, its private semantic algorithm and validation;
- lower application/runtime/provider fingerprint authorities; and
- Revision 3D execution.

Missing and specified here:

- one public aggregate semantic-input boundary;
- singular public ownership of aggregate fingerprint creation;
- construction without a caller fingerprint; and
- public authoritative reconstruction/parity validation.

Excluded: Phase 4.3 implementation, result serialization, filesystem export,
CLI, Producer, persistence, provider/runtime execution and composition.

## 5. Architectural decision and singular ownership

The exact public authority is:

```python
EditorGenerationExecutionRequestAuthorityV1
```

Its sole transformation is:

```text
validated semantic inputs
  -> exact compatibility projection
  -> one SHA-256 fingerprint
  -> frozen request construction
  -> authoritative reconstruction/parity check
  -> validated request
```

The authority accepts no injected dependency and retains no input or cache. It
does not expose its canonical payload or hash helper.

The new package contains one necessary byte-compatible implementation of the
frozen private projection. This is not an uncontrolled second public authority:

- the frozen constructor remains the validation/parity oracle;
- the new class becomes the sole public construction owner;
- helpers are private to the new package;
- callers and future Phase 4.3 never calculate fingerprints; and
- no other package/test may duplicate the projection.

This independent implementation is chosen over a lower primitive because
modifying a frozen package is prohibited, and exposing a general canonical
primitive would not by itself expose the aggregate semantic field ownership.

## 6. Additive package and dependency direction

Revision 2 creates exactly:

```text
src/pastila_scout/editor_generation_execution_request_authority_v1/
    __init__.py
    authority.py
    canonical.py
    errors.py
tests/test_editor_generation_execution_request_authority_v1.py
```

`canonical.py` is package-private by API and owns only byte compatibility for
this aggregate. The package imports public symbols from:

- `pastila_scout.contracts.editor_output`;
- public deterministic Editor artifact modules;
- `pastila_scout.editor.generation.models`;
- `pastila_scout.editor_generation_authority_v1`;
- `pastila_scout.editor_generation_execution_v1`;
- `pastila_scout.editor_operational_v1`;
- `pastila_scout.provider_execution_v2`; and
- `pastila_scout.provider_selection_v1`.

It imports no underscore-prefixed name and no private module helper. Frozen
packages never import it. Future `editor_application_v1` depends only on its
public class. There is no cycle, registry, lookup, discovery or locator.

## 7. Exact semantic inputs

`construct` accepts the twelve fields preceding `request_fingerprint`, with
these exact types and authorities:

| Parameter | Exact type | Authority and reconstruction |
|---|---|---|
| `preparation` | `EditorOperationalPreparationResultV1` | exact copy; must be successful and sealed |
| `plan` | `EditorGenerationPlanV1` | exact copy; must equal preparation plan |
| `flow_result` | `FlowOptimizationResult` | exact type; strict output/trace reconstruction |
| `editorial_blueprint` | `EditorialBlueprint` | exact strict Pydantic reconstruction |
| `commentary_blueprint` | `EpisodeCommentaryBlueprint` | exact strict Pydantic reconstruction |
| `voice_plan` | `EpisodeVoicePlan` | exact strict Pydantic reconstruction |
| `generation_configuration` | `LanguageGenerationConfig` | exact strict Pydantic reconstruction |
| `runtime_options` | `EditorGenerationRuntimeOptionsV1` | public copy/reconstruction behavior |
| `provider` | `ProviderChoiceV1` | exact enum; same member as options provider |
| `requested_at` | `datetime` | exact aware datetime; caller-owned clock value |
| `request_reference` | `str` | exact safe frozen constraint |
| `cancellation` | `CancellationTokenV2` | exact strict reconstruction |

Nothing is omitted merely because another object also contains it: these are
the exact independent fields of the frozen request, and the frozen constructor
cross-validates their duplicated lineage/configuration authority.

Ordering of flow output, blueprints, voice and nested tuples is preserved.
Copied-invalid values, subclasses, foreign identities, stale lineage,
substitution, reordered artifacts, configuration mismatch and provider mismatch
are rejected before fingerprint publication.

## 8. Caller-fingerprint prohibition

Neither public method accepts `request_fingerprint`, digest, canonical payload,
serialized request bytes, hash callback, override, salt, algorithm, or trusted
identity text. There is no optional/variadic escape path. A caller may inspect
the public fingerprint only after successful construction.

## 9. Exact frozen canonical semantic projection

After exact reconstruction, the authority constructs this mapping, with these
exact key spellings:

```python
{
    "preparation": canonical_value(preparation),
    "plan": canonical_value(plan),
    "flow_result": canonical_value(flow_result),
    "editorial_blueprint": canonical_value(editorial_blueprint),
    "commentary_blueprint": canonical_value(commentary_blueprint),
    "voice_plan": canonical_value(voice_plan),
    "generation_configuration": canonical_value(generation_configuration),
    "runtime_options": {
        "provider": runtime_options.provider.value,
        "model_identifier": runtime_options.model_identifier,
        "model_revision": runtime_options.model_revision,
        "temperature": tagged_number(runtime_options.temperature),
        "top_p": tagged_number(runtime_options.top_p),
        "max_output_tokens": runtime_options.max_output_tokens,
        "seed": runtime_options.seed,
        "stop_sequences": runtime_options.stop_sequences,
        "structured_output_mode": runtime_options.structured_output_mode,
        "timeout_seconds": tagged_number(
            runtime_options.timeout_policy.timeout_seconds
        ),
    },
    "provider": provider.value,
    "requested_at": requested_at,
    "request_reference": request_reference,
    "cancellation_requested": cancellation.cancellation_requested,
}
```

Mapping insertion order is shown for review; JSON keys are sorted, so it does
not affect bytes. Nested tuple order is semantic.

### 9.1 `canonical_value`

The private compatibility implementation exactly mirrors frozen behavior:

1. `None`, exact bool and exact int remain unchanged.
2. Exact strings normalize to Unicode NFC.
3. Exact finite floats remain floats; nonfinite values fail.
4. Exact aware datetimes convert to UTC, six fractional digits, terminal `Z`.
5. Enum instances recurse through `.value`.
6. Exact tuple/list becomes an ordered JSON array.
7. Exact dict requires exact string keys and recursively canonicalizes keys and
   values.
8. Pydantic models enter through `model_dump(mode="python", warnings=False)`.
9. Non-class dataclass instances enter declared field order, excluding names
   beginning `_`, using `object.__getattribute__`.
10. Every other value fails.

`tagged_number` yields exactly `{"type":"int","value":value}` for exact int
and `{"type":"float","value":value}` for finite exact float. Bool fails.

The payload is encoded by:

```python
json.dumps(
    canonical_value(payload),
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

The fingerprint is lowercase SHA-256 hexadecimal with no prefix.

## 10. Parity authority

For every successful call:

```text
authority fingerprint
== fingerprint accepted and stored by frozen constructor
== fingerprint recomputed during authority reconstruction
```

The `construct` method calculates once, calls the frozen constructor once with
that value, then invokes the request's public `copy.copy` reconstruction once.
It does not call the authority's public `reconstruct` method and therefore does
not perform a second authority calculation. Successful frozen construction and
public copy are the parity oracle; mismatched bytes cannot pass them.

Parity tests cover nominal inputs, canonically equivalent/non-equivalent
Unicode, timezone-equivalent/non-equivalent timestamps, tagged int/float/bool
distinctions, tuple order, every nested artifact, provider/model/options,
timeout, cancellation and reference. Each semantic field is mutated
individually. Tests compare authority outputs and frozen acceptance; they do not
contain a second payload builder. A small fixed vector may be committed only if
its digest is independently reviewed and never used as production authority.

## 11. Exact public API and signatures

Exact ordered API:

```python
__all__ = (
    "EditorGenerationExecutionRequestAuthorityError",
    "EditorGenerationExecutionRequestAuthorityV1",
)
```

The authority constructor is exactly `() -> None`.

```python
def construct(
    self,
    *,
    preparation: EditorOperationalPreparationResultV1,
    plan: EditorGenerationPlanV1,
    flow_result: FlowOptimizationResult,
    editorial_blueprint: EditorialBlueprint,
    commentary_blueprint: EpisodeCommentaryBlueprint,
    voice_plan: EpisodeVoicePlan,
    generation_configuration: LanguageGenerationConfig,
    runtime_options: EditorGenerationRuntimeOptionsV1,
    provider: ProviderChoiceV1,
    requested_at: datetime,
    request_reference: str,
    cancellation: CancellationTokenV2,
) -> EditorGenerationExecutionRequestV1: ...

def reconstruct(
    self,
    *,
    request: EditorGenerationExecutionRequestV1,
) -> EditorGenerationExecutionRequestV1: ...
```

There are no defaults, positional semantic arguments, overloads, `*args`,
`**kwargs`, fingerprint parameter or redundant public method.

## 12. Exact construction sequence

1. require the authority's exact retained valid type and exact semantic input
   types;
2. reconstruct each of the twelve semantic inputs at its distinct boundary;
3. validate generation/runtime/provider configuration parity;
4. validate cross-object lineage and ordering;
5. build the section 9 canonical semantic projection exactly once;
6. calculate the authority fingerprint exactly once;
7. call the frozen `EditorGenerationExecutionRequestV1` constructor exactly
   once;
8. invoke `copy.copy(completed_request)` exactly once as the frozen public
   authoritative reconstruction operation;
9. require exact reconstructed request type and compare all twelve semantic
   fields plus the stored fingerprint with the neutral authoritative state;
10. clear protected locals and return the reconstructed frozen request.

Failure before step 7 constructs zero requests. Every path performs zero
provider/runtime/generation calls. There is no alternate calculation, fallback
or second owner.

Exact `construct()` cardinality is:

```text
canonical projections = 1
authority fingerprint calculations = 1
direct frozen constructor calls = 1
copy.copy(completed_request) calls = 1
public reconstruct() calls = 0
returned authoritative reconstructions = 1
```

`construct()` MUST NOT call the authority's public `reconstruct()` method,
calculate a second fingerprint, build a second projection, call another frozen
constructor, or use a fallback construction path.

## 13. Reconstruction sequence

1. require exact `EditorGenerationExecutionRequestV1` type;
2. read its thirteen public fields through static known field names into
   neutral local values;
3. reconstruct all twelve semantic fields at their distinct boundaries;
4. validate generation/runtime/provider configuration parity and cross-object
   lineage/ordering;
5. build the section 9 canonical semantic projection exactly once;
6. recompute the authority fingerprint exactly once;
7. require exact built-in stored fingerprint and constant-time equality with
   the recomputed fingerprint;
8. invoke `copy.copy(request)` exactly once as the sole frozen public
   reconstruction mechanism;
9. require exact reconstructed request type;
10. compare every reconstructed semantic field and the stored fingerprint with
    the neutral authoritative state—not object equality alone;
11. clear protected locals and return the frozen public-copy reconstruction.

It returns a new equivalent validated request, never the source identity.
Subclasses, copied-invalid seals/state, stale/forged fingerprints, nested
substitution, ordering mismatch and foreign lineage fail.

Because the frozen private seal is not public, the single step 8 public copy is
the authoritative seal/state check. No private seal is read. `reconstruct()`
MUST NOT directly invoke the frozen constructor, call `copy.copy` a second
time, call `construct()`, call another public reconstruction method, build a
second projection, calculate a second fingerprint, or use a fallback path.

Exact `reconstruct()` cardinality is:

```text
canonical projections = 1
authority fingerprint calculations = 1
copy.copy(request) calls = 1
direct frozen constructor calls = 0
construct() calls = 0
returned authoritative reconstructions = 1
```

## 14. Failure model, boundaries, and precedence

The package exposes one exception type only:

```python
class EditorGenerationExecutionRequestAuthorityError(Exception): ...
```

Its sole message is:

```text
Editor generation execution request authority is invalid.
```

It has no fields, retryability, fingerprint, payload or nested error. Request
and fingerprint are absent on failure. The following package-private status set
is exact and is never exported:

```text
invalid_exact_input_type
invalid_request_state
invalid_preparation
invalid_generation_plan
invalid_flow_result
invalid_editorial_blueprint
invalid_commentary_blueprint
invalid_voice_plan
invalid_generation_configuration
invalid_runtime_options
invalid_provider
invalid_requested_timestamp
invalid_request_reference
invalid_cancellation
invalid_configuration_parity
invalid_lineage
canonicalization_failed
frozen_construction_failed
frozen_reconstruction_failed
fingerprint_mismatch
semantic_parity_failed
internal_authority_failure
```

All statuses map to the same fixed public error and are absent from its message,
attributes, repr, cause/context, traceback locals, logs and result. They are
neutral implementation control states, not public diagnostics.

### 14.1 Exact boundary ownership

- `invalid_exact_input_type` covers only a wrong exact public argument type or
  subclass detected before semantic reconstruction.
- `invalid_request_state` applies only in `reconstruct()` when static extraction
  of the thirteen declared public fields fails before nested reconstruction.
- Each of preparation, plan, flow, editorial, commentary and voice owns its
  correspondingly named reconstruction status. No artifact failure becomes a
  generic input or configuration failure.
- Generation configuration, runtime options, provider, timestamp, reference
  and cancellation each own their correspondingly named exact reconstruction
  status.
- `invalid_configuration_parity` covers only disagreement among successfully
  reconstructed configuration, runtime options and provider.
- `invalid_lineage` covers only cross-object source identity, reference,
  ordering and membership disagreement among successfully reconstructed
  artifacts.
- `canonicalization_failed` covers only failure to create exact canonical bytes
  from validated neutral semantic state.
- `frozen_construction_failed` applies only to the direct frozen constructor in
  `construct()`.
- `frozen_reconstruction_failed` applies only to the sole public copy in
  either public method.
- `fingerprint_mismatch` covers only stored versus authority-recomputed
  fingerprint disagreement in `reconstruct()`, or post-copy fingerprint
  disagreement in `construct()`.
- `semantic_parity_failed` covers only a successfully copied frozen request
  differing from the previously reconstructed neutral semantic state.
- `internal_authority_failure` is limited to finite package-owned return-state
  corruption after neutral reduction where no earlier enumerated status
  applies. It is not an injected, frozen, provider, runtime or open-ended
  failure source.

### 14.2 Exact `construct()` precedence

1. `invalid_exact_input_type`;
2. the individual semantic reconstruction status in parameter order;
3. `invalid_configuration_parity`;
4. `invalid_lineage`;
5. `canonicalization_failed`;
6. `frozen_construction_failed`;
7. `frozen_reconstruction_failed`;
8. `fingerprint_mismatch`, then `semantic_parity_failed`;
9. `internal_authority_failure`.

### 14.3 Exact `reconstruct()` precedence

1. `invalid_exact_input_type` for the request, then `invalid_request_state` for
   public-field extraction failure;
2. the individual nested semantic reconstruction status in field order;
3. `invalid_configuration_parity`;
4. `invalid_lineage`;
5. `canonicalization_failed`;
6. `fingerprint_mismatch`;
7. `frozen_reconstruction_failed`;
8. `semantic_parity_failed`;
9. `internal_authority_failure`.

### 14.4 Narrow exception constraints and neutral reduction

Each authority-bearing helper owns exactly one boundary:

```text
authority-bearing operation
  -> narrow owned catch
  -> one neutral built-in private status
  -> clear protected locals and raw exception
  -> leave the authority-bearing frame
  -> raise the fixed public error from a clean frame
```

No `except Exception` may span input reconstruction plus lineage,
canonicalization plus frozen construction, fingerprint comparison plus public
copy, or any other two statuses. A broad catch is permitted only immediately
around one precisely defined package-owned helper and maps only to
`internal_authority_failure`. Classification never inspects exception text,
repr, cause, context or traceback.

## 15. Object safety and dependency validation

The authority is `@dataclass(frozen=True, slots=True, init=False)` with no
fields and no `__dict__`. Construction is passive. Exact-type retained-state
checks reject substitution. Repr is exactly
`EditorGenerationExecutionRequestAuthorityV1()`. Equality is exact type only.
Copy/deepcopy return `self`; deepcopy records memo identity. Pickle raises
`TypeError`. There is no cache, singleton registry, mutable global or hook.

No dependency is injected, so dependency signature/descriptor validation is
inapplicable. This deliberately eliminates method, property, cached-property,
static/classmethod, partial, wrapper, forged-signature, dynamic-attribute,
instance-substitution and dependency-hook attack surfaces. Nested semantic
objects are validated by exact public frozen reconstruction, never repr,
equality hooks or dynamic lookup.

## 16. Error and traceback isolation

Authority-bearing work must reduce to neutral built-in status, clear locals,
leave protected frames, then construct the public error. The public exception
has:

```text
__context__ is None
__cause__ is None
__suppress_context__ is True
```

No public error or reachable traceback/frame/closure/container/nested exception
retains preparation, plan, artifacts, editorial content, configuration,
cancellation, operation reference, timestamp, canonical payload, fingerprint
bytes/string, request, raw exception, path or private helper. Raw Pydantic and
frozen request errors are suppressed without message inspection.

## 17. Passivity and determinism

Fresh import and authority construction perform zero fingerprint work,
provider selection/execution, credentials/environment access, networking,
runtime composition, generation, file/database I/O, threads, subprocesses,
timers, streams or warnings.

Identical valid semantic inputs yield identical payload bytes, fingerprint,
request, reconstructed result, repr, equality and cross-process result. All
time/reference/cancellation/configuration values are explicit. There is no
clock, UUID, random, PID, address, locale, filesystem, environment or Python
hash-order input.

## 18. Complete offline test matrix

Focused tests must cover:

1. exact four-file package, two ordered exports and passive imports/construction;
2. exact constructor/method signatures, annotations and keyword-only layout;
3. nominal construction with one authority calculation, one frozen
   construction and one frozen public-copy reconstruction;
4. exact projection of every field and frozen-constructor parity;
5. per-field mutation, NFC equivalence/distinction, timezone equivalence,
   numeric tagging, tuple order, timeout, cancellation and operation reference;
6. cross-process determinism and independently reviewed fixed-vector parity;
7. absence of any fingerprint/payload/digest/callback parameter or override;
8. exact-type/subclass/coercion rejection for all twelve inputs;
9. copied-invalid preparation, plan, flow, blueprints, voice, config, options,
   cancellation and request;
10. substituted artifacts, provider/config mismatch, lineage/order/foreign
    identity, extra/missing state and stale/forged fingerprint;
11. valid reconstruction returns a new equivalent request and detects
    seal-only corruption through frozen public copy;
12. slots/no dict, safe repr/equality, copy/deepcopy, pickle and no mutable state;
13. recursive traceback isolation for every private neutral failure source;
14. static source audit for private frozen imports and duplicate projection;
15. zero provider/runtime/I/O/CLI/export/Producer calls; and
16. frozen hashes/exports, full offline suite and static gates.

Construction cardinality and order tests are exactly:

```text
test_construct_calculates_fingerprint_once
test_construct_calls_frozen_constructor_once
test_construct_calls_public_copy_once
test_construct_never_calls_public_reconstruct
```

Reconstruction cardinality and order tests are exactly:

```text
test_reconstruct_uses_one_canonical_projection
test_reconstruct_calculates_fingerprint_once
test_reconstruct_uses_one_public_copy
test_reconstruct_never_calls_frozen_constructor_directly
test_reconstruct_never_calls_construct
```

The tests instrument package-owned seams and assert the complete sequence, not
only final counts. No helper invocation may be counted twice through a nested
public call.

The failure-boundary matrix independently injects every private status:

```text
invalid_exact_input_type
invalid_request_state
invalid_preparation
invalid_generation_plan
invalid_flow_result
invalid_editorial_blueprint
invalid_commentary_blueprint
invalid_voice_plan
invalid_generation_configuration
invalid_runtime_options
invalid_provider
invalid_requested_timestamp
invalid_request_reference
invalid_cancellation
invalid_configuration_parity
invalid_lineage (identity, ordering and membership cases)
canonicalization_failed
frozen_construction_failed
frozen_reconstruction_failed
fingerprint_mismatch
semantic_parity_failed
internal_authority_failure
```

For every row, tests prove the intended boundary was reached through private
instrumentation without exposing the status; the public exception type/message
are identical; later stages are not called; protected state is absent from the
recursive exception graph; and no broader handler masks the earlier category.

Tests obtain expected parity from successful frozen construction inside the
authority and observable public fields. They must not import frozen private
helpers or implement `_semantics`/canonical hashing.

## 19. Private-helper and duplication audit

Implementation review must establish:

- no import path contains a frozen private module or underscore symbol;
- section 9 exists exactly once, inside this authority package;
- no other production/test module builds the payload or digest;
- `canonical.py` exports nothing from package `__all__`;
- the future application imports only the two public symbols;
- the frozen constructor accepts every produced fingerprint; and
- frozen source hashes and APIs remain unchanged.

Necessary byte-compatible reimplementation means the single reviewed private
compatibility code in this additive public-authority package. Prohibited
duplication means any payload/hash implementation elsewhere, including tests
or Phase 4.3.

## 20. Frozen-package policy

The chosen architecture is additive independent compatibility implementation,
validated by the frozen constructor. It does not expose or require a lower
primitive and does not modify:

- `editor_generation_execution_v1`;
- `editor_generation_authority_v1`;
- `editor_request_fingerprint_authority_v1`; or
- `editor_operational_execution_v1`.

Singular public ownership is preserved: only the new authority constructs the
aggregate fingerprint for callers; frozen private computation remains its
unchanged validation oracle.

## 21. Phase 4.3 integration contract

After this authority is verified, Phase 4.3 performs:

```text
reconstruct explicit application inputs
  -> successful deterministic preparation
  -> deterministic flow/editorial/commentary/voice artifacts
  -> EditorGenerationExecutionRequestAuthorityV1.construct(...)
  -> EditorOperationalExecutionCoordinatorV1.execute(request)
```

Phase 4.3 never calculates/accepts the fingerprint, imports authority internals,
mutates the request, or catches private canonical errors. This task does not
modify the existing Phase 4.3 specification.

## 22. Revision roadmap

### Revision 1 — specification

Add only this file after reproducing the blocker. Entry is the exact Revision
3D baseline plus unchanged untracked Phase 4.3 specification. Exit requires
independent readiness review and static gates. Rollback removes this file only.

### Revision 2 — implementation and focused parity tests

Entry requires this specification independently implementation-ready.
Authorized paths are exactly the four-file package and one focused test in
section 6. Frozen packages, Phase 4.3, CLI, runtime, providers and Producer are
forbidden. Run focused/full offline tests, Ruff, Black, compileall, pip check,
diff/frozen audits and independent verification. Rollback removes only those
five additive paths.

### Revision 3 — freeze

After independent VERIFIED status and separate Git authorization, create one
scoped commit/tag. No implementation change belongs to this step.

### Phase 4.3 resumption

Independently revise/review the application specification against the verified
public authority before implementing application configuration or composition.

## 23. Contradiction scan

Search terms reviewed: `EditorGenerationExecutionRequestV1`, `fingerprint`,
`caller-supplied`, `canonical`, `projection`, `private`, `public authority`,
`reconstruct`, `lineage`, `generation configuration`, `preparation`, `runtime`,
`provider`, `Phase 4.3`, `duplicate`, and `singular authority`.

The document has exactly one public construction owner, no caller fingerprint,
no private frozen import, one canonical payload, one `construct()` sequence,
one `reconstruct()` sequence, one safe public failure, and the exact finite
private status set. `construct()` has one direct constructor and one public
copy; `reconstruct()` has zero direct constructors and one public copy. Each
public method calculates one fingerprint. Construction and reconstruction have
separate precedence tables; preparation, generation configuration and lineage
are never merged. No broad cross-boundary handler is authorized. There is zero
runtime/provider execution, Phase 4.3 implementation or frozen modification.
The controlled compatibility implementation and prohibited duplication boundary
are explicit. No load-bearing decision remains unresolved.

## 24. Findings by severity

Critical: none.

Major: none open. The missing-public-authority blocker is resolved
normatively by the additive architecture in sections 5–13 and remains to be
implemented only after independent verification.

Minor: none open.
