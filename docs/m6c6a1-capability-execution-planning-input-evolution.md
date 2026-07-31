# M6C.6A.1 Capability Execution Planning Input Evolution

## Gap and ownership

The frozen planning chain preserved the decision, plan policy, plan, and result,
but had no authorized revision policy, scope, or instructions. Source draft
identity already survived through decision → integration → generation result.
M6C.6A.1 introduces the missing typed input at planning-request construction; it
does not move revision interpretation into generic planning.

## Package architecture

The generic `execution_plan.planning_input` module owns only immutable metadata:
input type, corrective action, required capability, source lineage fingerprint,
authorization-policy fingerprint, version, and fingerprint. The generic v2
lineage envelopes validate compatibility and preserve identity without importing
Draft Revision.

The capability extension `executors.draft_revision.planning` owns
`DraftRevisionPlanningInput`. It reuses the frozen revision policy, scope,
instructions, and target contracts and retains the exact authoritative source
draft. It validates target existence, policy limits, scope/instruction lineage,
and conservative anti-regeneration rules before generic planning begins.

There is no registry or discovery. Capability validation is ordinary typed
composition, suitable for additional capability extension packages without
adding optional fields to generic models.

## Versioning and compatibility

Version-1 request, plan, and result classes are untouched. Their constructors,
model dumps, validators, and fingerprint payloads remain bit-for-bit unchanged.
Version 2 uses immutable envelopes:

1. `CorrectiveActionExecutionPlanRequestV2` preserves the exact v1 request and
   adds one typed planning input.
2. `CorrectiveActionExecutionPlanV2` preserves the exact v1 plan, v2 request,
   and planning-input identity.
3. `CorrectiveActionExecutionPlanResultV2` preserves the exact v1 result and v2
   plan.

This avoids adding a nullable field that would silently change legacy Pydantic
serialization. Unknown versions fail closed and invalid v2 inputs never fall
back to v1.

Lineage is decision result → Draft Revision planning input → request v2 → plan
v2 → result v2. Policy, scope, instructions, source draft, v1 plan, and typed
input identities are preserved throughout.

## Authorization and privacy

Planning-time authorization is the exact planning-policy fingerprint. Actual
human authorization remains owned by the later dispatch execution context. Safe
reports expose only types, counts, controlled enum values, and fingerprints;
they exclude draft and instruction prose.

M6C.6B.2 may later transport the v2 planning input without inspecting revision
fields. This milestone does not modify dispatch, executor requests, Controlled
Generation, providers, or runtime execution.

## Architecture self-review

BLOCKING: none.

HIGH PRIORITY: M6C.6B.2 must accept the v2 planning-result envelope and preserve
the exact planning input in executor-request v2 without teaching dispatch any
revision semantics.

WORTH CONSIDERING: if several capability extensions repeat safe-report or v2
envelope construction, extract small pure utilities after the repetition is
demonstrated. Do not introduce a registry or template-method hierarchy.

DO NOT CHANGE: version-1 models and fingerprints, M6C.5F decision ownership,
dispatch authorization, provider boundaries, or frozen revision contracts.

Known limitation: v2 is an explicit transport envelope rather than an in-place
nullable-field evolution. This is deliberate because in-place fields would alter
legacy serialization. Controlled Generation still lacks targeted revision
contracts and remains a separate compatibility milestone.
