# M6C.6D Draft Revision Executor

## Part 1 contract architecture

M6C.6D owns controlled revision semantics only. M6C.5F decides, M6C.6A
plans, M6C.6B dispatches, M6C.6D will execute, and Controlled Generation will
provide provider-neutral generation. Part 1 defines immutable contracts and does
not execute or invoke generation.

Revision is not regeneration. Regeneration creates a fresh replacement draft;
revision authorizes changes only at explicit structural targets while preserving
all unlisted content. Supported targets mirror `EpisodeDraft`: opening, story by
stable story ID, transition by its stable story pair, closing, and call to action.
There is no whole-document wildcard, title target, or metadata target because the
current draft contract exposes no such stable structures.

The default policy requires explicit scope and preservation of unmodified
content. Structural and factual changes are denied unless an explicitly built
policy authorizes them. Scopes are nonempty, bounded, deduplicated, and sorted by
a canonical structural order. Instructions are bounded editorial intent tied to
the exact scope fingerprint; they are never provider prompts.

`DraftRevisionRequest` preserves the authoritative executor request and source
draft objects. It accepts only `REVISE_DRAFT` with `DRAFT_REVISION`, validates
authorization, and proves every target exists in the source. A successful result
requires a distinct immutable `EpisodeDraft`; preservation never means object
reuse.

The capability output reference contains only fingerprints and embeds the exact
M6C.6B.1 generic `CorrectiveActionOutputReference` intended for a future
version-2 executor result. To avoid circular hashing, its
`revision_result_fingerprint` is the deterministic semantic result-core
fingerprint; the final result fingerprint additionally commits to the completed
output reference. Lineage is executor request → revision request → result core →
revision output reference → final result → future executor result.

Reports exclude drafts and instruction prose. Diagnostics reject secrets,
paths, prompts, email-like content, exception traces, and provider details.
There are no provider SDKs, HTTP/database access, persistence, retries, runtime
executors, services, or reverse dependencies.

## Architecture self-review

BLOCKING: none.

HIGH PRIORITY: Part 2 must define how typed revision scope and instructions are
projected onto the existing Controlled Generation boundary without turning a
revision into regeneration or constructing raw prompts.

WORTH CONSIDERING: regeneration and revision demonstrate repeated pure
fingerprint and safe-report patterns, but their output semantics and preparation
rules are not yet sufficiently identical to justify a shared executor framework.
Shared utilities should be considered only after both runtimes exist.

DO NOT CHANGE: frozen decision, planning, dispatch, regeneration, Controlled
Generation, and `EpisodeDraft` contracts. Do not introduce inheritance between
revision and regeneration.

Known limitation: the current `EpisodeDraft` has no stable title or metadata
target, and Controlled Generation has no revision-specific request contract.
Both remain deferred rather than represented through fragile free-form selectors.

## Part 2 request preparation

Part 2 implements preparation only. It does not implement the production Draft
Revision executor and does not invoke Controlled Generation.

### Authoritative input and compatibility evolution

The authoritative input is now `CorrectiveActionExecutorRequestV2`. This is the
approved M6C.6B.2 compatibility evolution required because the frozen v1
request cannot carry `DraftRevisionPlanningInput`. The v2 transport preserves
its exact v1 `legacy_request`, planning result, and planning input. The
capability-owned `DraftRevisionRequest` therefore retains
`executor_request_v2.legacy_request` by identity, while the preparation result
retains the v2 request itself. No v1 contract or fingerprint was changed.

Preparation requires the exact registered descriptor object, not merely an
equal reconstruction. The composition caller supplies that canonical registry
object. Executor-request v2 validation occurs once before resolution; version,
fingerprint, planning lineage, action, capability, plan type, descriptor, and
authorization failures stop preparation.

### Preparation flow and ownership

`DraftRevisionPreparationService.prepare` is the sole public boundary. Its
deterministic sequence is:

1. Validate executor-request v2 and exact descriptor identity.
2. Resolve the exact `DraftRevisionPlanningInput` objects once.
3. Validate the explicit scope and build preservation metadata.
4. Construct and validate one frozen `DraftRevisionRequest`.
5. Evaluate all mandatory preconditions in controlled enum order.
6. Project one provider-neutral `ControlledRevisionRequest`.
7. Validate the projection with the frozen Controlled Revision validator.
8. Construct one immutable preparation result.

`DraftRevisionInputResolver` returns the exact source draft, policy, scope, and
instructions already authorized by planning. It never copies, deserializes,
infers, broadens, or substitutes them. `DraftRevisionRequestFactory` preserves
those identities and delegates domain validation to the Part 1 validator.

### Scope, targets, policy, and preconditions

Part 1 and planning validators remain the authoritative owners for nonempty,
canonical, deduplicated scope; supported target identities; target existence;
scope/policy limits; instruction/scope lineage; and typed regeneration
rejection. Preparation does not reproduce those rules.

The precondition evaluator records exactly one ordered finding for executor
validity, capability, action, authorization, source, policy, scope, target
count, instructions, policy permission, regeneration semantics, preservation,
and projection support. Any failed required finding rejects preparation. A
secondary conservative instruction check blocks explicit factual or structural
changes denied by policy and common whole-draft rewrite phrases; typed scope and
policy remain authoritative.

### Preservation baseline

`DraftRevisionPreservationManifest` contains no prose. It commits to:

- source-draft fingerprint;
- canonical authorized target fingerprints;
- fingerprints of every untargeted opening, closing, story, transition, or CTA;
- immutable episode-ID fingerprint;
- story/transition/CTA structural-order fingerprint;
- authoritative scope fingerprint.

The manifest builder runs once. It establishes evidence for the Part 3 result
validator and the already-frozen Controlled Revision preservation validator;
it does not delegate preservation authority to a provider.

### Controlled Generation boundary

The former blocker is resolved by Controlled Generation Revision Evolution
Parts 1–2. `ControlledGenerationRevisionRequestProjector` maps capability-owned
typed targets, instructions, policy, and preservation metadata into the
dedicated `ControlledRevisionRequest`. The source draft crosses by exact
identity. Each projected contract retains its upstream fingerprint, and the
request references the planning-input and executor-request-v2 fingerprints.

The projector creates no prompt, provider configuration, SDK/HTTP payload, or
generation mode. It cannot fall back to regeneration or legacy generation. The
preparation service contains no gateway dependency, so generation invocation
count is structurally zero.

### Results, lifecycle, reports, and failures

A prepared result contains all validated artifacts and enforces their exact
nested identities. A rejected or internally failed result exposes no partial
runtime artifacts—only the input fingerprint, safe diagnostic, immutable
lifecycle, and result fingerprint. Unexpected exception messages are discarded.

The successful lifecycle is:

`received → validating_executor_request → resolving_input → validating_scope →
building_preservation_baseline → building_revision_request →
evaluating_preconditions → projecting_generation_request →
validating_projection → prepared`.

Controlled rejection or internal failure terminates after the last reached
phase. Histories contain no timestamps and are canonically fingerprinted.

Preparation reports expose only controlled identifiers, counts, statuses,
diagnostic codes, lifecycle names, and fingerprints. Source prose, revised
prose, instruction prose, provider data, prompts, credentials, paths, and raw
exceptions are excluded. Report serialization is deterministic canonical UTF-8
JSON and is not a runtime input format.

### Invocation guarantees and architecture review

Each dependency is invoked at most once: request validator, resolver, request
factory, preservation builder, evaluator, projector, and projection validator.
Failures stop subsequent dependencies. There is no retry, fallback, alternate
policy, alternate source, silent repair, registry discovery, persistence,
network access, provider import, generation gateway, or production executor.

Architecture self-review:

- **BLOCKING:** none.
- **HIGH PRIORITY:** Part 3A must consume only a validated prepared result and
  invoke the frozen Controlled Revision runtime exactly once.
- **WORTH CONSIDERING:** regeneration and revision share pure report and
  fingerprint patterns, but their preparation semantics remain too different
  for a frozen shared framework.
- **DO NOT CHANGE:** upstream decision/planning/dispatch contracts, legacy
  generation modes, Part 1 capability contracts, and Controlled Revision
  contracts.

Known limitations are intentional: no provider adapter, executor runtime,
result wrapping, persistence, publication, retry, or fallback exists in Part 2.
The current target vocabulary remains limited to stable `EpisodeDraft`
structures. Part 3A may now consume the prepared Controlled Revision invocation
boundary in its separately approved runtime milestone.

## Part 3A production executor

Part 3A adds the capability-specific production execution boundary but does not
integrate it with the dispatcher or application composition.

### Ownership and authoritative input

`DraftRevisionExecutor.execute` is the sole production entry point. Its only
accepted input is the exact immutable `DraftRevisionPreparationResult` from
Part 2. It does not accept executor requests, planning inputs, source drafts,
scopes, instructions, manifests, dictionaries, or serialized projections.

The executor validates preparation once and requires the prepared outcome,
prepared status, terminal prepared lifecycle, valid nested lineage, and the
existing `ControlledRevisionRequest`. Invalid preparation causes zero
Controlled Revision service calls. The executor never invokes the resolver,
precondition evaluator, preservation builder, capability request factory, or
preparation service.

### Invocation and exactly-once execution

`ControlledRevisionInvocationFactory` wraps the exact prepared request:

`invocation.request is preparation_result.generation_request`.

It does not inspect prose, copy request fields, recanonicalize targets, rebuild
preservation, or add provider/model/prompt configuration. The invocation is
constructed once and validated with the frozen Controlled Revision validator.

The executor depends on an explicitly injected provider-neutral service
protocol exposing only `execute(invocation)`. It does not import or invoke
`ControlledRevisionGateway`. For a valid preparation, the service is called
exactly once with the exact invocation object. Approved failures, malformed
results, lineage failures, and executor mapping failures cannot trigger another
call. There is no retry, repair, fallback, regeneration, legacy generation, or
scope broadening.

### Result validation and mapping

The frozen Controlled Revision result validator remains authoritative for its
contract version, fingerprint, success/failure shape, nested draft, lifecycle,
diagnostic, and invocation lineage. The executor adds only capability-owned
lineage checks connecting:

`executor request v2 → preparation → controlled request → invocation →
controlled result → executor result`.

It verifies planning-input, executor-request, source-draft, revision-request,
invocation, preservation, and output-contract fingerprints. It never
reconstructs upstream objects.

`DraftRevisionExecutionResult` is the single executor-owned result. Success
preserves the exact preparation, invocation, Controlled Revision result, and
revised draft identities. Approved Controlled Revision failure preserves its
safe typed result and nested diagnostic code but exposes no revised output.
Malformed or mismatched results are omitted from authoritative result fields.

### Lifecycle, diagnostics, and exceptions

The deterministic success lifecycle is:

`created → preparation_validated → invocation_created →
controlled_revision_invoked → controlled_revision_completed → result_validated
→ completed`.

Failures terminate after the last reached phase. Histories are immutable,
versioned, fingerprinted, and contain no time or exception data.

Executor diagnostics distinguish invalid preparation, non-executable
preparation, invalid invocation, Controlled Revision failure, malformed result,
lineage mismatch, output failure, lifecycle failure, and unexpected internal
failure. Controlled Revision diagnostics remain nested provider-neutral codes;
they are not reinterpreted as editorial decisions. Raw exception classes,
messages, tracebacks, paths, credentials, prompts, provider payloads, and draft
content are discarded.

### Reporting, serialization, and privacy

The safe execution report contains capability/action, status/outcome,
target count, lifecycle, approved diagnostic codes, and complete fingerprint
lineage. It contains no source, revised, or instruction prose; provider/model
metadata; prompt payload; credentials; exception text; paths; or unsafe object
repr. Canonical UTF-8 JSON serialization is deterministic and remains a
non-reconstructable projection distinct from domain serialization.

### Dependency and architecture audit

The preparation validator, invocation factory and validator, Controlled
Revision service, Controlled Revision result validator, result factory, and
final result validator are injected explicitly and invoked at most once on each
normal terminal path. There is no singleton, registry, discovery, dispatcher
change, global registration, persistence, publication, networking, cache,
provider adapter, or prompt renderer.

Reuse/duplication classification:

- Controlled Revision validators and lifecycle: **DO NOT CHANGE**, reused by
  ownership rather than duplicated.
- Capability executor lifecycle and result factory: **JUSTIFIED**, because
  executor outcomes and corrective-action lineage differ from subsystem runtime
  outcomes.
- Canonical fingerprint/report serialization: **DO NOT CHANGE**, existing pure
  utilities are reused.
- Exception normalization and test spies: **JUSTIFIED** at the capability
  boundary and in tests.
- A generic executor framework: **CANDIDATE FOR FUTURE EXTRACTION** only after
  more stable capabilities demonstrate identical execution semantics.

Architecture self-review finds no blocking issue. Dependency direction remains
one-way from Draft Revision execution to Part 2 preparation and provider-neutral
Controlled Revision. Controlled Revision does not depend back on this executor.
The executor remains capability-specific because preparation eligibility,
corrective-action lineage, mapping, and diagnostics are Draft Revision
semantics; gateway execution remains Controlled Generation-owned.

### Known limitations and Part 3B boundary

Part 3A intentionally has no provider adapter or prompt projection, dispatcher
integration, executor registration, final application composition, persistence,
publication, retry, or fallback. Execution requires a prebuilt validated Part 2
result and supports only stable `EpisodeDraft` targets. Part 3B owns final
composition, generic corrective-action adaptation, registration, end-to-end
integration, and the final M6C.6D freeze audit.
# Part 3B: Corrective Action integration and final freeze

The production Draft Revision path is now an explicit version-2 lane:
`CorrectiveActionExecutorRequestV2` is resolved by an immutable typed binding,
prepared once by `DraftRevisionPreparationService`, and—only when executable—run
once by `DraftRevisionExecutor`. The generic response retains the exact executor
result object and carries deterministic request, preparation, execution, and
response fingerprint lineage.

The existing version-1 dispatcher and its bindings remain unchanged. Draft
Revision alone uses the v2 lane because its authorized planning input is required
by preparation. Routing uses the `DRAFT_REVISION` capability and
`REQUEST_REVISION` action enums; unsupported or ambiguous routes fail closed
before preparation.

The composition root constructs only the integration and immutable binding from
injected frozen services. It contains no validation rules, prompt projection,
provider or gateway access, retry, fallback, persistence, publication, or
post-revision approval. Controlled Revision remains entirely behind the Part 3A
executor.

Call-count guarantees are: routing rejection 0/0/0, preparation rejection 1/0/0,
and executable outcomes 1/1/1 for preparation/executor/Controlled Revision.
Nested lifecycles remain authoritative; the outer lifecycle records orchestration
only. Safe reports are UTF-8-capable deterministic metadata projections and never
contain draft text, instructions, provider payloads, exception text, paths, or
credentials.

Architecture reconciliation deliberately keeps the v1 dispatcher intact and
adds one v2 capability-neutral dispatcher rather than forcing unrelated
executors through a new contract. Similar binding and resolution shapes are
intentional compatibility duplication and are candidates for extraction only
after another v2 capability demonstrates the need. No blocking ownership or
dependency-direction finding remains. Known limitations are the intentionally
absent provider adapter, persistence, publication, retry, fallback, and
post-revision QA. M6C.6D is safe to freeze when the complete quality gates pass.

## Part 3C: V2 integration hardening

The v2 boundary now enforces exact identity between the request received by the
integration and the request retained by its preparation result. A substituted or
cross-request preparation is rejected before the executor is invoked; equal
fingerprints are deliberately insufficient.

The capability-neutral dispatcher validates every integration response before
returning it. Validation covers response type, current request identity, resolved
capability and action, attached capability-result execution lineage, and the
response fingerprint. Invalid integration responses are normalized to the safe
canonical internal-failure response without retry or downstream reconstruction.

Malformed executor envelopes and invalid request fingerprints are normalized to
canonical routing failures. The binding collection is a frozen, canonically
ordered tuple and cannot be reassigned after composition. These checks change no
Part 2, Part 3A, Controlled Revision, Controlled Generation, v1 dispatcher, or
provider boundary behavior.
