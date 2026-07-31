# Controlled Provider Quality Baseline

Part 7C executed the frozen 24-scenario, 12-category corpus once through the
production OpenAI Controlled Revision pipeline on 2026-07-28. The production
schema fingerprint matched
`70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556`
before execution. The model was `gpt-4.1-mini`; SDK retries, runtime retries,
and provider/model fallbacks were all zero.

## Result

- Benchmark ID: `20260728-092119-openai-gpt-4.1-mini`
- Provider requests: 24 (one per scenario)
- Pipeline successes: 0
- Safely rejected provider outputs: 1
- Other normalized provider-pipeline failures: 23
- Most frequent safe diagnostics:
  - `openai_provider_output_reference_unknown`: 12
  - `openai_provider_output_reference_unauthorized`: 11
  - `openai_provider_output_schema_invalid`: 1
- Quality sample: 0
- Root conclusion: `INSUFFICIENT_SAMPLE`
- Final recommendation: `INVESTIGATE_PROVIDER_FAILURES`

Because no response completed the full production acceptance pipeline, no
scenario was eligible for quality-rate calculation. The runtime does not
expose response usage after interpretation/reconstruction rejection, so token,
latency, and estimated-cost measurements for these failed trials were not
available. Their zero-valued aggregate fields must not be interpreted as
provider-reported zero usage or zero latency.

No prompt text, source draft, revised draft, raw provider response, credential,
or secret is stored in the benchmark artifact. The artifact contains only
scenario identifiers, categories, bounded diagnostic codes, counters, and
aggregate measurements.

## Artifacts and history

The complete content-free result is stored in
`docs/artifacts/controlled-provider-quality-baseline.json`. Exactly one entry
was appended atomically to
`docs/artifacts/controlled-provider-quality-history.json`. The history record
is immutable and retains the `INSUFFICIENT_SAMPLE` conclusion.

No scenario was retried, replayed, replaced, or manually repaired. A future
run requires a separately authorized benchmark; this milestone does not
automatically repeat the baseline.
