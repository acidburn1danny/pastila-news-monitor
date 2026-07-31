# Causal Editorial Trade-off Analysis

## Scope and evidence

This offline analysis covers all 24 paired Part 7H.2 scenarios. It preserves the
official `REJECT` / `H2_PROMPT_INEFFECTIVE` decision and makes no provider requests.

## Scenario-level findings

Twenty-one scenarios had unchanged criterion failures. `SYN-10` and `SYN-23`
resolved `quote_preservation` but remained rejected under pre-existing authority,
meaning, and instruction failures. `SYN-20` introduced `editorial_acceptance`,
`instruction_compliance`, `meaning_preservation`, and
`source_authority_preservation`, moving `PASS_TO_FAIL`.

## Editorial trade-off matrix

| Category | Baseline | Treatment | Delta | Classification | Confidence | Likely cause |
|---|---:|---:|---:|---|---|---|
| editorial_acceptance | 23 | 24 | 1 | INCREASED | LOW | Prompt interaction |
| instruction_compliance | 23 | 24 | 1 | INCREASED | LOW | Prompt interaction |
| meaning_preservation | 23 | 24 | 1 | INCREASED | LOW | Prompt interaction |
| quote_preservation | 2 | 0 | -2 | ELIMINATED | MEDIUM | Prompt wording |
| source_authority_preservation | 23 | 24 | 1 | INCREASED | LOW | Prompt interaction |

Primary taxonomy movement is retained separately in the structured matrix. In the
two quote scenarios, `SOURCE_AUTHORITY_DRIFT` became primary because quote failure
was removed; the underlying authority criteria were already failing.

## Net Editorial Utility

Formula: resolved scenario-criterion failures minus introduced scenario-criterion
failures. Resolved: 2; introduced:
4; net utility: -2.
This supplements but never replaces frozen editorial acceptance.

## Causal attribution and hidden trade-offs

The quote effect has `MEDIUM` confidence: both targeted paired cases improved, but
there was no repeated or factorial provider trial. The four SYN-20 regressions have
`LOW` confidence because prompt interaction, provider stochasticity, and benchmark
variance cannot be separated. Evidence supports failure substitution and a
compensating failure; prompt saturation is not supported.

## Observational dependency graph

The graph contains 7 nodes and 4 observational
edges. Edges are labeled only `LIKELY_CAUSES` or `POSSIBLY_CAUSES` and retain scenario
evidence and uncertainty.

## H2 assessment

Hypothesis correct: **YES** under this corpus (`QUOTE_MUTATION` 2→0).
Production candidate: **NO** because acceptance decreased 1→0, mean score decreased,
and aggregate editorial improvement failed.

## H2 causal narrative

H2 successfully reduced observed quote mutation in both targeted control cases. Those cases still failed on pre-existing source-authority criteria, while SYN-20 newly failed four criteria and moved pass-to-fail. The trade-off prevented aggregate editorial improvement. Evidence for the targeted effect is medium; attribution of the SYN-20 regression is low-confidence because provider stochasticity and benchmark variance remain plausible.

## H3 design guidance

H3 may address prompt-responsive preservation interactions, but this milestone does
not design it. Source-authority causality and SYN-20 reproducibility require more
evidence; independent criterion gating and multi-objective experiments are possible
architectural design-space items.

## Root conclusion

`EDITORIAL_TRADE_OFFS_CHARACTERIZED`

## Recommended next milestone

`Part 7H.3 — Third Evidence-Derived Prompt Hypothesis`
