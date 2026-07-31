# M6C.6C — Draft Regeneration Executor

## Part 1 objective and ownership

Part 1 defines the immutable capability-specific contract boundary for a future
draft-regeneration executor. It contains no executor runtime and never invokes
Controlled Generation or a provider.

```text
M6C.5F decides.
M6C.6A plans.
M6C.6B dispatches.
M6C.6C regenerates.
```

M6C.6C accepts only `REGENERATE_DRAFT` plans requiring
`DRAFT_REGENERATION`. It never reinterprets the authoritative execution plan,
resolves another executor, dispatches recursively, revises text, routes manual
review, publishes, persists, queues work, or resumes another workflow.

Regeneration creates a new `EpisodeDraft` and never mutates the source draft.
Revision is a separate future capability that transforms an existing draft.

## Frozen input and descriptor

The authoritative input is the exact frozen M6C.6B
`CorrectiveActionExecutorRequest`. `DraftRegenerationRequest` preserves that
object and adds only a regeneration policy and typed regeneration input. Plan
type, execution mode, capability, action, reason, plan fingerprint, and executor
descriptor are always read from the nested request and are never reconstructed.

The canonical descriptor is `draft-regeneration.v1`. It advertises exactly
`DRAFT_REGENERATION`, exactly `REGENERATE_DRAFT`, and supports both automatic
and explicitly authorized human-gated invocation. `NON_EXECUTABLE` is rejected.
Human-gated requests require the already-frozen M6C.6B authorization state to
be `GRANTED`; M6C.6C cannot infer or override authorization.

## Controlled Generation reuse

`DraftRegenerationInput` reuses the existing immutable
`ControlledGenerationInvocation`, `GenerationPolicy`, and optional
`EpisodeDraft`. A future result reuses `ControlledGenerationResult` and its
exact `draft`. No parallel prompt, provider-request, generation-request, draft,
or generation-result model is introduced.

The source draft must be supplied through this approved capability-specific
input because neither the frozen execution plan nor M6C.6B executor request
contains it. It is bounded context only. Successful output must satisfy:

```text
result.regenerated_draft is result.generation_result.draft
result.regenerated_draft is not input.source_draft
```

Object identity is authoritative; Part 1 does not compare prose.

No raw prompt, provider message, model identifier, provider SDK type, API key,
or provider payload appears in an M6C.6C public contract. Provider-specific
generation logic is outside Part 1.

## Policy and preconditions

The immutable policy fixes fresh generation, distinct output identity, output
fingerprinting, and generation lineage. It may allow the source draft as bounded
context. It cannot change plan type, capability, execution mode, source action,
source reason, or authorization.

Typed precondition observations cover source input, generation policy,
Controlled Generation contract compatibility, executor-request integrity, plan
lineage, and authorization. They validate already-declared M6C.6A requirements;
they do not add, remove, or reinterpret plan preconditions.

## Outcomes, statuses, and generic mapping

Regeneration outcomes remain separate from Controlled Generation and generic
executor outcomes. `COMPLETED` uses `COMPLETED`; all controlled failures use
`FAILED`. The complete deterministic generic mapping is:

- completed → generic completed/completed;
- invalid input, unsupported contract, or execution mode → failed invalid request;
- plan or capability mismatch → failed unsupported plan;
- authorization failure → failed authorization;
- precondition or generation-contract failure → failed precondition;
- invalid output or internal failure → failed internal.

Part 1 defines this mapping but does not construct or return a generic executor
result. The frozen M6C.6B generic result has no capability-output-reference
field, so the typed `DraftRegenerationResult` and its output reference remain a
separate capability-specific boundary. No frozen generic contract is altered.

## Results and output references

A successful result contains the exact request, exact Controlled Generation
result, exact new draft, a content-free output reference, and no diagnostic. A
failure contains no generation result, accepted draft, or output reference and
requires one safe typed diagnostic.

The output reference contains only its version/type, regeneration-request
fingerprint, regenerated-draft fingerprint, generation-result fingerprint, and
its own fingerprint. It contains no prose, provider data, path, or database ID.

## Fingerprints and validation

The deterministic lineage is:

```text
executor request
→ regeneration policy and input
→ regeneration request
→ Controlled Generation result and distinct draft
→ output reference
→ regeneration result
→ safe report
```

Fingerprints use the repository canonical UTF-8 SHA-256 function and approved
lineage fields only. They exclude clocks, randomness, environment, object
identity, report serialization, provider configuration, and raw prompt/draft
content where an existing fingerprint is available.

Pure validators cover policy, input, request, precondition, diagnostic, output
reference, result, descriptor, report consistency, and outcome mapping. Frozen
M6C.6A/M6C.6B validators are reused. Unsupported versions, enums, plan types,
capabilities, modes, authorization states, and nested fingerprint corruption
fail closed without repair.

## Safe reporting and serialization

Reports expose only outcome/status, plan and capability taxonomy, executor ID,
contract versions, diagnostic code, and safe lineage fingerprints. They never
contain draft prose, prompts, provider output, credentials, tokens, paths,
findings, or arbitrary metadata. Safe reports and serialized reports are never
generation inputs or executor inputs. JSON serialization uses stable keys,
enum values, explicit nulls, and UTF-8.

## Part 2 boundary

Part 2 may implement regeneration-request construction, deterministic
precondition evaluation, and a provider-neutral Controlled Generation boundary.
It must not invoke generation, implement the production executor, mutate a
draft, retry, or modify frozen M6C.6A/M6C.6B semantics.
# Part 2: deterministic preparation

Part 2 prepares a valid Controlled Generation request but never invokes it. The
authoritative `CorrectiveActionExecutorRequest` remains unchanged while a pure
factory validates its plan, capability, descriptor, execution mode, and
authorization; resolves one explicitly injected typed generation input; builds
the regeneration request; preserves the existing Controlled Generation
invocation by identity; and evaluates typed preconditions in canonical order.

The frozen generic executor request intentionally contains no generation
payload. Consequently, `DraftRegenerationInputResolver` must be composed with
an approved immutable `DraftRegenerationInput`. Absence fails explicitly; no
filesystem, database, environment, registry, or global fallback is allowed.
The source draft is optional and, when present, is preserved by identity because
the standard policy permits it only as context.

Preparation has a content-free immutable lifecycle from `received` through
`prepared` or `failed`. Fingerprints form a deterministic chain from executor
request and policy through input, regeneration request, existing Controlled
Generation invocation, precondition results, lifecycle state, and preparation
result. Reports contain only statuses, enum values, safe lineage fingerprints,
and counts; they exclude drafts, prompts, source prose, provider data, secrets,
exceptions, and paths.

M6C.6C does not construct raw provider prompts and does not select a provider or
model. A failed regeneration precondition prevents generation. A successful
Part 2 result means ready to generate, not draft generated. Each resolver,
projector, and evaluator is called at most once, with no retries or fallback.
The authoritative execution plan remains unchanged throughout preparation.

Part 3 may inject and invoke the existing Controlled Generation boundary only
after consuming a successful preparation result.

# Part 3: exactly-once regeneration runtime

`DraftRegenerationExecutor` implements the frozen generic executor protocol. It
validates the executor request, prepares once through the Part 2 factory, invokes
one injected provider-neutral Controlled Generation gateway at most once,
validates the returned frozen generation result and fresh-draft identity, builds
the capability-specific regeneration result, and wraps its output lineage in the
M6C.6B.1 generic output reference.

There is no retry, fallback, provider discovery, direct provider import, dispatch
construction, planning, persistence, or publication. The generation invocation
object is passed to the gateway by identity. Known failures and unexpected
exceptions become content-free generic executor failures. The runtime lifecycle
is immutable and deterministic; generation occupies exactly one phase.

## Part 3B: execution service and final runtime graph

The permanent runtime graph contains one `DraftRegenerationExecutionService`,
one `DraftRegenerationExecutor`, one Part 2 request factory/resolver/projector/
precondition evaluator, one generation-result validator, one result factory, and
one explicitly injected `ControlledGenerationGateway`. The service invokes its
executor once and normalizes only unexpected outer-boundary failures. All
regeneration rules and generation validation remain owned by the executor.

The deterministic composition root accepts a typed regeneration input and a
provider-neutral gateway. It does not read configuration, environment variables,
files, registries, or provider SDKs. Each call creates an isolated graph; there
are no singletons, discovery paths, pools, caches, concurrency, retries, or
fallbacks.

Successful flow is validation, preparation, one generation call, output
validation, regeneration-result construction, and version-2 generic result
wrapping. Preparation failures make zero generation calls. Generation and
runtime failures make at most one. The source draft, generation request, and
generation result retain object identity; output boundaries retain deterministic
fingerprint lineage without exposing content.

Service reports are non-authoritative projections containing only versions,
outcomes, identifiers, diagnostic codes, and approved fingerprints. They are
never runtime inputs and cannot reconstruct requests, drafts, or generated
content.

Known limitation: the frozen Controlled Generation result does not embed a
request fingerprint. Request-to-result lineage is therefore established by the
exact invocation boundary and the regeneration output references rather than a
nested generation-result field.
