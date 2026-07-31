# M6C.5A — Editorial QA Architecture

M6C.5A introduces the private contracts and deterministic orchestration boundary
between an immutable generated `EpisodeDraft` and a QA approval decision. It does
not judge editorial quality. It defines how future editorial judgments are
represented, structurally validated, aggregated, traced, and converted into a
minimal deterministic decision.

## Package and responsibilities

`pastila_scout.editor.qa` contains immutable models, a review manifest, execution
state, reviewer protocol/test doubles, result validation, structural aggregation,
minimal approval policy, and orchestration. QA receives the existing draft and never
mutates or rewrites it, invokes generation, retrieves external data, or performs
regeneration.

Issue families provide stable broad taxonomy while detailed rule IDs remain
extensible strings. Severity (`INFO`, `WARNING`, `ERROR`, `CRITICAL`) is ordered and
separate from confidence (`LOW`, `MEDIUM`, `HIGH`). Findings contain bounded evidence,
structured validated locations, deterministic IDs, severity-consistent blocking,
and recommendations that describe actions rather than replacement prose.

## Reviewer and execution contracts

The provider-independent `EditorialReviewer` receives one immutable
`EditorialReviewRequest` and returns an `EditorialReviewResult`. Capabilities are
declarations only. `NoOpEditorialReviewer` and `ScriptedEditorialReviewer` enable
fully offline architectural tests; neither aggregates, approves, rewrites, or
updates state.

The deterministic manifest sorts reviewer plans by stable identity/scope/target,
rejects duplicates, unknown dependencies, and cycles, then adds
`aggregate-findings` and `approval-decision` dependency items. `EditorialQAState`
contains only tuples, scalars, and frozen models. Accepted results and failures are
atomic new revisions; invalid or failed results never partially register findings.

## Aggregation, report, decision, and trace

Aggregation is structural: severity descending, draft component order, scope,
reviewer, issue code, then finding ID. It does not use NLP or merge semantically
similar findings. Reports expose deterministic counts, blocking IDs, coverage,
reviewer failures, and SHA-256 fingerprints tied to the exact draft and manifest.

The default approval policy is:

- missing required reviewer → `REQUIRES_HUMAN_REVIEW`;
- critical finding → `REJECTED`;
- blocking error → `REQUIRES_REGENERATION`;
- warnings or optional-reviewer failure → `APPROVED_WITH_WARNINGS`;
- no blocking concerns → `APPROVED`.

Required actions are declarations only; no regeneration request is executed.
Deterministic trace sequence numbers record manifest creation, separate reviewer
execution, validation/failure, state advancement, aggregation, and approval without
timestamps, stack traces, secrets, or draft duplication.

Fingerprints reuse the strict M6C.4D.1 recursive canonicalizer: stable UTF-8 JSON,
sorted mappings and sets, finite numbers, and explicit rejection of opaque objects.
Operational reproducibility covers manifests, requests, scripted results, finding
IDs/order, reports, decisions, state revisions, and trace ordering. Future external
reviewer wording is not guaranteed byte-identical.

## Explicit exclusions and roadmap

There are no substantive structure rules, voice-drift checks, humor or naturalness
scores, semantic fact checks, production LLM reviewers, web access, rewriting,
regeneration, generator calls, persistence, queues, caching, or UI.

Planned sequence:

1. M6C.5A — Editorial QA Architecture (this milestone)
2. M6C.5B — Deterministic Editorial Rules
3. M6C.5C — Reviewer Pipeline
4. M6C.5D — Corrective Actions and Component Regeneration
5. M6C.5E — Final Approval Engine

Later milestones are not implemented here.
