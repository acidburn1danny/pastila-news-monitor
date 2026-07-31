# M6C Editorial Pipeline Architecture Checkpoint

This document is the authoritative architecture checkpoint for the implemented M6C
editorial pipeline. Milestone-specific documents remain authoritative for internal
rules and detailed matrices; this checkpoint defines ownership, public boundaries,
call direction, immutable lineage, and the future M6C.6 entry point.

## System overview

The implemented pipeline generates one controlled episode draft, reviews it through
the editorial QA stack, classifies the resulting authoritative integration state, and
returns a requested next action. It does not execute that action.

```text
ControlledGenerator
    -> ControlledGenerationResult containing EpisodeDraft
        -> EditorialReviewIntegrationService (M6C.5E)
            -> EditorialReviewOrchestrator (M6C.5D)
            -> EditorialReviewIntegrationResult
                -> CorrectiveActionDecisionService (M6C.5F)
                -> CorrectiveActionDecisionResult
                    -> future M6C.6 execution boundary
```

`EditorialDecisionWorkflowService` is the application composition that invokes
M6C.5E and then M6C.5F. M6C.5F decides; future M6C.6 may execute an authorized action.

## Runtime call flow

Solid arrows below are direct calls. Indentation shows calls nested inside the owning
service.

```text
Application
  -> EditorialDecisionWorkflowService.execute()
       -> EditorialReviewIntegrationService.execute()             [M6C.5E]
            -> ControlledGenerator.generate()
            -> EditorialReviewOrchestrator.review()                [M6C.5D]
                 -> DeterministicReviewerPipeline.execute()        [M6C.5C]
                      -> DeterministicRulesReviewer.review()        [M6C.5B]
                 -> EditorialQAOrchestrator / aggregation / policy [M6C.5A]
       -> CorrectiveActionDecisionService.decide()                 [M6C.5F]
  <- EditorialDecisionWorkflowResult
```

The standalone M6C.5F service never invokes M6C.5E or any generation/review layer.
Only the Part 3 workflow composition owns the M6C.5E-then-M6C.5F sequence.

## Authoritative object lineage

```text
ControlledGenerationResult
  contains ──> EpisodeDraft
       │             │
       │             └── same draft object passed into M6C.5D request
       └── same generation result retained by EditorialReviewIntegrationResult

EditorialReviewOrchestrationResult (M6C.5D)
  retained unchanged ──> EditorialReviewIntegrationResult (M6C.5E)
                              │
                              └── retained unchanged
                                  by CorrectiveActionDecisionResult (M6C.5F)
                                      │
                                      └── retained unchanged with the decision
                                          by EditorialDecisionWorkflowResult

Authoritative objects ──> safe report projections ──> JSON/text renderings
                         (projections never replace authoritative objects)
```

The intended identity relationships are:

- `decision_result.integration_result is integration_result`;
- `workflow_result.integration_result is integration_result`;
- `workflow_result.decision_result is decision_result`;
- the M6C.5E result retains the original `ControlledGenerationResult`, its
  `EpisodeDraft`, and the returned M6C.5D result without rebuilding their content.

## Responsibilities and frozen ownership

| Subsystem | Owner | Primary responsibility | Authoritative input | Authoritative output | May invoke | Must not invoke | Frozen |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Controlled generation | `editor/generation` | Controlled component generation and draft assembly | Typed Scout, blueprint, flow, voice, and generation inputs | `ControlledGenerationResult` containing `EpisodeDraft` | Configured language-model provider and deterministic assembly | Editorial QA, action decisions, publication | Yes |
| M6C.5A editorial QA | `editor/qa` | Findings aggregation and authoritative approval decision | Frozen draft, manifest, accepted review results | `EditorialQAResult` | Aggregator and approval policy engine | Generation, correction execution, publication | Yes |
| M6C.5B reviewer | `editor/qa/rules` | Deterministic objective review rules | Frozen `EpisodeDraft` review request | Immutable editorial review result/findings | Registered deterministic rules | Generator, action mapping, publication | Yes |
| M6C.5C pipeline | `editor/qa/pipeline` | Reviewer selection, scheduling, isolation, accepted-result collection | Frozen draft, manifest, pipeline policy | `ReviewerPipelineResult` | Registered reviewer interfaces | Finding reinterpretation, generation, corrective execution | Yes |
| M6C.5D orchestration | `editor/qa/orchestration` | Manifest resolution, pipeline invocation, handoff, M6C.5A execution | `EditorialReviewOrchestrationRequest` | `EditorialReviewOrchestrationResult` | M6C.5C and M6C.5A | Generation, action mapping, publication | Yes |
| M6C.5E integration | `editor/qa/integration` | One generation attempt followed by at most one M6C.5D review | `EditorialReviewIntegrationRequest` | `EditorialReviewIntegrationResult` | `ControlledGenerator`, M6C.5D public API | Findings interpretation, retry, regeneration, publication | Yes |
| M6C.5F decision | `editor/qa/corrective_action` | Validate and classify M6C.5E result; request one next action | `CorrectiveActionDecisionRequest` containing the original `EditorialReviewIntegrationResult` | `CorrectiveActionDecisionResult` | No upstream service in standalone mode | Findings, generation, review, action execution, persistence, publication | Yes |
| M6C.5F composition | `editor/qa/corrective_action/composition.py` | Invoke M6C.5E once, then M6C.5F once, and preserve both results | `EditorialDecisionWorkflowRequest` | `EditorialDecisionWorkflowResult` | M6C.5E and M6C.5F public services | Corrective execution, publication, persistence, routing | Yes |
| Future M6C.6 | Not implemented | Execute an already frozen action through authorized executors | `CorrectiveActionDecisionResult`, directly or unchanged inside an immutable execution request | Future execution result | Future authorized executor interfaces | Re-deciding editorial state, findings aggregation, provider construction, publication authorization | No; boundary only |

Frozen public semantics may be consumed by later milestones but may not be changed.
Compatibility changes require a separately approved milestone.

## Public contract inventory

| Contract | Defining package | Producer | Consumer | Immutable | Fingerprinted | Role |
| --- | --- | --- | --- | --- | --- | --- |
| `EpisodeDraft` | `editor.generation.models` | `ControlledGenerator`/`DraftAssembler` | M6C.5D through M6C.5E | Yes | No native field; canonical fingerprint derived by integration/review | Authoritative content |
| `ControlledGenerationResult` | `editor.generation.models` | `ControlledGenerator.generate()` | M6C.5E | Yes | No native field; M6C.5E safe report derives `generation_result_fingerprint` | Authoritative generation result |
| `EditorialReviewOrchestrationResult` | `editor.qa.orchestration` | `EditorialReviewOrchestrator.review()` | M6C.5E | Yes | `result_fingerprint` | Authoritative review orchestration result |
| `EditorialReviewIntegrationRequest` | `editor.qa.integration` | Application/composition | M6C.5E service | Yes | `request_fingerprint` property | Authoritative integration request |
| `EditorialReviewIntegrationResult` | `editor.qa.integration` | M6C.5E | M6C.5F | Yes | `result_fingerprint` | Authoritative generation-review result |
| `CorrectiveActionDecisionPolicy` | `editor.qa.corrective_action` | Standard policy builder/application | M6C.5F evaluator | Yes | `policy_fingerprint` | Authoritative ambiguous-mapping policy |
| `CorrectiveActionDecisionRequest` | same | Application/composition | `CorrectiveActionDecisionService` | Yes | `request_fingerprint` | Authoritative decision input |
| `CorrectiveActionDecision` | same | M6C.5F evaluator/service | Later execution boundary | Yes | `decision_fingerprint` | Authoritative requested action and reason |
| `CorrectiveActionDecisionResult` | same | M6C.5F service | Workflow composition/future M6C.6 | Yes | `result_fingerprint` | Authoritative decision outcome retaining M6C.5E result |
| `EditorialDecisionWorkflowRequest` | `corrective_action.composition` | Application | Workflow service | Yes | `request_fingerprint` | Authoritative composition request |
| `EditorialDecisionWorkflowResult` | same | Workflow service | Application | Yes | `result_fingerprint` | Authoritative composed result |
| Integration, decision, and workflow reports | respective packages | Owning service | Renderer/serializer/application diagnostics | Yes | `report_fingerprint` | Safe projections only |

Every subsystem consumes the authoritative result of the immediately preceding owner.
M6C.5F accepts the complete `EditorialReviewIntegrationResult`, never independently
supplied generation status, review status, editorial status, findings, or draft
fingerprint. Future M6C.6 must likewise consume the complete
`CorrectiveActionDecisionResult`, not reconstruct a decision from editorial state.

## Fingerprint lineage

The actual deterministic lineage is:

```text
canonical EpisodeDraft fingerprint (derived; no native EpisodeDraft field)
  + canonical ControlledGenerationResult hash in M6C.5E safe report
  + EditorialReviewOrchestrationResult.result_fingerprint
      -> EditorialReviewIntegrationResult.result_fingerprint
          + CorrectiveActionDecisionPolicy.policy_fingerprint
              -> CorrectiveActionDecisionRequest.request_fingerprint
                  -> CorrectiveActionDecision.decision_fingerprint
                      -> CorrectiveActionDecisionResult.result_fingerprint
                          -> EditorialDecisionWorkflowRequest.request_fingerprint
                              -> EditorialDecisionWorkflowResult.result_fingerprint
```

Intermediate diagnostics, trace events, completeness objects, descriptors, and safe
reports also have validated fingerprints. These SHA-256 fingerprints establish
deterministic identity and lineage; they are not signatures and do not establish
authenticity against a malicious actor.

## Decision versus execution

M6C.5F decides. Future M6C.6 may execute.

- `CONTINUE_WORKFLOW`: no editorial corrective action is requested. M6C.5F neither
  publishes nor resumes another workflow.
- `REQUEST_REVISION`: a future executor may revise the existing draft. M6C.5F does
  not inspect findings, select components, or modify text.
- `REQUEST_REGENERATION`: a future executor may invoke an authorized regeneration
  path. M6C.5F never invokes generation.
- `REQUEST_MANUAL_REVIEW`: a future executor may create or route a human task.
  M6C.5F performs no routing or assignment.
- `HALT_WORKFLOW`: a future workflow owner should not continue automatically.
  M6C.5F does not terminate a process or delete data.
- `NO_ACTION`: an explicit policy-selected neutral result, currently available for
  disabled review. It is never a generic failure fallback.

Operational outcomes remain separate. For example, M6C.5F may return
`COMPLETED + HALT_WORKFLOW` after correctly interpreting a valid upstream generation
failure. `FAILED_INVALID_INPUT` instead has no decision and no action.

## Authoritative decision policy

Fixed mappings use actual frozen statuses:

- `approved` and `approved_with_warnings` → `CONTINUE_WORKFLOW`;
- `requires_regeneration` → `REQUEST_REGENERATION`;
- `requires_human_review` → `REQUEST_MANUAL_REVIEW`;
- valid generation, pre-review, and review failures → `HALT_WORKFLOW`.

Only ambiguous mappings use `CorrectiveActionDecisionPolicy`:

- `rejected_action`: halt or request manual review;
- `missing_editorial_action`: halt or request manual review;
- `review_disabled_action`: halt, request manual review, or no action.

The frozen editorial vocabulary contains `pending`, `approved`,
`approved_with_warnings`, `requires_regeneration`, `requires_human_review`, and
`rejected`. It contains no needs-revision state. Therefore `REQUEST_REVISION` remains
a stable capability but has no invented current mapping. Unknown versions or statuses
fail closed.

M6C.5F does not inspect findings, severities, evidence, recommendations, component
locations, or reviewer internals. Those remain inside editorial review ownership.

## Call-count and composition guarantees

`EditorialDecisionWorkflowService` owns only this sequence:

1. invoke `EditorialReviewIntegrationService.execute()` at most once;
2. receive its authoritative result;
3. invoke `CorrectiveActionDecisionService.decide()` at most once;
4. preserve both results and construct a safe workflow result.

Through M6C.5E, `ControlledGenerator.generate()` and M6C.5D `review()` are each called
at most once. Later stages may be called zero times after an early invocation failure.
There are no retries, recursion, hidden continuation, or action execution.

## Reporting boundary

Authoritative results retain full nested objects. Safe reports, canonical JSON
serializers, and fixed-order text renderers expose only statuses, action, reason,
diagnostic codes, completeness, versions, and fingerprints. They do not expose draft
prose, findings, evidence, recommendations, prompts, provider responses, raw
exceptions, credentials, or paths. Reports are projections, never substitutes for
the authoritative results.

## Future M6C.6 boundary

M6C.6 should accept `CorrectiveActionDecisionResult` directly or an immutable
execution request containing that exact result unchanged. It may inspect the decision
operational outcome, requested action, reason, policy and lineage fingerprints, and
authoritative nested references required by an authorized executor.

M6C.6 may own execution requests, execution policy, action dispatch, authorized
executor interfaces, execution outcomes, diagnostics, trace, and reporting. It must
not re-evaluate editorial outcomes, remap actions, aggregate findings, construct
generation providers, authorize publication, publish, or introduce unbounded retries.

Proposed roadmap—not frozen implementation:

1. M6C.6A — Corrective-Action Execution Contracts
2. M6C.6B — Execution Planning and Dispatch Semantics
3. M6C.6C — Regeneration Execution Boundary
4. M6C.6D — Manual-Review Routing Boundary
5. M6C.6E — Execution Workflow Composition
6. M6C.6F — Final Audit and Freeze

## Current limitations and unsupported capabilities

Accepted non-defect limitations:

1. Workflow construction requires an explicit generator because no
   provider-independent standard generator builder exists.
2. The frozen editorial vocabulary has no needs-revision status, so no revision
   mapping was invented.
3. No CLI can construct the complete frozen generation-blueprint chain without
   becoming a second workflow owner; therefore no workflow CLI composition point
   exists.

The checkpointed pipeline intentionally lacks revision execution, regeneration
execution, manual-review task creation, publication or publication authorization,
persistence, workflow resume, notifications, queue integration, batch or asynchronous
execution, retry orchestration, and CLI workflow composition.

## Architectural invariants

1. Every subsystem has one authoritative owner.
2. Each subsystem consumes authoritative public results rather than reconstructed
   state.
3. Frozen upstream semantics are not reinterpreted downstream.
4. M6C.5F decides but never executes.
5. Operational failure and requested action are separate.
6. Valid upstream failures may produce successful halt decisions.
7. Invalid contracts never fabricate actions.
8. Unknown statuses fail closed.
9. Findings remain inside editorial-review ownership.
10. Object identity and fingerprint lineage are preserved.
11. Reports are safe projections, not authoritative replacements.
12. Composition invokes each owned stage at most once.
13. No retries or hidden continuation exist.
14. `CONTINUE_WORKFLOW` does not authorize publication.
15. Future M6C.6 must execute the frozen decision rather than re-decide it.

## Repository reconciliation

All documented packages, types, service methods, builders, enum values, report fields,
and call directions were checked against the repository. The only planning-level
assumption requiring correction was the notion of a native generation-result
fingerprint: neither `ControlledGenerationResult` nor `EpisodeDraft` defines one.
The implemented integration derives canonical fingerprints without changing those
frozen contracts. No production contradiction or behavior change was required.
