# M6C.6A — Corrective Action Execution Plan

## Purpose and architecture

M6C.6A defines the immutable boundary between the frozen editorial decision and
future corrective-action executors:

```text
CorrectiveActionDecisionResult
        -> execution planning
CorrectiveActionExecutionPlanResult
        -> future authorized execution dispatch
```

M6C.5F decides. M6C.6A plans. Future M6C.6 executors execute. The authoritative
input is the complete frozen `CorrectiveActionDecisionResult`; it is retained by
object identity in both request and plan. The authoritative output is
`CorrectiveActionExecutionPlanResult`. A safe report is only a projection and
must never replace that result for execution consumers.

This boundary follows the conclusions in
`m6c-editorial-pipeline-architecture-checkpoint.md` and consumes the public
contracts documented by `m6c5f-editorial-corrective-action-decision.md`.

## Ownership and non-responsibilities

The subsystem owns execution planning only. It does not reconsider editorial
status, findings, evidence, or recommendations. It does not invoke M6C.5F,
generation, review, persistence, queues, notification, publication, dispatch,
or an executor.

The execution plan is not evidence that execution occurred. `CONTINUE_WORKFLOW`
does not authorize publication. `NO_CORRECTIVE_EXECUTION` does not resume or
publish another workflow. `BLOCK_AUTOMATIC_CONTINUATION` does not terminate
infrastructure.

## Plan, mode, and capability taxonomies

Plan types are `NO_CORRECTIVE_EXECUTION`, `REVISE_DRAFT`, `REGENERATE_DRAFT`,
`CREATE_MANUAL_REVIEW_REQUEST`, and `BLOCK_AUTOMATIC_CONTINUATION`. The original
M6C.5F action and reason remain present even where two actions eventually share
a plan type.

Execution modes are `AUTOMATIC`, `HUMAN_GATED`, and `NON_EXECUTABLE`. They state
authorization requirements, not execution state. Capabilities are `NONE`,
`DRAFT_REVISION`, `DRAFT_REGENERATION`, `MANUAL_REVIEW_ROUTING`, and
`WORKFLOW_CONTINUATION_BLOCK`. A capability is a provider-independent
requirement declaration, not an executor or credential.

## Policy boundary

The immutable policy controls only valid execution characteristics: whether
regeneration may be automatic, whether revision or manual-review routing is
human-gated, whether halt is non-executable, and whether continue/no-action use
the same plan type. It contains no action mapping and therefore cannot remap or
erase the authoritative source action. Part 2 owns the mapping matrix.

Policy identity consists of `policy_id`, `policy_version`, and a deterministic
fingerprint. Unknown versions fail closed.

## Identity and fingerprint lineage

The request fingerprint binds the request contract version, upstream
decision-result fingerprint, and planning-policy fingerprint. The plan
fingerprint additionally binds source action and reason, plan type, mode,
capability, request and policy identities, and canonical typed preconditions.
The result fingerprint binds its operational outcome and present plan,
diagnostic, and report identities.

Canonical serialization uses stable field ordering, enum values, booleans,
optional values, and tuple ordering. It excludes timestamps, paths, reports from
plan identity, raw content, exceptions, environment state, and secrets. These
fingerprints are deterministic identity and lineage values. They are not
cryptographic signatures or trust proofs.

## Validation boundary

Pure validators fail closed for unsupported versions, corrupt fingerprints,
failed or missing upstream decisions, inconsistent authorization flags,
incompatible plan type/mode/capability combinations, lost object identity, and
result/report contradictions. They validate the public M6C.5F contract without
reconstructing its editorial classification or inspecting its findings.

Planning operational outcome and plan semantics are separate. A completed
planning result may validly contain `BLOCK_AUTOMATIC_CONTINUATION`. An invalid
request instead produces a failed operational outcome, no plan, and a safe
diagnostic. Invalid input never receives a fallback plan.

## Safe reporting

The report exposes outcome, plan taxonomy, authorization flags, source action
and reason, safe diagnostic code, contract identities, fingerprints, and
completeness indicators. It excludes draft/article content, findings, evidence,
recommendations, prompts, provider data, exceptions, credentials, and paths.

## Part 2 authoritative evaluator

`CorrectiveActionExecutionPlanEvaluator` is the only production owner of the
action-to-plan mapping:

| Authoritative M6C.5F action | Plan type |
| --- | --- |
| `CONTINUE_WORKFLOW` | `NO_CORRECTIVE_EXECUTION` |
| `REQUEST_REVISION` | `REVISE_DRAFT` |
| `REQUEST_REGENERATION` | `REGENERATE_DRAFT` |
| `REQUEST_MANUAL_REVIEW` | `CREATE_MANUAL_REVIEW_REQUEST` |
| `HALT_WORKFLOW` | `BLOCK_AUTOMATIC_CONTINUATION` |
| `NO_ACTION` | `NO_CORRECTIVE_EXECUTION` |

The mapping is fixed. Policy controls only whether revision, regeneration, or
manual-review request creation is automatic or human-gated. Revision is
human-gated when `revision_requires_human_authorization` is true. Regeneration
is automatic only when `regeneration_automatic_allowed` is true. Manual-review
request creation is human-gated when
`manual_review_requires_human_authorization` is true. Policies that make halt
executable or split the fixed continue/no-action plan type fail before evaluator
invocation.

## Execution characteristics and preconditions

| Plan type | Allowed mode | Capability |
| --- | --- | --- |
| `NO_CORRECTIVE_EXECUTION` | `NON_EXECUTABLE` | `NONE` |
| `REVISE_DRAFT` | `AUTOMATIC`, `HUMAN_GATED` | `DRAFT_REVISION` |
| `REGENERATE_DRAFT` | `AUTOMATIC`, `HUMAN_GATED` | `DRAFT_REGENERATION` |
| `CREATE_MANUAL_REVIEW_REQUEST` | `AUTOMATIC`, `HUMAN_GATED` | `MANUAL_REVIEW_ROUTING` |
| `BLOCK_AUTOMATIC_CONTINUATION` | `NON_EXECUTABLE` | `WORKFLOW_CONTINUATION_BLOCK` |

`WORKFLOW_CONTINUATION_BLOCK` is a declarative requirement, not an executable
infrastructure operation. A revision declares original-draft and executor
capability prerequisites. Regeneration declares generation-context and executor
capability prerequisites. Manual-review request creation declares destination
and executor capability prerequisites. Human authorization follows the selected
mode. Non-executable plans require no executor or external context.

No precondition proves that infrastructure or content is currently present. No
revision instructions, prompt, routing destination, queue payload, or workflow
token is invented.

## Service, lifecycle, and failures

`CorrectiveActionExecutionPlanService.plan()` accepts an already completed
planning request. It does not invoke M6C.5F. After validation and semantic policy
checks, it calls the evaluator exactly once, validates the returned plan, and
returns it by object identity. Early failures call the evaluator zero times;
there are no retries or fallback evaluators.

The immutable successful lifecycle is:

```text
PREPARED -> VALIDATING -> PLANNING -> PLANNED -> FINALIZED
```

Validation and planning may transition to `FAILED`. Each accepted transition
increments revision once and appends one deterministic fingerprinted event.
`FINALIZED` and `FAILED` are terminal. Rejected transitions return no new state
and cannot mutate the original.

Operational outcomes are `COMPLETED`, `FAILED_INVALID_INPUT`,
`FAILED_UNSUPPORTED_CONTRACT`, `FAILED_INTEGRITY_VALIDATION`,
`FAILED_POLICY_VALIDATION`, and `FAILED_INTERNAL`. Every failure has no plan and
a fixed safe diagnostic. A valid non-executable plan remains `COMPLETED`.
Invalid or failed upstream M6C.5F results never become halt or no-action plans.

Safe reports add the decision-result identity, final lifecycle phase, revision,
and state fingerprint. Safe result serialization adds only the result
fingerprint to that projection. It never serializes the authoritative upstream
object graph.

## Future boundaries

Part 2 creates the authoritative execution plan. Part 3 adds production
composition and public wiring. Neither part dispatches or executes the plan.
Future executor milestones may consume a successful plan but remain outside
this package and require explicit capability and authorization checks.

## Part 3 production composition

`CorrectiveActionPlanningWorkflowService` is the production composition layer:

```text
CorrectiveActionDecisionResult
        -> CorrectiveActionExecutionPlanService (exactly once)
        -> CorrectiveActionExecutionPlanResult
        -> CorrectiveActionPlanningWorkflowResult
```

The immutable workflow request contains the complete decision result and an
explicit planning policy. The workflow constructs one planning request without
reconstructing the upstream action or reason. Its result preserves the exact
decision result, planning result, and nested plan objects.

Planning failures are transported rather than reinterpreted. A workflow may be
`COMPLETED` while its planning result is `FAILED_POLICY_VALIDATION`,
`FAILED_INVALID_INPUT`, or another planning failure. A malformed workflow
request instead produces `FAILED_INVALID_INPUT` before the planning service is
called. An unexpected composition failure produces a generic safe
`FAILED_INTERNAL` diagnostic without exception content.

Dependencies are explicit. `CorrectiveActionPlanningWorkflowService` receives
its planning service through construction; there are no global services,
registries, implicit discovery, or retries. The standard builder constructs one
evaluator, one planning service, and one workflow service. The
`generate_execution_plan` helper only builds the request and delegates to that
workflow.

The workflow report contains only workflow/planning statuses, plan taxonomy,
source action and reason, safe diagnostic codes, versions, and fingerprints.
Deterministic serialization operates on this safe projection and never on the
nested authoritative object graph.

M6C.6A produces an execution plan. It does not execute the plan. Composition
does not revise, regenerate, route, enqueue, persist, publish, notify, resume, or
dispatch. Future M6C.6B integration must consume the authoritative planning
result and introduce separately authorized executor contracts without changing
this ownership boundary.

## Part 4 freeze audit

The freeze audit verified the exhaustive action mapping, policy boundaries,
mode/capability matrices, immutable lifecycle, call counts, object identity,
fingerprint lineage, safe projections, dependency direction, and absence of an
execution path. It tightened three defensive boundaries without changing the
production mapping: plan preconditions must equal the canonical typed matrix;
planning reports must agree with their authoritative plan; and workflow reports
must agree with their authoritative planning result. Workflow diagnostic text
also rejects representative credential and path content.

The authoritative lineage is:

```text
CorrectiveActionDecisionResult.result_fingerprint
  -> CorrectiveActionExecutionPlanPolicy.policy_fingerprint
  -> CorrectiveActionExecutionPlanRequest.request_fingerprint
  -> CorrectiveActionExecutionPlan.plan_fingerprint
  -> lifecycle event/state fingerprints
  -> CorrectiveActionExecutionPlanResult.result_fingerprint
  -> CorrectiveActionPlanningWorkflowRequest.request_fingerprint
  -> CorrectiveActionPlanningWorkflowResult.result_fingerprint
```

Fingerprints are deterministic lineage identities, not signatures or trust
proofs. Reports and serialized reports remain projections; future execution
must consume the authoritative result and plan.

Accepted scope limitations are intentional: no executor or dispatch registry
exists; there are no corrective payload contracts, regeneration executor,
manual-review destination contract, publication integration, or CLI composition
for this workflow. `REQUEST_REVISION` is structurally supported, although the
current frozen M6C.5F evaluator has no editorial-status branch that emits it.

Future M6C.6B must dispatch the authoritative frozen plan rather than
reinterpret the source decision. It may validate the completed planning
outcome, plan presence, execution mode, capability, authorization requirements,
typed preconditions, source action/reason, and lineage. It must not remap the
action, inspect findings, or treat a safe report as authoritative.
