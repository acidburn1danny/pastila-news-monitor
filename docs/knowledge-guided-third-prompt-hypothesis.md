# Knowledge-Guided Third Prompt Hypothesis

## Knowledge validation and review

All 7 ACTIVE knowledge entries were reviewed.
`EK-002` was selected; all others were classified as already exploited or needing
replication. The knowledge base, evidence, fingerprints, and manifest linkage pass.

## Selected finding

`EK-002` records that H2 resolved two quote-preservation failures but introduced four
criterion failures, yielding Net Editorial Utility -2. It is the only selected finding.

## Hypothesis

Adding one balanced-preservation precedence rule will retain non-target quote wording while preventing instruction-compliance, meaning-preservation, and source-authority regressions, producing positive Net Editorial Utility without technical or reference regression.

## Prompt change

`H3-C01`: BALANCED PRESERVATION: Preserve non-target quotation wording, but never at the expense of completing the authorized revision or preserving the original meaning and source authority.

H3 starts from the frozen Part 7C.2 prompt, not from H2. The exact candidate and diff
are frozen in the structured artifact. Production and H2 prompts remain unchanged.

## Traceability chain

Knowledge `EK-002` → H2 experiment `20260728-144134-openai-gpt-4.1-mini-7h2`
→ observed 2 resolved / 4 introduced failures → balanced-preservation change →
expected positive multi-criterion utility. Orphan changes: 0.

## Prompt Delta Budget

One independent behavioral mechanism, one documented semantic change, zero
undocumented changes. Validation: `PASS`.

## Expected benefit and trade-offs

Expected Net Editorial Utility: 2 (a future
testable expectation, not an observed result). Regression and interaction risks are
both `MEDIUM`. Expected affected scenarios: SYN-10, SYN-20, SYN-23.
Potential trade-offs are under-editing an authorized quotation and priority competition.

## Offline readiness

All 24 requests assemble offline with 24 prompt-identity, projection-count, and
projection-set passes. Provider requests: 0.

## Future controlled experiment

The planned Part 7H.4 experiment uses 24 scenarios, 24 requests, and zero retries,
fallbacks, or replays. Only the exact frozen H3 prompt may vary.

## Root conclusion

`KNOWLEDGE_GUIDED_HYPOTHESIS_DESIGNED`

## Recommended next milestone

`Part 7H.4 — Controlled Knowledge-Guided Prompt Experiment`
