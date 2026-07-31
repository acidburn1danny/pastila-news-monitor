# M6C.5F Editorial Corrective-Action Decision — Part 1

M6C.5F is a deterministic decision boundary. It consumes one authoritative, frozen
M6C.5E `EditorialReviewIntegrationResult` and describes what a later application layer
should request next. It never executes that action.

```text
Controlled generation and editorial review
    -> M6C.5E EditorialReviewIntegrationResult
        -> M6C.5F CorrectiveActionDecisionResult
            -> later workflow milestone (not implemented)
```

## Ownership boundaries

M6C.5F owns its action, reason, operational outcome, policy, completeness,
diagnostics, trace, safe report, and deterministic identities. M6C.5A–E retain
authority over generation, draft construction, findings, aggregation, editorial
approval, pipeline execution, orchestration, and integration status. The original
M6C.5E result is retained unchanged as a nested authoritative object.

M6C.5F reads only public M6C.5E statuses, completeness, authoritative editorial status
when available, presence of nested results, and fingerprints. It does not inspect
finding codes, severities, evidence, recommendations, locations, reviewer results, or
draft prose. It does not invoke M6C.5E, generation, M6C.5D, or M6C.5A–C.

An operational outcome and requested action are separate. A completed decision may
request regeneration or halt. Conversely, invalid decision input produces an
operational failure with no fabricated action.

`CONTINUE_WORKFLOW` means only that M6C.5F found no editorial corrective action. It
does not authorize publication or assert legal, scheduling, asset, or distribution
readiness. `REQUEST_MANUAL_REVIEW` does not assign a reviewer or dispatch a task.
`REQUEST_REVISION` does not choose or rewrite components. `REQUEST_REGENERATION` does
not call generation. `HALT_WORKFLOW` is a descriptive request to stop automatic
continuation, not process termination or deletion.

## Public contracts

- `CorrectiveAction`
- `CorrectiveActionDecisionReason`
- `CorrectiveActionDecisionOutcome`
- `CorrectiveActionDecisionPolicy`
- `CorrectiveActionDecisionRequest`
- `CorrectiveActionDecision`
- `CorrectiveActionDecisionResult`
- `CorrectiveActionDecisionCompleteness`
- `CorrectiveActionDecisionDiagnostic`
- `CorrectiveActionDecisionTraceEvent`
- `CorrectiveActionDecisionReport`
- `CorrectiveActionDecisionService`
- `build_standard_corrective_action_decision_policy()`
- `decide_corrective_action()`
- safe JSON and text report renderers

All public contracts are frozen. Collections use canonical tuples, trace order is
explicit, and SHA-256 fingerprints use the repository canonical serializer. Identity
lineage is:

```text
M6C.5E result fingerprint
    -> M6C.5F request + policy fingerprints
        -> decision fingerprint
            -> completeness and report fingerprints
                -> final result fingerprint
```

Supplied corrupted identities are rejected, never repaired. Reports contain stable
IDs, versions, statuses, actions, reasons, diagnostic codes, completeness, and
fingerprints only. They do not copy nested prose, findings, evidence, prompts,
provider responses, exceptions, paths, credentials, or environment data. Evaluation
is synchronous, local, timestamp-free, network-free, and filesystem-independent.

## Conceptual mappings

- Approved editorial outcome → completed decision requesting `CONTINUE_WORKFLOW`; no
  publication occurs.
- Requires regeneration → completed decision requesting `REQUEST_REGENERATION`; no
  generation occurs.
- Upstream generation failure → completed decision requesting `HALT_WORKFLOW`; the
  upstream failure is not an M6C.5F execution failure.
- Operational completion without editorial outcome → policy-controlled manual review,
  halt, or no action.

## Frozen status inventory and decision matrix

M6C.5E exposes `completed`, `completed_without_review`,
`failed_during_generation`, `failed_before_review`, and `failed_during_review`.
M6C.5D exposes three completed variants and three explicit operational failures.
M6C.5A exposes `pending`, `approved`, `approved_with_warnings`,
`requires_regeneration`, `requires_human_review`, and `rejected`. It does not expose a
current `needs_revision` status, so `REQUEST_REVISION` remains a stable action
capability without an invented upstream mapping.

| M6C.5E / editorial state | Action | Reason | Policy |
| --- | --- | --- | --- |
| completed / approved | continue workflow | editorial approved | no |
| completed / approved with warnings | continue workflow | editorial approved | no |
| completed / requires regeneration | request regeneration | editorial regeneration required | no |
| completed / requires human review | request manual review | editorial human review required | no |
| completed / rejected | halt or manual review | editorial rejected | yes |
| completed / pending | halt or manual review | upstream incomplete | yes |
| completed / no editorial outcome | halt or manual review | editorial outcome absent | yes |
| completed without review | manual review, halt, or no action | review disabled | yes |
| failed during generation | halt | upstream generation failed | no |
| failed before review | halt | upstream draft invalid | no |
| failed during review | halt | upstream review failed | no |
| invalid or unsupported input | no decision | operational diagnostic | n/a |

The standard policy halts rejection, requests manual review for absent editorial
outcomes, and requests manual review when review was disabled. Policy fingerprints
change with every allowed override. Unknown versions or statuses fail closed.

The private runtime lifecycle is `prepared → validating → deciding → decided →
finalized`, with failure allowed from nonterminal execution states. Every accepted
transition returns a new frozen state, increments revision exactly once, and appends
one fingerprinted trace event. `finalized` and `failed` are terminal.

## Production composition

Part 3 provides `EditorialDecisionWorkflowService`. It invokes the injected M6C.5E
service once and, when an integration result exists, invokes M6C.5F once. It preserves
both authoritative results and returns a safe workflow report. A valid upstream
generation or review failure can still yield a completed workflow containing a halt
decision. Invocation exceptions are sanitized and stop downstream execution.

The composition builder requires an explicit controlled generator because generation
provider construction remains outside M6C.5F. Construction itself performs no work.
No CLI was added because the repository has no existing command that constructs the
frozen generation blueprints required by this workflow.

Part 4 freeze auditing covers the completed contracts, mapping, composition, privacy,
determinism, frozen regression baseline, and quality gates.

## Unsupported in Part 1

Draft rewriting, component repair, regeneration, generation or review retries,
publication or authorization, scheduling, persistence, resume, human-review
execution, notifications, queue dispatch, batch or asynchronous decisions, metrics,
telemetry, and workflow continuation are not implemented.
