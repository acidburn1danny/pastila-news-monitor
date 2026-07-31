# Part 7C.2.1 — Pipeline Success Semantics Reconciliation

## Executive Summary

Repository contracts establish that `PIPELINE_SUCCESS` means successful technical
production of a valid `EpisodeDraft`; editorial acceptance is a separate benchmark-only
quality judgment. Part 7C.2 correctly counted 24 technical completions but its funnel
renderer incorrectly copied that count into `editorial_acceptance_passes`. The artifact,
report, and matching history entry now explicitly distinguish 24 technical completions,
24 editorial evaluations, 1 acceptance, and 23 editorial failures. No provider request,
benchmark execution, replay, raw trial, rubric, or production behavior changed.

## Observed Inconsistency

The original Part 7C.2 output reported `pipeline_successes = 24` and
`editorial_acceptance_passes = 1` in the completion report, while the JSON funnel stored
24 for both. The first value was valid under production semantics; the funnel's editorial
value was a rendering defect.

## Evidence Reviewed and Hierarchy

The review followed the required hierarchy:

1. `production_observability.OperationalOutcome` and its stage model.
2. `execute_trial`, `aggregate_results`, `_quality_metrics`, and `_pipeline_funnel`.
3. `test_acceptance_failure_remains_pipeline_success` and operational-validation tests.
4. Part 7C, 7C.1, and 7C.2 structured artifacts and reports.
5. `BenchmarkHistoryEntry` and the Part 7C.2 history record.
6. Part 7D–7G diagnostic, architecture, and implementation evidence.
7. Milestone wording.

The decisive typed/tested evidence explicitly allows acceptance failure alongside
`PIPELINE_SUCCESS`. Editorial acceptance is evaluated only after the gateway has
produced a valid technical result.

## Implemented Pipeline Funnel

1. Scenario preparation — benchmark-only setup.
2. Exact-schema projection checkpoint — benchmark execution gate.
3. Provider request and response — provider boundary.
4. Response-format and DTO validation — technical pipeline.
5. Exact reference authorization — technical trust boundary.
6. Deterministic reconstruction — technical pipeline.
7. `EpisodeDraft` validation/gateway completion — technical pipeline boundary.
8. Editorial evaluation — benchmark-only quality measurement.
9. Editorial acceptance or rejection — benchmark-only quality judgment.

Technical pipeline success ends at a valid `EpisodeDraft`. Editorial evaluation does
not change that operational outcome.

## Success-Term Inventory

| Term | Type/source | Canonical meaning | Includes acceptance? | Historical |
| --- | --- | --- | --- | --- |
| `PIPELINE_SUCCESS` | production and benchmark enums | valid technical pipeline result | no | yes |
| `pipeline_successes` | benchmark artifact | deprecated alias for technical completions | no | yes |
| `technical_pipeline_successes` | reconciled artifact | explicit valid-`EpisodeDraft` count | no | yes |
| `editorial_evaluation_attempts` | reconciled funnel | valid drafts submitted to rubric | no | yes |
| `editorial_evaluation_completions` | reconciled funnel | rubric evaluations with an outcome | no | yes |
| `editorial_acceptance_passes` | quality/funnel | rubric passes | yes | yes |
| `editorial_acceptance_failures` | reconciled funnel | rubric failures | no | yes |
| `editorial_acceptance_rate` | quality metrics | passes divided by evaluable outputs | yes | yes |
| `usable_revision` | scenario evaluation | conjunction of all quality dimensions | yes | yes |
| `quality_sample_count` / `sample_count` | aggregate | technically valid, evaluable outputs | no | yes |
| `quality_sample_status` | benchmark artifact | whether evaluable count reaches 12 | no | yes |
| `safe_rejection` | operational outcome | provider output rejected before technical completion | no | yes |
| `operational_success` | conceptual | synonym for technical pipeline completion | no | indirect |
| `full_benchmark_success` | not defined | no canonical consumer exists | n/a | no |

Generic `success`, `scenario_success`, and `benchmark_success` have no authoritative
stored contract in this benchmark and are not introduced.

## Canonical Definitions

### Technical Pipeline Success

A provider response is DTO-valid, exactly authorized, deterministically reconstructed,
and accepted as a valid `EpisodeDraft` by the gateway. Editorial acceptance is excluded.

### Editorial Acceptance

A technically valid output passes the frozen editorial rubric. It is an independent
quality judgment and cannot be inferred from technical completion.

### Full Benchmark Success

Not defined. No existing consumer needs a combined technical-and-editorial Boolean.
The explicit technical and editorial metrics prevent double counting without adding a
redundant concept.

## Quality Sample Sufficiency

The pre-existing rule in `build_v2_artifacts` is at least 12 `quality_items`: outputs
that completed the technical pipeline and could be evaluated. It is not based on the
number accepted. Part 7C.2 has 24 evaluable outputs and therefore remains `SUFFICIENT`,
despite only one acceptance.

## Part 7H Readiness

Part 7H requires at least 12 technically valid, editorially evaluated outputs, detailed
quality dimensions/failure categories, and uncontaminated reference compliance. Part
7C.2 provides 24 such outputs and 24/24 exact reference compliance. Readiness remains
true; low editorial acceptance is the subject of the controlled prompt experiment, not
a reason to exclude the sample.

## Artifact Reconciliation Method

The offline reconciliation reads only the official Part 7C.2 `trials` array, derives
technical outcomes from `operational_outcome`, derives evaluation and acceptance counts
from stored `quality` records, validates aggregate invariants, and atomically rewrites
derived metadata. Scenario records are serialized unchanged. Schema version increased
from 3 to 4 and an audit-rich `reconciliation` section preserves original values and
the reason for correction.

`pipeline_successes = 24` remains as a deprecated technical alias for backward
compatibility. New canonical fields are `technical_pipeline_successes`,
`editorial_evaluation_completions`, `editorial_acceptance_passes`, and
`editorial_acceptance_failures`.

## Benchmark History Reconciliation

The two older history entries remain byte-equivalent at the entry level. Only the
official Part 7C.2 entry received additive semantic fields. Its existing
`pipeline_success_count = 24` was not numerically changed because it already represented
technical completion. Editorial counts and the sufficiency/readiness rule were added.

## Part 7C.1 Comparison and Root Conclusion

The comparison remains semantically valid when read as technical pipeline advancement:
0 to 24 authorization passes, reconstructions, and technical completions. Part 7G
remediated reference compliance, not editorial quality. Consequently
`REFERENCE_CONTRACT_REMEDIATION_EFFECTIVE` remains correct.

## Affected Artifacts

- Part 7C.2 JSON artifact: schema v4 plus explicit semantics and audit metadata.
- Part 7C.2 Markdown report: canonical funnel and reconciliation notice.
- Benchmark history: additive clarification on the Part 7C.2 entry only.
- This report and its structured reconciliation artifact.

## Files Modified

- Benchmark aggregation/reporting code: fixes future funnel rendering.
- Offline reconciliation utility: deterministic artifact/history regeneration.
- Part 7C.2 artifact, report, and history.
- Focused semantic tests and this documentation.

No production provider, prompt, schema, DTO, authorization, reconstruction,
`EpisodeDraft`, editorial rubric, threshold, or corpus file changed.

## Tests and Regression Results

Focused tests cover the canonical technical boundary, independent editorial outcomes,
aggregate invariants, frozen trial preservation, history-prefix preservation, quality
sample/readiness rules, and Markdown/JSON consistency. Final gate results are recorded
in the structured reconciliation artifact.

## Final Semantic Decision

`PIPELINE_SUCCESS_MEANS_TECHNICAL_COMPLETION`

Reconciliation outcome: `AMBIGUOUS_METRIC_REPLACED_BY_SEPARATE_TECHNICAL_AND_EDITORIAL_METRICS`.

Root conclusion: `PIPELINE_SUCCESS_SEMANTICS_RECONCILED`.

## Recommended Next Milestone

Part 7H — Controlled Prompt Effectiveness Experiment.
