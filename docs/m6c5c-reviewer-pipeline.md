# M6C.5C deterministic reviewer pipeline

## Architecture

The private pipeline converts the frozen M6C.5A manifest into an immutable execution
plan, resolves an active selection and dependency closure, schedules one unit at a time,
invokes an abstract `EditorialReviewer`, accepts a validated terminal outcome atomically,
and produces operational coverage, diagnostics, trace, result, and report artifacts.

The pipeline owns execution mechanics only. It does not aggregate findings, approve or
reject an episode, rewrite text, retry reviewers, invoke providers, or mutate a draft.
Editorial findings—including critical findings—are successful operational reviewer
results when structurally valid.

## Lifecycle and scheduling

The synchronous state partitions selected IDs into pending, ready, and terminal
outcomes. Revision zero is initialized. Each accepted reviewer outcome plus deterministic
dependency/policy propagation increments revision once. Dependencies require a validated
`COMPLETED` result; failed or skipped dependencies propagate `DEPENDENCY_UNSATISFIED`.
Independent units follow frozen manifest order. Requested subsets include their complete
dependency closure. No thread, process, async task, retry, or hidden background work is
used.

## Failure separation

Reviewer exceptions and malformed results become sanitized failed outcomes. Raw
exceptions are never retained. Uninvoked dependents become skipped, not failed. Pipeline
diagnostic severity is operational and has no mapping to editorial severity or approval.
M6C.5A remains the sole owner of aggregation and approval consequences.

## Identity, trace, and privacy

Policy, request, registry, plan, selection, outcome, diagnostic, trace event, state,
coverage, result, and report artifacts use canonical SHA-256 fingerprints without
timestamps or object identity. The authoritative trace records accepted transitions,
not transient invocation starts. Pipeline metadata contains no draft prose, static CTA
content, raw articles, prompts, provider data, credentials, or raw exception messages.
Validated reviewer results retain their frozen M6C.5A content unchanged.

## Recovery and limitations

Immutable state supports in-memory incremental continuation only when plan, registry,
policy, selection, draft, and pipeline identities match. Durable resume, persistence,
caching, parallel execution, retries, dynamic reviewer discovery, semantic reviewer
selection, approval, rewriting, and regeneration are not implemented. The pipeline can
guarantee atomic state acceptance but cannot roll back arbitrary side effects inside a
third-party reviewer implementation.
