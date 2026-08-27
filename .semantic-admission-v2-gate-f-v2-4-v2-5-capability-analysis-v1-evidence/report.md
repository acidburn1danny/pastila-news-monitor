# Semantic Admission V2 — Gate F V2.4/V2.5 capability analysis

## Conclusion

The evidence supports stopping additive single-pass prompt patching. V2.4 safely rejected Case 10 but chose the wrong semantic classes; V2.5 preserved Case 01 yet changed Case 10 to an unsafe PASS. Both used the same model, input, constrained grammar, and reason namespace. The Case 10 rendered prompt grew from 6,443 to 8,920 bytes, but length alone is not proven causal.

The strongest current explanation is instruction competition inside a single pass. V2.5 combined creative-scope protection, exhaustive proposition discovery, matched-event deltas, negative evidence, proposition grouping, status ranking, and span rules. Its suppression of spurious motive/causality coincided with suppression of valid certainty/timing/stakes detection.

## What is established

- Case 01 passes under both candidates.
- V2.4 rejects Case 10 for wrong reasons.
- V2.5 unsafely passes Case 10.
- The post-generation span validator did not cause the PASS and cannot recover omitted findings.
- Both model outputs satisfied the constrained transport contract.

The evidence does not establish that prompt length alone caused the regression, that the model has a hard semantic capability limit, or that a shorter prompt would generalize.

## Candidate disposition

V2.5 must remain stopped. V2.4 is a safer empirical reference, not a deployable fallback: Run 4 showed false factual rejections and widespread wrong reasons. Neither candidate is runtime eligible.

## Recommended architecture direction

The next work should be design-only staged Gate F feasibility, not another prompt candidate.

Stage P would extract and align source-grounded real-world commitments without deciding admission or choosing FSEM codes. A deterministic boundary would validate schema and exact source membership only. Stage C would classify validated commitments while still receiving the original immutable authority and candidate. It must not treat ledger omission as proof of safety.

This decomposition makes proposition discovery, scope, event-axis mutation, grouping, and classification separately auditable. It costs two model calls per Gate F evaluation and therefore needs an explicit call ceiling and fail-closed precedence. Any malformed, uncertain, incomplete, or source-invalid stage must abstain.

## Alternatives

- More additive prompt patching: reject as the next step.
- Compressed single-pass prompt: retain only as a future control, not the preferred architecture.
- Parallel specialist classifiers: defer until proposition extraction is proven.
- Lexical or deterministic semantic routing: prohibit.

## Authority

Analysis only. No staged design, candidate implementation, inference, runtime, Gate S, curriculum, or training authority is granted.
