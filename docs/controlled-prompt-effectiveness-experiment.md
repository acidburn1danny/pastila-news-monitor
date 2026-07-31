# Part 7H — Controlled Prompt Effectiveness Experiment

## Executive Summary

The frozen candidate decision is `REJECT` with root conclusion
`CANDIDATE_PROMPT_FAILED_TECHNICAL_NON_REGRESSION`. The control is official Part 7C.2; only the provider
instruction text changed.

## Editorial Failure Taxonomy

```json
[
  {
    "category_id": "SOURCE_AUTHORITY_DRIFT",
    "confidence": "high",
    "definition": "Meaning, instruction compliance, or source authority was not preserved",
    "evaluated_scenario_percentage": 0.875,
    "exclusion_criteria": "another primary frozen evaluator category applies",
    "inclusion_criteria": "quality_failure_category == SOURCE_AUTHORITY_DRIFT",
    "independently_causes_rejection": true,
    "prompt_addressability": "PROMPT_ADDRESSABLE",
    "rejected_scenario_percentage": 0.9130434782608695,
    "scenario_count": 21,
    "scenario_ids": [
      "SYN-01",
      "SYN-02",
      "SYN-03",
      "SYN-04",
      "SYN-05",
      "SYN-06",
      "SYN-07",
      "SYN-08",
      "SYN-09",
      "SYN-11",
      "SYN-12",
      "SYN-13",
      "SYN-14",
      "SYN-15",
      "SYN-16",
      "SYN-17",
      "SYN-18",
      "SYN-19",
      "SYN-21",
      "SYN-22",
      "SYN-24"
    ],
    "severity": "high"
  },
  {
    "category_id": "QUOTE_MUTATION",
    "confidence": "high",
    "definition": "An authoritative quotation changed while revising the target",
    "evaluated_scenario_percentage": 0.08333333333333333,
    "exclusion_criteria": "another primary frozen evaluator category applies",
    "inclusion_criteria": "quality_failure_category == QUOTE_MUTATION",
    "independently_causes_rejection": true,
    "prompt_addressability": "PROMPT_ADDRESSABLE",
    "rejected_scenario_percentage": 0.08695652173913043,
    "scenario_count": 2,
    "scenario_ids": [
      "SYN-10",
      "SYN-23"
    ],
    "severity": "high"
  }
]
```

The control taxonomy contains 21 `SOURCE_AUTHORITY_DRIFT` and 2 `QUOTE_MUTATION`
primary failures. Both were classified prompt-addressable before execution. No
non-prompt category dominated, so the candidate eligibility gate passed.

## Candidate Prompt and Frozen Design

Control fingerprint: `a96575ff38ec6f7b50d4174157f0f99c73ed16857a8cb4235cb5487cf8507264`.
Candidate fingerprint: `e56b51a7a0ffdbf7a90f453067c0943b0c2e78d29af9c6e71b7d701c9918287a`.
The exact candidate and evidence mapping are preserved in the design artifact.

## Frozen Experimental Design and Success Thresholds

The treatment uses the same 24 scenarios, order, provider/model configuration, exact
schema projection, authorization, reconstruction, EpisodeDraft validation, editorial
rubric, threshold, single-attempt policy, and pricing as Part 7C.2. The sole intended
variable is prompt text. The precommitted threshold was:

```json
{
  "maximum_pass_to_fail": 0,
  "minimum_acceptance_gain": 6,
  "minimum_improved_scenarios": 16,
  "minimum_mean_score_gain": 10.0,
  "rule": "acceptance gain >= 6 OR (mean score gain >= 10 and improved scenarios >= 16)"
}
```

Technical and exact-reference success were required to remain 100%.

## Treatment Funnel and Reference Metrics

```json
{
  "pipeline": {
    "authorization_passes": 23,
    "editorial_acceptance_failures": 23,
    "editorial_acceptance_passes": 0,
    "editorial_evaluation_attempts": 23,
    "editorial_evaluation_completions": 23,
    "episode_draft_validation_passes": 23,
    "json_parse_passes": 23,
    "pipeline_successes": 23,
    "provider_call_failures": 1,
    "provider_dto_passes": 23,
    "provider_responses_received": 23,
    "quality_evaluation_completions": 23,
    "reconstruction_passes": 23,
    "reference_mapping_passes": 23,
    "scenarios_requested": 24,
    "technical_pipeline_successes": 23
  },
  "references": {
    "confusion_matrix": {
      "story:101 -> <MISSING>": 1,
      "story:101 -> story:101": 23
    },
    "duplicate_scenarios": 0,
    "exact_authorized_scenarios": 23,
    "malformed_scenarios": 0,
    "missing_scenarios": 1,
    "most_common_first_invalid_reference": null,
    "most_common_unauthorized_reference": null,
    "most_common_unknown_reference": null,
    "precision": {
      "maximum": 1.0,
      "mean": 1.0,
      "median": 1.0,
      "minimum": 1.0,
      "p95": 1.0
    },
    "precision_availability_rate": 0.9583333333333334,
    "recall": {
      "maximum": 1.0,
      "mean": 0.9583333333333334,
      "median": 1.0,
      "minimum": 0.0,
      "p95": 1.0
    },
    "recall_availability_rate": 1.0,
    "unauthorized_scenarios": 0,
    "unknown_scenarios": 0
  }
}
```

## Editorial and Paired Metrics

```json
{
  "acceptance_absolute_delta": -0.041666666666666664,
  "acceptance_failures": 23,
  "acceptance_passes": 0,
  "acceptance_rate": 0.0,
  "evaluations": 23,
  "fail_to_pass": 0,
  "improved_score_scenarios": 2,
  "maximum_score": 73.33333333333333,
  "mean_score": 73.33333333333333,
  "mean_score_delta": -0.5555555555555571,
  "median_score": 73.33333333333333,
  "median_score_delta": 0.0,
  "minimum_score": 73.33333333333333,
  "pass_to_fail": 1,
  "regressed_score_scenarios": 1,
  "unchanged_score_scenarios": 20
}
```

Acceptance moved from 1
of 24 to
0 of
23. Paired transitions were
0 fail-to-pass and
1 pass-to-fail.

## Failure-Taxonomy Comparison

```json
{
  "QUOTE_MUTATION": {
    "absolute_reduction": 2,
    "control": 2,
    "treatment": 0
  },
  "SOURCE_AUTHORITY_DRIFT": {
    "absolute_reduction": -2,
    "control": 21,
    "treatment": 23
  }
}
```

Quote mutation fell from 2 to 0, but source-authority drift rose from 21 to 23.
No new primary category appeared. The targeted improvement was therefore narrow and
offset by broader preservation failure.

## Latency, Usage, and Cost

```json
{
  "cost": {
    "control": {
      "calculability_rate": 1.0,
      "calculable_scenarios": 24,
      "coverage_complete": true,
      "estimated": true,
      "known_cost_distribution": {
        "count": 24,
        "maximum": 0.0005616,
        "mean": 0.0005149,
        "median": 0.0005112000000000001,
        "minimum": 0.0005040000000000001,
        "p50": 0.0005108000000000001,
        "p90": 0.0005276,
        "p95": 0.0005448,
        "percentile_method": "nearest-rank"
      },
      "known_estimated_total_cost_usd": 0.0123576,
      "pricing_effective_date": "2026-07-28",
      "pricing_source": "OpenAI GPT-4.1 mini model pricing page, accessed 2026-07-28",
      "pricing_version": "openai-gpt-4-1-mini-2026-07-28",
      "unknown_scenarios": 0
    },
    "treatment": {
      "calculability_rate": 0.9583333333333334,
      "calculable_scenarios": 23,
      "coverage_complete": false,
      "estimated": true,
      "known_cost_distribution": {
        "count": 23,
        "maximum": 0.0006472,
        "mean": 0.0005663826086956522,
        "median": 0.0005612000000000001,
        "minimum": 0.0005564000000000001,
        "p50": 0.0005612000000000001,
        "p90": 0.0005767999999999999,
        "p95": 0.000578,
        "percentile_method": "nearest-rank"
      },
      "known_estimated_total_cost_usd": 0.0130268,
      "pricing_effective_date": "2026-07-28",
      "pricing_source": "OpenAI GPT-4.1 mini model pricing page, accessed 2026-07-28",
      "pricing_version": "openai-gpt-4-1-mini-2026-07-28",
      "unknown_scenarios": 1
    }
  },
  "latency": {
    "control": {
      "all_provider_calls": {
        "count": 24,
        "maximum": 14287.841100012884,
        "mean": 2846.277320815716,
        "median": 2060.607500025071,
        "minimum": 1545.371500076726,
        "p50": 2040.7650999259204,
        "p90": 3583.992099855095,
        "p95": 4297.788699856028,
        "percentile_method": "nearest-rank"
      },
      "pipeline_successes": {
        "count": 24,
        "maximum": 14287.841100012884,
        "mean": 2846.277320815716,
        "median": 2060.607500025071,
        "minimum": 1545.371500076726,
        "p50": 2040.7650999259204,
        "p90": 3583.992099855095,
        "p95": 4297.788699856028,
        "percentile_method": "nearest-rank"
      },
      "provider_execution_failures": null,
      "safe_rejections": null
    },
    "treatment": {
      "all_provider_calls": {
        "count": 24,
        "maximum": 30148.45780003816,
        "mean": 3489.014233336396,
        "median": 1964.25675007049,
        "minimum": 1585.3418000042439,
        "p50": 1963.6290001217276,
        "p90": 3622.2409000620246,
        "p95": 5298.85430005379,
        "percentile_method": "nearest-rank"
      },
      "pipeline_successes": {
        "count": 23,
        "maximum": 5298.85430005379,
        "mean": 2329.9079913058845,
        "median": 1963.6290001217276,
        "minimum": 1585.3418000042439,
        "p50": 1963.6290001217276,
        "p90": 3394.4980001542717,
        "p95": 3622.2409000620246,
        "percentile_method": "nearest-rank"
      },
      "provider_execution_failures": {
        "count": 1,
        "maximum": 30148.45780003816,
        "mean": 30148.45780003816,
        "median": 30148.45780003816,
        "minimum": 30148.45780003816,
        "p50": 30148.45780003816,
        "p90": 30148.45780003816,
        "p95": 30148.45780003816,
        "percentile_method": "nearest-rank"
      },
      "safe_rejections": null
    }
  },
  "usage": {
    "control": {
      "availability_rate": 1.0,
      "available_scenarios": 24,
      "cached_prompt_tokens": 0,
      "completion_tokens": 1982,
      "derived_total_tokens": 0,
      "known_total_tokens": 24948,
      "prompt_tokens": 22966,
      "provider_reported_total_tokens": 24948,
      "reasoning_tokens": 0,
      "unavailable_scenarios": 0
    },
    "treatment": {
      "availability_rate": 0.9583333333333334,
      "available_scenarios": 23,
      "cached_prompt_tokens": 0,
      "completion_tokens": 1897,
      "derived_total_tokens": 0,
      "known_total_tokens": 26876,
      "prompt_tokens": 24979,
      "provider_reported_total_tokens": 26876,
      "reasoning_tokens": 0,
      "unavailable_scenarios": 1
    }
  }
}
```

## Experiment Integrity

Projection, prompt identity, request count, no-retry, no-fallback, no-replay,
technical, and reference gates are preserved in the structured artifact. Production
prompt source code was not modified.

Exactly 24 provider requests were attempted with zero retries, fallbacks, and replays.
One request timed out after 30 seconds, leaving 23 responses and 23 evaluable outputs.
The sample remains sufficient, but mandatory technical and reference non-regression
gates failed. No timeout replay or replacement was performed.

## Candidate Decision and Adoption Rationale

Decision: `REJECT`. Editorial acceptance decreased from
1/24 to 0/23; the mean quality score decreased; one control pass became a treatment
failure; and technical/reference completion fell from 24 to 23. The frozen candidate
must not be promoted.

## Known Limitations

The experiment is descriptive for one 24-scenario corpus and one model alias. The
single timeout makes that scenario non-comparable editorially. Privacy-safe artifacts
retain structural references, quality dimensions, hashed request identity, latency,
usage, and cost rather than provider prose. No population-level model claim is made.

## Final Recommendation

`Part 7H.1 — Second Prompt Hypothesis Design`
