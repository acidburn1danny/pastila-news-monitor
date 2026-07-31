# Controlled Generation Revision Evolution — Part 1

## Decision and original incompatibility

The frozen Controlled Generation path owns full-draft component generation. Its
three `GenerationMode` values (`standard`, `constrained`, and `minimal_safe`),
provider protocol, result, state, prompts, validators, and fingerprints do not
represent target selection, an authoritative source draft, preservation, or
revision lineage. Adding optional revision fields to those v1 objects would
create illegal combinations and change frozen serialization. Part 1 therefore
uses **Option A: a dedicated revision invocation family** under
`pastila_scout.editor.generation.revision`.

No legacy generation model, serializer, fingerprint, provider, or runtime was
modified. Revision is explicit and cannot be inferred from content or mapped to
a legacy generation mode.

## Compatibility audit

| Required semantic | Audit verdict | Part 1 treatment |
|---|---|---|
| Source draft | `REQUIRES_NEW_REVISION_CONTRACT` | Exact immutable `EpisodeDraft`, not reconstructed |
| Revision target set | `SUPPORTED_BY_REUSABLE_TYPED_CONTRACT` | Boundary projection retains typed identity and upstream fingerprint |
| Revision instructions | `SUPPORTED_BY_REUSABLE_TYPED_CONTRACT` | Typed boundary projection retains authorized scope and upstream fingerprint |
| Revision policy | `SUPPORTED_BY_REUSABLE_TYPED_CONTRACT` | Typed boundary projection retains upstream fingerprint |
| Preservation requirements | `REQUIRES_NEW_REVISION_CONTRACT` | `DraftPreservationRequirements` |
| Expected output type | `REQUIRES_NEW_REVISION_CONTRACT` | `ControlledRevisionOutputContract` |
| Request lineage | `REQUIRES_VERSIONED_EVOLUTION` | Dedicated request v1 |
| Result lineage | `REQUIRES_VERSIONED_EVOLUTION` | Dedicated gateway and controlled result v1 |
| Lifecycle | `REQUIRES_NEW_REVISION_CONTRACT` | Immutable revision lifecycle v1 |
| Privacy-safe reporting | `REQUIRES_NEW_REVISION_CONTRACT` | Request and execution projections |
| Deterministic serialization | `SUPPORTED_DIRECTLY` | Existing canonicalization convention reused without legacy changes |

There is no blocking incompatibility: the source draft is already an immutable
generation-owned contract and can cross this sibling boundary by identity.

## Ownership and dependency direction

Controlled Generation owns the revision request, invocation, output contract,
preservation transport, versioned gateway protocol, gateway result, controlled
result, validators, lifecycle, deterministic lineage, serializers, and safe
reports. It does not own authorization, target selection, policy creation,
dispatch, persistence, publication, provider configuration, or provider
adaptation.

The M6C.6D editorial domain already depends on Controlled Generation for
`EpisodeDraft`; reversing that dependency would create a cycle. Consequently,
the Controlled Revision boundary does not import executor packages. M6C.6D Part
2 must explicitly project its authoritative `DraftRevisionTarget`,
`DraftRevisionInstructions`, and `DraftRevisionPolicy` into their boundary
counterparts while preserving upstream fingerprints. It passes the exact
`EpisodeDraft`. This is deliberate boundary translation, not duplication of
executor behavior.

## Contract architecture

- `ControlledRevisionRequest` owns the explicit `revision` operation, exact
  source object, canonical targets, instructions, policy, preservation and
  output contracts, and upstream planning/executor fingerprints.
- `ControlledRevisionInvocation` wraps the request and a validated lifecycle.
- `ControlledRevisionGateway` is a separate protocol with `revise`; legacy
  language-model providers do not have to implement it.
- `ControlledRevisionGatewayResult` represents one provider-neutral candidate
  or safe failure with complete referenced lineage.
- `ControlledRevisionResult` represents terminal success or failure. Success
  requires a revised `EpisodeDraft`; failure prohibits one.

The gateway protocol is intentionally versioned by type rather than extending
`LanguageModelProvider`. Adapters can migrate independently in a later
milestone. Part 1 performs no gateway invocation.

## Source, targets, policy, instructions, and preservation

The exact source object is retained and its canonical fingerprint is carried
through every boundary. It is hidden from repr and safe reports. There is no
empty-draft or regeneration fallback.

Targets are a closed taxonomy (opening, story, transition, closing, and CTA),
canonicalized deterministically, checked against source structure, limited by
policy, and rejected when their set equals all editable draft regions. The
boundary objects retain upstream target fingerprints. Instructions carry
authorized prose at runtime, but repr and reports expose only fingerprints;
their authorized-scope fingerprint must match preservation lineage. Policy
cannot disable explicit scope or unmodified-content preservation.

Preservation is structured: allowed target fingerprints, protected component
fingerprints, immutable fields, structural compatibility, source lineage, and
upstream scope lineage. M6C.6D will construct concrete requirements; Controlled
Generation only validates and transports them. Output verification is deferred
to Part 2, as required.

## Output contract, lifecycle, and lineage

The output contract requires a canonical `EpisodeDraft`, source lineage,
preservation lineage, and distinct source/revised identity. It contains no SDK
or wire-format assumptions.

Lifecycle paths are deterministic prefixes of:

`created → validated → invoked → gateway_completed → output_validated → completed`

Failure may terminate after any reached non-terminal phase. Unknown versions,
duplicates, skips, repeats, and impossible transitions fail closed.

Fingerprint lineage is:

`source draft → upstream planning input → executor request v2 → revision request
→ invocation → gateway result → controlled result`.

Upstream fingerprints are referenced; they are not recomputed substitutes.
New identities use canonical UTF-8 JSON, SHA-256, no clock values, no provider
metadata, and no self-referential fingerprint fields.

## Validation, serialization, privacy, and provider neutrality

Each aggregate has one public validator owner in `validation.py`. Validators
revalidate nested immutable models and, when the related invocation/gateway
result is supplied, compare the complete lineage. Pydantic construction also
checks local invariants and fingerprints, so nested tampering fails closed.

Runtime serialization is deterministic and intentionally contains authorized
content; it is distinct from safe report serialization. Reports expose only
versions, statuses, lifecycle, counts, diagnostics, and fingerprints. They do
not contain source/revised prose, instruction prose, prompts, provider payloads,
credentials, raw exceptions, or model metadata. Content-bearing fields are
also excluded from repr.

The revision package imports no provider SDK, networking, authentication,
retry, persistence, cache, or dynamic discovery code. No prompt contract exists
in Part 1, preventing prompt smuggling.

## Architecture reconciliation and self-review

Intentional similarities with full generation are immutable Pydantic domain
models, typed protocols, canonical serialization, and structured output.
Intentional differences are a source draft, targets, preservation, explicit
revision operation, lineage-bearing results, and a revision lifecycle. Forcing
unification would either alter frozen v1 behavior or create nullable-field and
semantic-branching hazards. A small parallel family is justified because the
operation semantics differ while low-level canonicalization is reused.

The design satisfies single responsibility, dependency inversion at the
gateway, closed typed extension points, and one-way package dependencies. It
can later support human-guided, style, tone, or compliance rewrite through
typed instruction/policy evolution without weakening targeted preservation.
Full regeneration remains a separate capability.

Classification:

- **BLOCKING:** none.
- **HIGH PRIORITY:** Part 2 must validate actual protected-region equality and
  complete invocation/gateway/result lineage before producing success.
- **WORTH CONSIDERING:** a future shared editorial/generation target vocabulary
  could remove boundary projection, but only through a separately approved
  migration of frozen ownership.
- **DO NOT CHANGE:** legacy generation modes, providers, fingerprints,
  serializers, runtime, or M6C.6D authorization ownership.

## Known limitations and Part 2 boundary

Part 1 defines contracts only. It does not execute a gateway, verify returned
protected content, construct a Draft Revision executor, translate M6C.6D
objects, retry, cache, persist, publish, or call a provider. Part 2 may implement
the single controlled runtime service against the new gateway, but M6C.6D Part
2 must remain paused until that runtime is separately completed and frozen.

## Part 2 — Runtime compatibility freeze

### Pre-implementation audit and runtime architecture

The frozen Part 1 family supplies the dedicated request, invocation,
`ControlledRevisionGateway.revise`, gateway result, controlled result,
lifecycle, canonical fingerprint helper, deep validators, safe report, and
serializer. Legacy Controlled Generation uses a separate component-oriented
`ControlledGenerator` and `LanguageModelProvider.generate_structured` boundary.
Its provider exception handling, retries, generation modes, prompts, manifest,
state, and composition are intentionally unsuitable for targeted revision and
remain unchanged.

Part 2 adds one public production entry point:
`ControlledRevisionExecutionService.execute(invocation)`. The service is
composed by `compose_controlled_revision_execution_service` with exactly one
injected gateway, canonical invocation/gateway/result validators, one revised
draft validator, one output-contract validator, one preservation validator,
one lifecycle factory, and one result factory. Dependencies are stored and used
by exact identity; there is no singleton, registry, import scanning, service
locator, or runtime discovery.

### Authoritative execution sequence and call counts

The runtime sequence is:

1. Deeply validate the invocation and all nested request contracts.
2. Call the injected `revise(invocation)` gateway exactly once.
3. Validate gateway-result shape, fingerprint, nested draft, diagnostic, and
   complete invocation/request/source/output/preservation lineage.
4. Reject an approved gateway failure without exposing output.
5. Revalidate the exact returned `EpisodeDraft` through its canonical model.
6. Validate output type, contract version, source/output lineage, immutable
   episode identity, and distinct source/output identity.
7. Independently prove preservation using typed structural comparison.
8. Build one terminal result through the sole result factory and deeply
   validate it.

Invalid invocations produce zero gateway calls. Every path that reaches the
gateway produces exactly one call, including gateway failures, malformed
results, invalid output, lineage mismatch, and preservation failure. There is
no retry, repair invocation, secondary gateway, generation-mode fallback, or
regeneration fallback.

### Gateway and exception boundary

The runtime invokes only the injected provider-neutral revision protocol. It
does not import or call legacy generation methods. The service is the outer
unexpected-exception boundary: gateway exceptions are converted to the safe
`REVISION_GATEWAY_FAILURE` diagnostic without exception class, message,
traceback, path, credentials, provider data, or payload. Malformed gateway
objects and nested contract failures are distinguished from lineage failures.

Part 2 contains no provider adapter, SDK, HTTP client, model configuration,
authentication, prompt conversion, token handling, persistence, cache,
publication, or networking.

### Draft, output-contract, and preservation validation

The revised draft is revalidated with the canonical `EpisodeDraft`; no second
draft framework exists. The output validator checks the frozen typed output
contract and immutable episode identity before preservation analysis.

The preservation validator does not trust gateway self-declaration. It checks:

- exact source and target fingerprint lineage;
- story IDs and ordering;
- transition identities and ordering;
- CTA presence, placement, target and immutable static content;
- every untargeted opening, closing, story, transition and CTA by typed value;
- every declared protected source-component fingerprint;
- immutable episode identity and structural compatibility.

Because Part 1 rejects a target set equal to all editable regions, at least one
region remains protected. A narrow target with changes elsewhere, structural
replacement, disappearance/addition of regions, metadata substitution, or a
whole-draft replacement therefore fails deterministically. No similarity or
percentage heuristic is used. Changes within a target are accepted only after
all supplied structural, policy, preservation, and output constraints pass;
the runtime does not judge editorial quality.

### Results, lifecycle, lineage, and diagnostics

`ControlledRevisionResultFactory` is the sole result-construction owner and
preserves the exact revised-draft object from the gateway. The frozen Part 1
result represents other immutable objects by their approved fingerprints, so
the runtime validates those references rather than reconstructing objects.

The successful lifecycle is:

`created → validated → invoked → gateway_completed → output_validated → completed`.

Preservation validation occurs after `output_validated` and before `completed`.
The frozen Part 1 lifecycle intentionally has no separate preservation phase.
Failure paths terminate immutably after the last reached phase. No lifecycle
timestamp contributes to identity.

The runtime uses the minimal frozen Part 1 diagnostic vocabulary:

- invalid invocation → `INVALID_REVISION_REQUEST`;
- gateway exception or approved failure → `REVISION_GATEWAY_FAILURE`;
- malformed gateway result → `INVALID_REVISION_GATEWAY_RESULT`;
- mismatched references → `REVISION_LINEAGE_MISMATCH`;
- invalid output or output-contract mismatch → `REVISION_OUTPUT_INVALID`;
- unauthorized structural/content change →
  `INVALID_PRESERVATION_REQUIREMENTS`;
- final lifecycle/result failure → `REVISION_LIFECYCLE_INVALID`.

No diagnostic includes raw exception content.

### Reporting, serialization, privacy, and identity

The existing Part 1 execution report remains the single safe runtime
projection. It includes operation, terminal status, lifecycle and complete
controlled-runtime fingerprint lineage, while excluding draft prose,
instruction prose, prompts, provider/model data, credentials, exception text,
paths, and object repr. Safe serialization is canonical UTF-8 JSON and is not a
reconstructable invocation format. Content-bearing domain serialization remains
separate.

The runtime validates:

`source → planning reference → executor request reference → revision request →
invocation → gateway result → controlled result`.

Upstream fingerprints remain references. Equivalent executions have stable
result/report fingerprints and serialization; call count or wall-clock state is
not part of successful identity.

### Reuse, duplication, and architecture self-review

- Lifecycle transitions: **JUSTIFIED** dedicated revision lifecycle; legacy
  generation state is component-oriented and frozen.
- Report projections and canonical serialization: **DO NOT CHANGE**; Part 1
  implementations are reused unchanged.
- Gateway exception normalization: **JUSTIFIED** at the new operation boundary.
- Result factory: **JUSTIFIED** because revision has preservation and lineage
  invariants absent from full generation.
- Fingerprint validation: **DO NOT CHANGE**; Part 1 validators are reused.
- Test gateway spy: **JUSTIFIED**, test-only and deterministic.
- A generic capability runtime: **CANDIDATE FOR FUTURE EXTRACTION** only after
  more production capabilities demonstrate identical behavior.

SOLID ownership and dependency inversion are preserved: the service owns
orchestration, focused validators own proofs, the factory owns result shape,
and the injected protocol isolates future adapters. Controlled Generation does
not depend on M6C.6D, dispatch, planning, or provider packages. There are no
blocking architecture findings.

### Test evidence, limitations, and integration readiness

Focused tests prove exactly-once/zero-call behavior, exact invocation and draft
identity, deterministic success, approved failures, exception sanitization,
malformed results, all lineage mismatches, canonical draft validation,
protected-region and metadata rejection, whole-draft rejection, nested
tampering, lifecycle/version rejection, deterministic reports, privacy, and
composition identity. Full regression and quality-gate results are recorded in
the milestone completion report.

Known limitations are intentional: there is no production provider adapter or
prompt projection; no M6C.6D executor translation/integration; preservation is
limited to the typed structural invariants expressible by `EpisodeDraft`; the
target vocabulary remains the approved Part 1 set; and there is no persistence
or publication. These are not runtime contract defects. Once Part 2 is frozen,
M6C.6D Part 2 is architecturally ready to translate its authorized executor
request into this boundary in a separately approved milestone.
