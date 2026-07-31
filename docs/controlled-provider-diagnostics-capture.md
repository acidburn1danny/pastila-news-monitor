# Controlled Provider Diagnostics Capture

## Executive Summary

Part 7E adds benchmark-only, privacy-safe capture needed for a future separately
authorized Controlled Revision provider baseline. Metadata is captured as soon
as a response is available and before production interpretation can reject it.
No provider request, SDK request, network request, benchmark replay, scenario
replay, or history append occurred in this milestone.

## Background

Part 7C made 24 single-attempt requests but retained only terminal diagnostic
codes after downstream rejection. Part 7D confirmed that provider-produced
references, early usage, and latency were unavailable and that 23 safe output
rejections had been classified as generic provider failures.

## Part 7C Diagnostic Gap

The old result remains historically valid as `INSUFFICIENT_SAMPLE`. Neither
the Part 7C artifact nor its immutable history entry has been changed. Missing
references and usage were not inferred, and historical zeros were not replaced
with estimates.

## Scope and Frozen Boundaries

Changes are restricted to provider-neutral benchmark diagnostic models,
OpenAI-specific benchmark composition under `scripts/`, the Part 7C runner,
tests, documentation, and an empty diagnostics artifact. Production prompt,
schema, DTO, authorization, reconstruction, runtime, gateway, adapter, retry,
fallback, model, temperature, corpus, acceptance specifications, and pricing
remain unchanged. The schema fingerprint is still
`70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556`.

## Early Provider Metadata Capture

A benchmark-only client wrapper uses a monotonic clock around the one existing
transport call. A benchmark-only interpreter wrapper captures metadata before
delegating to the unchanged production interpreter. If JSON parsing, DTO
validation, authorization, reconstruction, domain validation, acceptance, or
quality evaluation subsequently fails, already captured safe metadata remains
available.

The wrappers do not retry, repair, fallback, or issue another request.

## Usage and Cost Semantics

Captured usage supports prompt, completion, reasoning, cached prompt, input
audio, output audio, provider-reported total, and benchmark-derived total
tokens. A total is derived only when prompt and completion counts both exist.
Its source is explicitly one of `PROVIDER_REPORTED`, `BENCHMARK_DERIVED`, or
`UNAVAILABLE`.

Unavailable usage is `null`, not zero. Zero means the provider explicitly
reported zero. Rejected provider output may still incur cost. Cost is estimated
with the frozen versioned pricing specification whenever prompt and completion
usage is known; otherwise cost is `null` with `INSUFFICIENT_USAGE`. Missing
pricing produces `PRICING_UNAVAILABLE`.

## Reference Metadata Model

The immutable diagnostic records:

- exact authorized references;
- provider references in original response order;
- recognized, unknown, unauthorized, missing, unexpected, and duplicate sets;
- first invalid reference and bounded kind;
- overlap and reference counts;
- precision and recall.

Only structural identifiers are retained. Malformed, non-string, oversized, or
non-structural values become `<MALFORMED_REFERENCE>`. No associated component
text is stored.

## Operational Outcome Classification

Outcomes are bounded. Received responses rejected fail-closed by JSON, DTO,
reference mapping, authorization, reconstruction, domain validation, or
acceptance are `PROVIDER_OUTPUT_REJECTED_SAFELY`. Safe output rejection is not
a provider transport failure.

Timeout, rate limit, service failure, transport failure, invalid SDK response,
benchmark internal failure, and abort remain distinct. Generic
`PROVIDER_FAILURE` is no longer used by the future diagnostic record.

## Safe Provider-Output Rejection Mapping

Existing normalized codes such as
`openai_provider_output_reference_unknown`,
`openai_provider_output_reference_unauthorized`, and
`openai_provider_output_schema_invalid` are preserved independently of the
operational outcome. Raw exception messages are not serialized.

## Failure Stage Taxonomy

Every terminal trial uses one controlled stage from request construction,
provider call/response capture, JSON parsing, DTO validation, reference mapping,
authorization, reconstruction, EpisodeDraft validation, editorial acceptance,
quality evaluation, persistence, or history append. `NONE` is reserved for a
complete pipeline success.

## Privacy and Content Safety

The capture never persists prompt text, raw request/response payloads, provider
prose, component prose, episode text, quotations, entities, credentials,
headers, or raw provider request identifiers. Provider correlation identifiers
are stored only as deterministic SHA-256 hashes and do not affect benchmark
identity.

## Reference Precision and Recall

Precision is the number of unique authorized references produced divided by
the number of unique provider-produced references. Unknown, unauthorized, and
malformed references therefore count against precision; duplicates do not
inflate true positives. Recall is unique
required authorized references produced divided by required authorized
references. An undefined zero denominator returns `null`, including a no-op
case whose acceptance specification requires no returned reference.

## Reference Confusion Analysis

Aggregate diagnostics count deterministic mappings of each authorized
reference to each produced structural reference. Empty production is represented
as `<MISSING>`; malformed values use `<MALFORMED_REFERENCE>`. Frequency tables
cover unknown, unauthorized, missing, duplicate, and first-invalid references.

## Artifact Persistence

`docs/artifacts/controlled-provider-quality-diagnostics.json` is a version-1
empty template. A future authorized run will populate trials and aggregates.
Serialization is canonical UTF-8 JSON using a temporary file, flush and fsync,
then atomic replace. A failed replace leaves the prior artifact unchanged.

## History Compatibility

No Part 7E history entry is appended. Existing schema-version-1 history remains
readable and byte-for-byte unchanged. Nullable diagnostics live in the separate
future diagnostics artifact and do not invalidate historical entries.

## Offline Test Coverage

Synthetic tests cover authorized, unknown, unauthorized, DTO-rejected,
duplicate, timeout, rate-limit, service, transport, internal-failure,
unavailable-usage, cached-input, no-op, and malformed-reference cases. They also
cover early capture before delegate rejection, latency, hashed identifiers,
precision/recall, confusion aggregation, null cost, privacy canaries, atomic
persistence, frozen schema/corpus/model, one adapter attempt, and SDK retries
set to zero.

## Regression Results

Part 7E focused and all requested historical/full regressions passed. Ruff,
Black, compileall, and `pip check` passed. The existing harmless Windows pytest
cache warning may still appear.

## Architecture Impact

None. Provider-neutral benchmark concepts remain isolated in the Controlled
Revision quality package. OpenAI response extraction and instrumentation remain
under `scripts/`. Production execution behavior is unchanged.

## Root Conclusion

`PROVIDER_DIAGNOSTICS_CAPTURE_READY`

## Final Recommendation

`READY_FOR_CONTROLLED_PROVIDER_BASELINE_RERUN`

No prompt, schema, or authorization modification is recommended. Those choices
require evidence from a future correctly instrumented and separately authorized
baseline.
