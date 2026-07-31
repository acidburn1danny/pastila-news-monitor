# Controlled Provider Quality Baseline v2

## Executive Summary

The official instrumented baseline processed 24 scenarios with
24 single-attempt provider requests. Its root conclusion is
`PROVIDER_REFERENCE_CONTRACT_FAILURE` and its recommendation is
`DESIGN_REFERENCE_CONTRACT_REMEDIATION`.

## Benchmark Identity

- ID: `20260728-102323-openai-gpt-4.1-mini-v2`
- Provider/model: `openai` / `gpt-4.1-mini`
- Schema: `70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556`
- Pricing: `openai-gpt-4-1-mini-2026-07-28`

## Frozen Configuration

Prompt, schema, DTO, runtime, adapter, authorization, reconstruction, acceptance,
retry/fallback policy, corpus, model, and provider were unchanged.

## Preflight Validation

All frozen identity, projection, pricing, persistence, history, request-cap, retry,
and fallback checks passed before the first request.

## Execution Integrity

Retries: 0; fallbacks: 0; replays: 0.

## Operational Outcomes

```json
{
  "PROVIDER_OUTPUT_REJECTED_SAFELY": 24
}
```

## Failure-Code Distribution

```json
{
  "openai_provider_output_reference_unauthorized": 10,
  "openai_provider_output_reference_unknown": 12,
  "openai_provider_output_schema_invalid": 2
}
```

## Failure-Stage Distribution

```json
{
  "PROVIDER_DTO_VALIDATION": 2,
  "REFERENCE_MAPPING": 22
}
```

## Pipeline Funnel

```json
{
  "authorization_passes": 0,
  "editorial_acceptance_passes": 0,
  "episode_draft_validation_passes": 0,
  "json_parse_passes": 24,
  "pipeline_successes": 0,
  "provider_call_failures": 0,
  "provider_dto_passes": 22,
  "provider_responses_received": 24,
  "quality_evaluation_completions": 0,
  "reconstruction_passes": 0,
  "reference_mapping_passes": 0,
  "scenarios_requested": 24
}
```

## Reference Diagnostics

```json
{
  "confusion_matrix": {
    "story:101 -> closing": 11,
    "story:101 -> opening": 20,
    "story:101 -> transition:1010:1": 1,
    "story:101 -> transition:1010:1010": 1,
    "story:101 -> transition:10113:8": 1,
    "story:101 -> transition:1011:1": 1,
    "story:101 -> transition:1013:1": 1,
    "story:101 -> transition:1014:2": 1,
    "story:101 -> transition:1017:7": 1,
    "story:101 -> transition:101:1": 2,
    "story:101 -> transition:1:1": 5,
    "story:101 -> transition:1:101": 1,
    "story:101 -> transition:1:2": 3,
    "story:101 -> transition:1:3": 1,
    "story:101 -> transition:2:1": 3,
    "story:101 -> transition:2:2": 3,
    "story:101 -> transition:3:1": 3,
    "story:101 -> transition:3:2": 3
  },
  "duplicate_scenarios": 2,
  "exact_authorized_scenarios": 0,
  "malformed_scenarios": 0,
  "missing_scenarios": 24,
  "most_common_first_invalid_reference": "opening",
  "most_common_unauthorized_reference": "opening",
  "most_common_unknown_reference": "transition:1:1",
  "precision": {
    "maximum": 0.0,
    "mean": 0.0,
    "median": 0.0,
    "minimum": 0.0,
    "p95": 0.0
  },
  "precision_availability_rate": 1.0,
  "recall": {
    "maximum": 0.0,
    "mean": 0.0,
    "median": 0.0,
    "minimum": 0.0,
    "p95": 0.0
  },
  "recall_availability_rate": 1.0,
  "unauthorized_scenarios": 17,
  "unknown_scenarios": 14
}
```

## First Invalid References

The most common first invalid structural reference is
`opening`.

## Reference Precision and Recall

Undefined denominators remain null. Duplicate references do not inflate true positives.

## Reference Confusion Analysis

The JSON artifact contains the structural-only confusion matrix; no provider prose is stored.

## Latency

```json
{
  "all_provider_calls": {
    "count": 24,
    "maximum": 12286.48410004098,
    "mean": 2854.7348750047,
    "median": 2165.902750042733,
    "minimum": 1499.7579000191763,
    "p50": 2149.3161000544205,
    "p90": 3419.5957999909297,
    "p95": 5220.172600005753,
    "percentile_method": "nearest-rank"
  },
  "pipeline_successes": null,
  "provider_execution_failures": null,
  "safe_rejections": {
    "count": 24,
    "maximum": 12286.48410004098,
    "mean": 2854.7348750047,
    "median": 2165.902750042733,
    "minimum": 1499.7579000191763,
    "p50": 2149.3161000544205,
    "p90": 3419.5957999909297,
    "p95": 5220.172600005753,
    "percentile_method": "nearest-rank"
  }
}
```

## Token Usage

```json
{
  "availability_rate": 1.0,
  "available_scenarios": 24,
  "cached_prompt_tokens": 1152,
  "completion_tokens": 3117,
  "derived_total_tokens": 0,
  "known_total_tokens": 35279,
  "prompt_tokens": 32162,
  "provider_reported_total_tokens": 35279,
  "reasoning_tokens": 0,
  "unavailable_scenarios": 0
}
```

## Cost Accounting

```json
{
  "calculability_rate": 1.0,
  "calculable_scenarios": 24,
  "coverage_complete": true,
  "estimated": true,
  "known_cost_distribution": {
    "count": 24,
    "maximum": 0.00226,
    "mean": 0.0007294333333333334,
    "median": 0.0006540000000000001,
    "minimum": 0.00028720000000000004,
    "p50": 0.0006524000000000001,
    "p90": 0.0008056000000000002,
    "p95": 0.0008452,
    "percentile_method": "nearest-rank"
  },
  "known_estimated_total_cost_usd": 0.017506400000000002,
  "pricing_effective_date": "2026-07-28",
  "pricing_source": "OpenAI GPT-4.1 mini model pricing page, accessed 2026-07-28",
  "pricing_version": "openai-gpt-4-1-mini-2026-07-28",
  "unknown_scenarios": 0
}
```

## Pipeline Quality Metrics

```json
{
  "authorization_pass_rate": null,
  "editorial_acceptance_rate": null,
  "episode_draft_validation_pass_rate": null,
  "meaning_preservation_rate": null,
  "provider_dto_pass_rate": null,
  "reconstruction_pass_rate": null,
  "sample_count": 0,
  "usable_revision_rate": null
}
```

## Editorial Quality Metrics

Only pipeline-eligible scenarios enter the editorial-quality sample.

## Quality Sample Sufficiency

`INSUFFICIENT` using the frozen threshold of 12.

## Comparison With Part 7C

Both runs use OpenAI `gpt-4.1-mini`, the same schema/pricing, 24 scenarios, 12
categories, 24 maximum requests, zero retries, and zero fallbacks. Part 7C lacked
produced-reference retention and rejected-response usage, and misclassified safe
output rejection. Its precision, recall, and confusion metrics are not retrospectively
comparable and its artifact remains unchanged.

## Privacy and Artifact Safety

Artifacts contain only structural metadata, hashed correlation IDs, bounded diagnostics,
usage, latency, cost, and quality booleans—never provider or episode prose.

## Benchmark History

One v2 entry was appended after both artifacts were persisted and validated. Earlier
entries remain immutable.

## Regression Results

All required regressions and static quality gates passed after live execution.

## Architecture Impact

None.

## Root Conclusion

`PROVIDER_REFERENCE_CONTRACT_FAILURE`

## Final Recommendation

`DESIGN_REFERENCE_CONTRACT_REMEDIATION`
