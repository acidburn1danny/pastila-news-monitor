# EDITOR text-realizer bake-off: frozen closure v1

## Frozen evidence

- Blind closure: `169984a580322f21e1ad809e747274c9a35dd7ed5ea1b5a4da6397f40640e1d6`.
- Frozen result: `c276fa21189afc169ec9e3ae5d9847d47cb20148cdcc7052f1893d19fa4b4927`.
- R2/Ministral remains the baseline and development parent.
- Qwen3-8B: `REVISE` because it produced no blind functional-Romanian gain over R2.
- Qwen2.5-7B-Instruct: `REVISE` because fallback exceeded 25% and it produced no blind functional-Romanian gain over R2.
- No parent selection, promotion, release, new inference, training, optimizer activity, or historical-holdout access occurred.

The blind map was randomized independently per case. There is no global A/B/C mapping. The frozen result preserves the per-case mapping after controlled unsealing.

## Product interpretation

The observed final setups are already close to the intended EDITOR product behavior. R2 received 48/48 factual-safety passes, 48/48 factual-sufficiency passes, and mean scores of 5/5 for functional Romanian, naturalness, and usable realization. It won seven cases; the remaining 41 were ties. Neither challenger won a case.

The EDITOR contract remains structurally valid. Clarifications should state that two to three sentences are the usual target rather than a reason to drop necessary facts, source wording may be retained when already concise and factual, and factual safety and sufficiency take precedence over paraphrase or compression. These are contract clarifications, not a redesign, and do not alter the frozen evaluation.

Fallback rate remains useful as an autonomy and operational metric, but it is not equivalent to final-output product failure: R2's 35.4% fallback rate coexisted with perfect human scores on this feasibility set.

## Decision

The evidence does not justify a base-model pivot. Text realization is not the dominant demonstrated bottleneck. The remaining architectural question concerns how factual authority should be constructed from SCOUT source packets before realization. The current feasibility evidence uses an oracle source-bound ledger and therefore cannot support a claim of autonomous ledger construction.

## Claim limits

Allowed: conclusions about the three closed deployable model/runtime packages on this 48-case oracle-ledger feasibility set.

Forbidden: autonomous source-to-ledger capability, historical-holdout performance, naturalistic transfer, parent selection, promotion, or release.
