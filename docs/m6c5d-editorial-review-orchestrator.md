# M6C.5D editorial review orchestrator

## Architecture and ownership

The application-facing orchestrator is a synchronous, immutable, in-memory composition
layer. It resolves one explicit or standard manifest, invokes M6C.5C once, evaluates only
handoff eligibility, then uses the frozen M6C.5A aggregator and approval evaluator. It
does not inspect findings to decide handoff and never rewrites or regenerates a draft.

```text
EpisodeDraft -> M6C.5D request -> manifest -> M6C.5C pipeline
             -> accepted results -> eligibility -> M6C.5A aggregation/approval
             -> composed M6C.5D result
```

M6C.5B owns deterministic findings. M6C.5C owns reviewer execution, coverage, failures,
and skips. M6C.5A owns aggregation and approval. M6C.5D owns only manifest precedence,
handoff policy, application status, safe diagnostics, trace, completeness, and composed
result identity.

## Standard construction and policy

`build_standard_editorial_review_orchestrator()` explicitly registers the real
`DeterministicRulesReviewer`; no semantic reviewer is invented. An explicit manifest
takes precedence over the deterministic standard provider. Defaults require at least one
accepted result and a fully completed pipeline; completed-with-skips and partial handoff
must be explicitly permitted.

## Status separation

Pipeline status is operational. Orchestration status describes whether composition and
handoff ran. Editorial approval remains the unchanged M6C.5A decision. A completed
orchestration may therefore contain a rejected or regeneration-required editorial
decision. Pipeline failure never fabricates editorial rejection.

## Privacy, determinism, and limitations

Diagnostics and the safe report contain stable codes, counts, statuses, and fingerprints
only—never draft prose, evidence, recommendations, provider content, exception messages,
paths, or credentials. No timestamps, randomness, retries, persistence, cache, network,
provider reviewer, history, metrics, dynamic discovery, rewrite, regeneration, or human
workflow is implemented. Incremental/durable orchestration resume is not supported.
