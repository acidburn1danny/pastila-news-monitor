# M6C.5E Editorial Review Integration

M6C.5E is the application boundary joining the authoritative controlled-generation
API to the frozen M6C.5D editorial-review orchestrator. It owns workflow sequencing,
identity checks, sanitized diagnostics, lifecycle reporting, and deterministic
integration fingerprints. It does not own generation or editorial decisions.

## Standard flow

`EditorialReviewIntegrationService.execute()` accepts one immutable
`EditorialReviewIntegrationRequest`. It invokes `ControlledGenerator.generate()` at
most once with the original typed inputs, validates the returned draft, creates the
M6C.5D request, and invokes `EditorialReviewOrchestrator.review()` at most once. The
standard composition root wires the real deterministic M6C.5B reviewer through the
M6C.5C pipeline and M6C.5D orchestrator.

The result preserves both nested results unchanged. A review finding that requires
regeneration is an editorial outcome, not an operational integration failure.
Generation or review exceptions are converted to stable diagnostic codes; raw
exception text, provider details, credentials, paths, draft content, and findings are
not copied into integration metadata.

```text
application
    -> M6C.5E integration service
        -> controlled generation public API
        -> M6C.5D public orchestrator
            -> M6C.5C reviewer pipeline
                -> M6C.5B deterministic reviewer
            -> M6C.5A aggregation and approval
```

| Layer | Authority retained by that layer |
| --- | --- |
| Generation | prompts, provider calls, component validation, draft assembly |
| M6C.5D | manifest resolution, pipeline handoff, editorial orchestration |
| M6C.5E | one generation-to-review sequence and its operational outcome |
| Later workflow | regeneration, publication, persistence, and human routing |

## Status and failure semantics

Generation exceptions and invalid generation results stop before review with
`failed_during_generation`. An invalid generated draft or review-request construction
failure returns `failed_before_review`. Review exceptions, invalid/mismatched review
results, and valid M6C.5D operational failures return `failed_during_review`. A valid
generation and review returns `completed` regardless of whether the editorial decision
is approval or `requires_regeneration`. Explicitly disabled review returns
`completed_without_review` and is marked as limited completion.

The high-level trace is the immutable transition record. Its zero-based sequence is
the deterministic revision order; each accepted boundary appends exactly one event,
and finalization appends one terminal event. Nested generation and review traces remain
inside their authoritative results and are not copied upward.

The authoritative in-memory result contains the unchanged generation and M6C.5D
results. `serialize_integration_report()` and `render_integration_report()` expose only
the sanitized application report: identities, statuses, completeness, and diagnostic
codes. They intentionally omit prose, findings, evidence, recommendations, provider
data, exceptions, paths, and credentials.

## Public API

- `ControlledGenerationInvocation`
- `EditorialReviewIntegrationRequest`
- `EditorialReviewIntegrationResult`
- `EditorialReviewIntegrationService`
- `build_standard_editorial_review_integration_service()`
- `generate_and_review_episode()`
- `render_integration_report()`

## Intentional milestone boundaries

The integration performs no retries, regeneration, repair, persistence, resume,
publication gating, human-review routing, provider selection, or workflow
continuation. A generator must be supplied explicitly because provider construction
belongs to the application composition layer. Review may be explicitly disabled by
policy; the result then reports limited completion without fabricating an editorial
outcome.

The current controlled-generation subsystem exposes keyword-oriented typed inputs,
not a single public generation-request/result-fingerprint contract. M6C.5E therefore
wraps those inputs immutably and derives deterministic SHA-256 identities using the
repository canonical serializer. The authoritative generation result itself is still
preserved unchanged. No CLI or web facade is added because the repository has no
existing episode-generation application command that can construct all required
blueprints without introducing a second workflow owner.
