# Controlled Revision Quality Baseline

## Executive Summary

Part 7A adds an offline, deterministic quality benchmark independent of the production runtime. It evaluates 24 synthetic scenarios across 12 categories using property checks rather than exact-output comparison. It performs no provider or SDK calls and changes no production boundary.

## Objectives

Provide a stable baseline for future prompt, model, evaluator, reconstruction, and editorial-policy comparisons while keeping production frozen.

## Non-Objectives

No prompt/model optimization, provider experiment, retry/fallback, schema/DTO/acceptance redesign, or production rollout is included.

## Benchmark Design

Every immutable scenario contains a synthetic `EpisodeDraft`, a candidate, bounded pipeline observations, authorized component kinds, an instruction class, protected properties, and an expected bounded result. Expected prose is never defined. The runner evaluates the corpus in `SYNTHETIC_FIXTURE` mode with a fixed zero duration for byte-reproducible results.

## Scenario Categories

The corpus contains two cases—one expected success and one failure edge—for each of: minimal clarity, grammar/flow, substantial rewrite, protected structure, source authority, quote preservation, numeric preservation, temporal preservation, multi-component revision, high-constraint revision, no-change required, and adversarial ambiguity.

## Evaluation Dimensions

Structural, DTO, authorization, reconstruction, EpisodeDraft, editorial acceptance, meaning, structure, quote, numeric, temporal, source authority, no-op, instruction, and proportionality dimensions are scored independently.

## Failure Taxonomy

The repository-owned enum contains exactly the 21 required categories, including `USABLE_REVISION`. Deterministic precedence guarantees one terminal category without free-form labels.

## Benchmark Metrics

The aggregate includes scenario/category counts, pass rates for all required dimensions, usable revision rate, failure distribution, category scores, overall score, fixed evaluation duration, and consistency checks.

`USABLE_REVISION_RATE` requires DTO, authorization, reconstruction, EpisodeDraft, editorial acceptance, meaning, and protected-structure passes. The synthetic baseline is 0.625 (15/24); cases may remain structurally usable while correctly receiving a non-usable editorial quality category such as unnecessary rewrite.

## Deterministic Evaluators

Evaluators use NFC/casefold whitespace normalization, exact protected token/quote/date checks, extracted numeric-token preservation, EpisodeDraft story/transition topology, `SequenceMatcher` proportionality with `autojunk=False`, no-op equivalence, and bounded observed pipeline flags. No LLM judge is used.

## Aggregate Results

All 24 expectations match. Twelve canonical success fixtures classify as usable; three editorial-property edges remain usable under the primary structural definition; nine safety/property edges fail usability. Exact rates and distributions are recorded in the safe artifact.

## Privacy Model

The committed artifact contains aggregate numbers, enum names, and gate results only. It contains no scenario prose, prompts, provider output, URLs, request IDs, component references, credentials, or episode identifiers. Corpus text is purpose-written synthetic Romanian material.

## Fixture Baseline

The corpus exercises perfect/good revisions, editorial weakness, excessive or unnecessary change, meaning drift, protected structure/fact/quote/numeric/temporal mutation, unauthorized change, and structural failure. These fixtures validate evaluator discrimination rather than provider quality.

## Future Provider Integration

`RevisionBenchmarkRunner` exposes a future provider mode but rejects it deterministically. The Part 7B compatibility milestone adds concrete instructions, production-valid single-story target subsets, deterministic acceptance specifications, offline production request projection, and versioned benchmark pricing while preserving all scenario IDs, ordering, categories, intent, dimensions, and failure taxonomy. Provider execution remains separately authorized and disabled here.

## Regression

Part 7A focused tests, Parts 6A/6B and 5K–5N regressions, the full suite, Ruff, Black, compileall, and pip check pass. Exact counts are stored in the artifact.

## Findings

- The 24-case corpus satisfies the requested initial size and category balance.
- Property-based evaluation is deterministic and avoids brittle exact prose matching.
- Aggregate reports are content-free and reproducible.
- Provider mode remains deliberately disabled until a separately authorized baseline.

## Architecture Impact

None. The package is an offline consumer of immutable synthetic domain objects and has no production composition path.

## Root Conclusion

`QUALITY_EVALUATION_FOUNDATION_COMPLETE`

## Final Recommendation

`READY_FOR_CONTROLLED_PROVIDER_BASELINE`
