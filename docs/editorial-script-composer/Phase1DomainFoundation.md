# Module 2.9 Phase 1 Domain Foundation

## Contract hardening

The public Phase 1 boundary uses closed vocabularies for factual certainty,
attribution, span binding, delivery, structural roles, generation policy, and
revision disposition. `construct_artifact()` translates untrusted Pydantic
payload failures into stable `DomainValidationIssue` values.

`validate_artifact()` recursively verifies every registered nested semantic
fingerprint and deterministic identity. Text spans are reusable coordinates;
duplicate semantic evidence edges are rejected separately, and attribution or
claim spans must belong to their sentence. Delivery annotation type and
semantic effect are validated as a strict matrix.

Provider response status, failure reason, and request lineage must match the
nested execution reference. Generated slots are unique and partial target
classifications must be contained by the originating request. Revision
contracts separate factual evidence from authoritative legal inputs, prevent
system regeneration from changing authority inputs, and restrict partial
results to inspection-only use.

Provider-request reference consistency, provider-response consistency, and
attribution-ownership invariants are shared by model construction and explicit
recursive validation. Copying and resealing an invalid artifact therefore
cannot bypass these structural guarantees. Public construction maps their
stable invariant codes and field paths into `DomainValidationError`.

Rejected provider units and rejected targets are parallel, one-to-one ordered
collections; rejected targets participate in the same disjointness rule as
completed and missing targets. System regeneration binds its immutable target
scope fingerprint to the concrete revision scope and target references. A
partial revision may omit an inspection draft, but any draft it exposes remains
`inspection_only`; a successful revision requires a replacement draft.

## Package layout

The public package is `pastila_scout.editor.script_composer`:

- `models.py` contains immutable first-class domain contracts;
- `vocabularies.py` contains closed editorial and execution-independent values;
- `canonical.py` owns canonical UTF-8 semantics and SHA-256 fingerprints;
- `identity.py` owns deterministic `scout:<artifact-type>:<sha256>` identities;
- `validation.py` provides pure structured validation;
- `profile.py` contains the immutable Pastila Acidă reference profile;
- `defaults.py` contains canonical identity and field-participation policy.

## Immutable contracts

Contracts use frozen Pydantic models, reject unknown fields, normalize nested
collections to immutable tuples, and normalize strings to Unicode NFC.
Revisions create new artifacts; no public update operation mutates an artifact.

The package includes the frozen script hierarchy, claim/evidence bindings,
`TextSpanReference`, `GenerationProfile`, `ResolvedGenerationPolicySnapshot`,
provider-neutral DTOs, revision authority and result contracts, generation
traceability, structured conflicts, and validation findings.

## Canonical serialization

Canonical rendering uses deterministic JSON with UTF-8 and NFC strings.
Mappings are sorted by key. Collections that are semantically ordered retain
their order; other collections are normalized by canonical content.
Unsupported runtime objects are rejected.

Self-fingerprint fields, timestamps, runtime provenance, token and retry data,
recomputable validation findings, and derived readiness are excluded from
semantic fingerprints. Presentation-only delivery annotations are excluded
from parent semantic identity; semantic annotations remain included.

## Identities and fingerprints

Canonical identities use the complete lowercase digest:

```text
scout:<artifact-type>:<64-character-sha256>
```

Identity functions use the exact structural seeds frozen by the Module 2.9
Contract Closure Amendment. Logical sentence identity is stable across a
wording-only revision, while its semantic fingerprint changes. A changed
parent creates a new identity. Random UUIDs are not canonical domain IDs.

Semantic fingerprints use SHA-256 over canonical UTF-8 bytes. Provider
execution identity remains separate from script semantics.

## Unicode and TextSpanReference

Sentence and span text is NFC. Span offsets count Unicode code points and use
the half-open interval `[start_offset, end_offset)`. Validation compares the
exact slice with `referenced_text`; repeated substrings are distinguished by
offsets. Proper nesting is valid, while crossing overlaps and duplicate
equivalent bindings are invalid.

## GenerationProfile

`GenerationProfile` is fully resolved, immutable, and provider-neutral. It
contains no audience ages or demographics and cannot redefine the Audience
Model. It contains no provider, model, prompt, sampling, retry, or token
parameters. Custom values require exact `custom:<slug>` syntax plus immutable
authority and semantic-documentation references.

`PASTILA_ACIDA_GENERATION_PROFILE` supplies the frozen Romanian conversational
baseline described by the architectural amendment. Audience identity remains
owned by its Audience Model reference.

## Resolved generation policy

`ResolvedGenerationPolicySnapshot` carries the source policy lineage, resolved
instructions and constraints, explicit satire permissions, authority, and
resolution decisions. Module 2.9 never reconstructs policy dynamically.
Satire permission specificity is target, beat, segment, episode, then implicit
prohibition. Equal-specificity contradictions are structurally detectable.

## Provider-neutral DTOs

The domain defines immutable provider request, generated-unit, partial-response,
response, execution-reference, and response-acceptance contracts. A provider
response remains an untrusted proposal and is not accepted merely because its
external execution status is successful. Phase 1 performs only structural and
lineage validation and imports no provider SDK.

## Revision contracts

`RevisionAuthority` implements the frozen system/editor/editor-in-chief
compatibility matrix without introducing RBAC. `RevisionRequest` preserves
upstream lineage. `RevisionExecutionResult` separates changed, preserved,
removed, and new units and proves immutable fingerprint continuity. Phase 1
does not execute revisions.

## Validation and errors

Pydantic construction enforces contract shape. Additional pure validators
return immutable `DomainValidationIssue` objects with stable codes, artifact
references, field references, and related references. Strict callers may use
`DomainValidationError`, which retains the complete issue collection.

Phase 1 does not claim to validate humor quality, Romanian naturalness, voice
fit, emotional impact, rhetorical elegance, subjective pacing, or editorial
appropriateness.

## Deferred work

The following remain Phase 2 or later responsibilities:

- input authority and complete CompositionPlan compatibility orchestration;
- provider adapter execution and network calls;
- provider-response acceptance workflow orchestration;
- draft assembly from generated units;
- full claim, attribution, legal, and editorial validation;
- readiness derivation;
- revision execution;
- editorial and teleprompter rendering;
- persistence and publication workflows.
