# OpenAI Controlled Revision Production Observability Foundation

## Executive Summary

Part 6A adds a provider-neutral, privacy-safe telemetry foundation. Telemetry is disabled by default, uses a no-op sink when disabled, and cannot affect Controlled Revision outcomes. No provider or SDK requests were made.

## Part 5 Completion Context

Parts 5J–5N established schema/DTO conformance, deterministic downstream safety, and operational readiness. Their frozen behavior remains authoritative.

## Objectives

The foundation exposes bounded terminal outcomes, stage progress, counters, durations, immutable aggregate snapshots, rates, invariant checks, and rollout-status evaluation.

## Non-Objectives

It does not tune prompts, change contracts, repair output, retry, fall back, select models, alter editorial decisions, or integrate a vendor backend.

## Frozen Production Boundaries

Prompt, JSON Schema, provider DTO and validators, interpreter, authorization, reconstruction, EpisodeDraft, gateway, acceptance, retry/fallback policy, provider parameters, credentials, and timeouts are unchanged. The schema fingerprint remains `70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556`.

## Operational Outcome Taxonomy

- `PIPELINE_SUCCESS`: the full pipeline terminated normally after acceptance evaluation; acceptance may pass or fail.
- `PROVIDER_OUTPUT_REJECTED_SAFELY`: provider-originated output was rejected before unsafe downstream work.
- `EXTERNAL_PROVIDER_FAILURE`: transport/provider-side execution failed.
- `LOCAL_RUNTIME_FAILURE`: unexpected local processing failed.

Every telemetry execution accepts exactly one terminal outcome.

## Stage Taxonomy

The API contains the complete required ordered stage vocabulary from `execution_started` through `execution_completed`. Only reached stages are emitted by an execution session.

## Metric Inventory

Thirty counters and nine duration metrics are repository-owned constants. Dimensions are limited to operational outcome, scenario class, provider/model family, failure layer, safe failure category, acceptance result, telemetry state, and environment class.

## Duration Metrics

Execution, provider, JSON decode, DTO validation, authorization, reconstruction, EpisodeDraft validation, gateway, and acceptance durations use a monotonic clock. Values are finite, non-negative milliseconds; an unreached stage has no duration.

## Safe Dimensions

The in-memory sink rejects unknown dimension keys. Provider and model values are normalized to explicit bounded families; unknown model families are omitted.

## Forbidden Dimensions

References, request/episode/story/user identifiers, URLs, prompt/content hashes, raw model identifiers, validation paths, exception text, and free-form values are forbidden.

## Failure Classification

`SafeFailureCategory` owns a fixed vocabulary. Classification uses stable diagnostic codes and content-free aggregate validator metadata. Unknown failures become `unknown_safe_rejection`; raw Pydantic errors never leave the local classifier.

## Telemetry Interface

`ControlledRevisionMetricSink` defines counter and duration operations. `ControlledRevisionTelemetry` owns one execution's stages and terminal classification.

## Sink Implementations

`NoOpControlledRevisionMetricSink` is the default. `InMemoryControlledRevisionMetricSink` provides deterministic local assertions. `IsolatedControlledRevisionMetricSink` suppresses backend failures.

## Configuration

`ControlledRevisionTelemetryConfiguration.enabled` has explicit disabled/enabled states and defaults to disabled. Configuration cannot enter provider request content or editorial logic.

## Failure Isolation

Every sink call is isolated. A failing sink increments only an internal bounded failure count; it cannot escape, retry, or alter the business result.

## Instrumentation Ownership

| Stage | Owner |
|---|---|
| Provider request/response | provider adapter runtime |
| JSON decoding | Controlled Revision interpreter boundary |
| DTO validation | provider DTO boundary |
| Authorization | reference authorization layer |
| Reconstruction | deterministic reconstructor |
| EpisodeDraft validation | domain model boundary |
| Gateway | gateway creation layer |
| Acceptance | editorial acceptance evaluator |
| Terminal classification | orchestration/runtime |

Each boundary has one owner; the telemetry foundation does not duplicate business execution.

## Event Ordering

Sessions preserve insertion order, reject a second terminal outcome, and reject stages after completion. Local replay asserts the canonical success and fail-closed sequences.

## Aggregate Snapshot

`OperationalSnapshot` is frozen and contains counters, duration percentiles, and bounded category counts only. It carries no content or identifiers.

## Rate Definitions

- DTO success: DTO passes / DTO validations reached.
- Safe rejection: safe rejections / provider responses.
- Pipeline success, external failure, runtime failure, and gateway reach: respective count / total executions.
- Acceptance pass: passes / acceptance evaluations reached.

Zero denominators return `null`/`None`, never a misleading percentage. Percentiles use deterministic nearest-rank calculation.

## Rollout Status Evaluation

The pure evaluator reports inconsistent telemetry first, then runtime-safety violations, insufficient sample, or operational health. It does not remediate or affect execution. Rate thresholds are intentionally not invented.

## Privacy Model

Only enum values, bounded families, counts, and durations are retained. Tests prohibit references, provider/source prose, prompt bodies, request IDs, credentials, raw exceptions, and raw validation objects.

## Local Scenario Replay

The development-only replay covers acceptance pass/fail, duplicate reference, invalid JSON, provider timeout, local failure, and sink failure. It performs zero provider and zero SDK requests.

## Regression Results

Part 5K–5N focused regressions and the complete suite pass. Ruff, Black, compileall, and pip check pass; exact counts are recorded in the artifact.

## Findings

- **P6A-TELEMETRY** — severity: informational; layer: provider-neutral adapter; evidence: protocol plus two sinks; impact: safe backend seam; confidence: HIGH; follow-up: integrate an approved aggregate backend; architecture impact: targeted.
- **P6A-OUTCOMES / P6A-STAGES / P6A-METRICS / P6A-DURATIONS** — severity: informational; evidence: frozen enums and inventories; impact: consistent operational diagnosis; confidence: HIGH; follow-up: production sampling; architecture impact: none.
- **P6A-DIMENSIONS / P6A-CLASSIFICATION / P6A-PRIVACY** — severity: safety; evidence: strict sink validation and bounded classifier; impact: content-free telemetry; confidence: HIGH; follow-up: retain bounded review; architecture impact: none.
- **P6A-ISOLATION / P6A-CONFIGURATION** — severity: safety; evidence: isolated sink and disabled default; impact: behavioral transparency; confidence: HIGH; follow-up: backend fault injection; architecture impact: none.
- **P6A-INVARIANTS / P6A-REGRESSION / P6A-ARCHITECTURE** — severity: informational; evidence: snapshot checks and quality gates; impact: freeze preserved; confidence: HIGH; follow-up: monitor aggregate consistency; architecture impact: targeted additive seam.

## Architecture Impact

Targeted and additive. The provider-neutral telemetry boundary introduces no provider coupling and changes no production decision.

## Root Conclusion

`OBSERVABILITY_FOUNDATION_COMPLETE`

## Final Recommendation

`READY_FOR_OBSERVABILITY_BACKEND_INTEGRATION`
