# M6C.6B — Execution Dispatch

## Part 1 purpose and ownership

M6C.6B Part 1 defines immutable contracts for the future dispatch boundary:

```text
CorrectiveActionExecutionPlanResult
  -> CorrectiveActionExecutionDispatchRequest
  -> future capability resolution
  -> future executor invocation
  -> CorrectiveActionExecutionDispatchResult
```

M6C.5F decides. M6C.6A plans. M6C.6B dispatches. M6C.6C+ execute.

M6C.6A Parts 1–4 are frozen. The authoritative input is the complete frozen
`CorrectiveActionExecutionPlanResult`, retained by object identity. The request
does not accept reconstructed plan type, mode, capability, source action,
source reason, plan fingerprint, or decision result.

Dispatch does not reinterpret the execution plan. Part 1 has no registry,
resolver, dispatcher, lifecycle, real executor, invocation path, corrective
operation, publication, persistence, notification, queue, workflow continuation,
or infrastructure termination.

## Dispatch policy

The immutable dispatch policy contains:

- stable policy identity and version;
- whether automatic dispatch is allowed;
- whether a registered executor is required;
- the mandatory exact-capability rule;
- whether human-gated dispatch requests are allowed;
- the fixed completed treatment of non-executable plans;
- the required executor contract version.

Exact capability matching, registered-executor resolution, and completed
non-executable semantics cannot be disabled. Other switches may reject dispatch
but cannot change the plan type, execution mode, capability, source action,
source reason, or preconditions. `HUMAN_GATED` cannot become `AUTOMATIC`, and
`NON_EXECUTABLE` cannot become executable.

## Execution context and authorization

`CorrectiveActionExecutionContext` contains only authorization state, requested
executor contract version, a stable caller-supplied dispatch-attempt ID, an
optional correlation fingerprint, an optional approved-environment ID, and its
fingerprint. Identifiers are lowercase, case-sensitive, bounded, and restricted
to letters, digits, dots, and hyphens. Paths, whitespace, arbitrary metadata,
credentials, tokens, queue names, addresses, and content are not supported.

Authorization states are `NOT_REQUIRED`, `REQUIRED_NOT_GRANTED`, `GRANTED`,
`DENIED`, and `UNKNOWN`. Automatic executor requests require `NOT_REQUIRED`.
Human-gated executor requests require `GRANTED`. `NON_EXECUTABLE` plans must
never reach an executor. Part 1 does not obtain authorization.

## Executor contract and descriptor

`CorrectiveActionExecutor` is a capability-neutral protocol with one immutable
descriptor and one `execute(request) -> result` method. No production class
implements it in Part 1.

Each descriptor declares one stable executor ID, one executor contract version,
exactly one non-`NONE` capability, a canonical immutable tuple of explicitly
supported plan types, automatic/human-gated support flags, and a deterministic
fingerprint. Every advertised plan type must require that exact capability.
Universal or fuzzy executors are invalid.

The compatibility rules are exact:

| Plan type | Required capability |
| --- | --- |
| `NO_CORRECTIVE_EXECUTION` | `NONE` — never executor-compatible |
| `REVISE_DRAFT` | `DRAFT_REVISION` |
| `REGENERATE_DRAFT` | `DRAFT_REGENERATION` |
| `CREATE_MANUAL_REVIEW_REQUEST` | `MANUAL_REVIEW_ROUTING` |
| `BLOCK_AUTOMATIC_CONTINUATION` | `WORKFLOW_CONTINUATION_BLOCK` — non-executable |

Capability equality is necessary but not sufficient: the plan type must also be
explicitly listed by the descriptor. There is no alias, subtype, fuzzy,
executor-side `supports()`, or fallback decision.

Future resolution requires exactly one compatible executor. Zero matches fail;
two or more matches are ambiguous and fail. There is no first/last registered,
alphabetical, random, or priority fallback.

## Executor request and result

The executor request retains the complete planning result, its exact nested
plan, descriptor, execution context, version, and fingerprint. Validation
requires `executor_request.plan is executor_request.planning_result.plan`, exact
capability and plan compatibility, invocation-mode support, and valid
authorization. It never accepts a safe report as input.

The generic executor result retains the exact descriptor and executor request.
It separates executor operational outcome from execution status. A completed
outcome requires `COMPLETED` status and no diagnostic. Failures require
`NOT_STARTED` or `FAILED` status and a typed diagnostic. No revised draft,
regenerated content, ticket, provider response, queue receipt, publication
record, or unrestricted output payload exists. Capability-specific output
contracts belong to future executor milestones.

## Dispatch outcome and status

Dispatch operational outcomes are separate from dispatch status, executor
outcome, and plan semantics. Statuses distinguish `NOT_ATTEMPTED`,
`NOT_DISPATCHABLE`, `AWAITING_AUTHORIZATION`, `DISPATCHED`,
`EXECUTOR_COMPLETED`, `EXECUTOR_FAILED`, and `DISPATCH_FAILED`.

A valid non-executable plan uses:

```text
operational outcome = COMPLETED
dispatch status = NOT_DISPATCHABLE
executor descriptor/request/result = absent
```

A valid non-executable plan is not an invalid plan. `NO_CORRECTIVE_EXECUTION`
and `BLOCK_AUTOMATIC_CONTINUATION` therefore complete dispatch evaluation
without invocation. Failed, corrupted, or unsupported planning results cannot
become completed dispatches or fallback plans.

An authorization gate uses `COMPLETED + AWAITING_AUTHORIZATION`, no executor
request/result, and a typed gate diagnostic. Resolution and internal failures
use a failure outcome, `DISPATCH_FAILED` or `NOT_ATTEMPTED`, no executor result,
and a safe diagnostic. Terminal executor statuses require exact descriptor,
request, and result identity.

## Registry boundary

Part 2 provides one immutable, descriptor-only registry snapshot. Construction
sorts descriptors canonically and rejects duplicate executor identifiers and
duplicate descriptor fingerprints. It has no registration, replacement, or
removal API and owns no executor instances. Deliberately overlapping, otherwise
valid descriptors remain visible so resolution can fail explicitly as
`AMBIGUOUS_MATCH`; the registry never selects one by ordering or priority.

Lookup requires exact enum equality for `plan.required_capability` and explicit
membership of `plan.plan_type` in `descriptor.supported_plan_types`. Descriptor
validation also enforces the frozen M6C.6A plan-to-capability mapping. There is
no aliasing, fuzzy matching, name inference, fallback, global state, plugin or
entry-point discovery, filesystem scanning, environment lookup, or network
discovery.

Registry resolves. Dispatcher dispatches. Executor executes.

## Dispatch eligibility

`DispatchEligibilityEvaluator` is the single eligibility authority. It consumes
the exact planning result, dispatch policy, and execution context and returns an
immutable typed result. Completed automatic plans are eligible only when policy
permits automatic dispatch and authorization is `NOT_REQUIRED`. Human-gated
plans require enabled human-gated requests and explicit `GRANTED`
authorization. A missing grant is `AUTHORIZATION_REQUIRED`; a denial or policy
prohibition is `POLICY_BLOCKED`.

Valid non-executable plans and `NONE` capability are `NOT_EXECUTABLE`, not
operational corruption. Invalid plans, contexts, policies, and fingerprint
failures are distinct fail-closed states. Eligibility performs no registry
lookup and no invocation.

## Capability resolution

`CapabilityResolver` is the single resolution authority. It validates the
immutable registry and authoritative planning result, then applies the exact
capability and explicit plan compatibility rules once. Cardinality is reported
as `ZERO_MATCH`, `EXACT_MATCH`, or `AMBIGUOUS_MATCH`; only `EXACT_MATCH`
preserves a selected descriptor for a future dispatcher. `CAPABILITY_NONE`,
invalid registry, and integrity failures are terminal resolution diagnostics.
No first/last/alphabetical/priority fallback exists.

Eligibility and resolution results preserve the original planning-result
object. Exact resolution also preserves the descriptor object from the
registry. Their fingerprints include only the approved version and lineage
fields. Registry, eligibility, and resolution reports are immutable safe
projections with deterministic JSON serialization and contain no executor
instances or editorial/provider content.

## Identity and fingerprints

Exact identity paths include:

```text
dispatch_request.planning_result is planning_result
executor_request.planning_result is planning_result
executor_request.plan is planning_result.plan
executor_result.request is executor_request
dispatch_result.request is dispatch_request
dispatch_result.executor_request is executor_request
dispatch_result.executor_result is executor_result
```

The deterministic lineage is planning-result fingerprint → policy/context
fingerprints → dispatch-request fingerprint → descriptor fingerprint →
executor-request fingerprint → executor-result fingerprint → dispatch-result
fingerprint. Fingerprints use the repository canonical UTF-8 SHA-256 mechanism
and safe identity fields only. They exclude object identity, clocks, randomness,
environment state, registry contents, callable instances, reports, raw content,
and exceptions. They are lineage/integrity identifiers, not signatures.

## Validation, diagnostics, and unknown values

Public pure validators revalidate policy, context, descriptor, dispatch request,
executor request/result, diagnostic, and dispatch result contracts. Frozen
M6C.6A validation is reused for nested planning results. Validators perform no
resolution, planning, dispatch, invocation, I/O, network, database, registry, or
fingerprint repair.

Unknown versions, outcomes, statuses, authorization states, diagnostic codes,
capabilities, and plan types fail closed. They never default to `NONE`,
`NON_EXECUTABLE`, `NOT_DISPATCHABLE`, or an internal-failure-looking valid
result.

Diagnostics use typed codes/categories, concise safe messages, and an optional
canonical tuple of approved fingerprint references. They cannot contain raw
exceptions, paths, credentials, tokens, email addresses, prompts, findings, or
provider content.

## Safe reports and serialization

The safe report exposes only operational/status taxonomies, plan taxonomy,
authorization, safe executor identity/version, executor outcome/status,
diagnostic code, fingerprints, and completeness indicators. Result validation
requires the report to agree with the authoritative nested contracts.

Serialization is deterministic UTF-8 JSON with stable keys, enum values, and
explicit nulls. Rendering is deterministic and projection-only. Reports and
serialized reports are never authoritative executor inputs.

## Part 2 scope and future boundary

Part 2 implements the immutable capability registry, dispatch-eligibility
evaluator, exact capability/plan resolver, typed diagnostics, and safe reports.
It ends after resolution. There is no dispatcher, executor binding, lifecycle,
retry, service, infrastructure adapter, or executor invocation. A future Part 3
dispatcher may consume only an eligible result and one exact resolution; it
must not change or reconstruct the authoritative plan.

## Part 3 authoritative runtime

The permanent ownership statement is:

```text
M6C.5F decides.
M6C.6A plans.
M6C.6B dispatches.
M6C.6C+ execute.
```

`CorrectiveActionExecutionDispatchService` owns the public validation and
lifecycle boundary. `CorrectiveActionExecutionDispatcher` is the sole owner of
runtime dispatch semantics: it invokes the authoritative eligibility evaluator
once, invokes the authoritative resolver once only for eligible plans, resolves
one exact binding, constructs one executor request, and invokes at most one
executor at most once. The service sanitizes unexpected dispatcher failures.

The dispatcher never changes the authoritative execution plan. It preserves
the original planning-result and plan objects through the dispatch request,
executor request, executor result, dispatch result, and workflow result.

## Executor bindings

`CorrectiveActionExecutorBinding` links one exact registry descriptor object to
one executor implementing the frozen protocol. The executor must advertise that
same descriptor object. `CorrectiveActionExecutorBindings` is an immutable,
canonically ordered runtime snapshot whose descriptor set must exactly equal
the immutable registry descriptor set. Duplicate IDs, descriptors, missing
bindings, foreign bindings, and fingerprint changes fail closed. Bindings have
no registration or discovery API and their fingerprint excludes executor
object identity.

## Runtime branch semantics and call counts

- Automatic execution requires an eligible plan, policy permission, an exact
  descriptor and binding, and descriptor support for automatic invocation.
- A human-gated plan never reaches an executor without explicit valid
  `GRANTED` authorization.
- A non-executable plan never reaches capability resolution or an executor.
- A zero match and an ambiguous executor match are dispatch failures. An
  ambiguous match is never treated as a selection policy.
- A valid completed executor result becomes `COMPLETED + EXECUTOR_COMPLETED`.
- A valid executor-declared failure becomes `COMPLETED + EXECUTOR_FAILED`; it
  remains distinct from dispatcher operational failure.
- A malformed result or executor exception becomes
  `FAILED_EXECUTOR_CONTRACT + DISPATCH_FAILED`, with no accepted executor result
  and only a fixed safe diagnostic.

Early request validation invokes eligibility, resolution, and execution zero
times. A valid evaluated request invokes eligibility exactly once. Only an
eligible request invokes resolution, exactly once. Only one exact resolution
and binding can invoke an executor, exactly once. There is no retry, fallback,
recursive dispatch, or secondary executor.

## Lifecycle

The immutable lifecycle phases are `PREPARED`, `VALIDATING`,
`EVALUATING_ELIGIBILITY`, `RESOLVING`, `BUILDING_EXECUTOR_REQUEST`,
`INVOKING_EXECUTOR`, `VALIDATING_EXECUTOR_RESULT`, `DISPATCHED`, `FINALIZED`,
and `FAILED`. One transition function owns the allowed graph. Each accepted
transition returns a new state, increments revision once, appends one safe
fingerprinted event, and recomputes the state fingerprint. `FINALIZED` and
`FAILED` are terminal; self-transitions, skipped phases, and transitions from a
terminal state are rejected.

Lifecycle events contain only phase, sequence, revision, request fingerprint,
and event fingerprint. They contain no timestamps, content, paths, exceptions,
credentials, executor instances, or arbitrary metadata.

## Production composition

The workflow layer consumes an already-created M6C.6A planning result. It does
not invoke planning or editorial decision-making. Its immutable request combines
that exact result with dispatch policy and execution context. The workflow
builds one dispatch request and invokes the explicitly supplied dispatch service
once. Its result preserves the workflow request, dispatch request, dispatch
result, lifecycle state, executor request, and executor result identities.

The standard builder requires an explicit complete binding snapshot. It does
not discover executors or consult files, environment variables, entry points,
network services, databases, queues, or global registries.

Safe runtime reports are projections and are never executor inputs. They expose
only workflow/dispatch outcomes, executor identifier/outcome, terminal lifecycle
phase/revision, and lineage fingerprints. JSON serialization is deterministic,
versioned, stable-key ordered, UTF-8 safe, and uses explicit nulls.

## Operational boundary and Part 4

Part 3 contains no draft revision, regeneration, manual-review routing,
publication, persistence, notification, queueing, workflow continuation,
networking, or capability-specific production executor. Future M6C.6C
executors must implement the frozen executor protocol, consume the immutable
executor request, preserve all plan lineage, and return a validated generic or
approved typed result. Part 4 will audit the complete M6C.6B boundary and freeze
readiness; it must not add capability-specific execution.

## Part 4 audit and freeze posture

The final audit verifies a single eligibility evaluator, capability resolver,
and dispatcher; exact planning and descriptor identity; immutable registry and
binding snapshots; at-most-once dependency calls; terminal lifecycle behavior;
fail-closed unknown values and fingerprints; safe report consistency; and the
absence of retries, discovery, reverse M6C.6A dependencies, infrastructure
adapters, and production capability-specific executors.

Binding validation is deliberately repeated at the public service boundary.
It rechecks the executor's currently advertised descriptor and requires every
binding descriptor to be the exact descriptor object in the frozen registry.
This prevents descriptor substitution after initial construction. Workflow
validation likewise revalidates the nested planning result, dispatch policy,
execution context, dispatch request/result, and lifecycle rather than trusting
only the workflow-level fingerprint.

Accepted scope limitations are: no production revision, regeneration, or
manual-review executor; no capability-specific output contract; no retry or
asynchronous orchestration; no executor discovery; no persistence, publication,
queue, network, notification, or CLI integration; and no external authorization
provider. These are future executor/integration responsibilities and do not
weaken the generic dispatch boundary.
