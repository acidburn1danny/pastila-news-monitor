# EDITOR VNext Minimal Source Authority V0/V1/V2 Runtime Diagnostic v1

## Terminal verdict

`STOP` for adding V1 or V2 to the active normal path. The frozen R2 realizer
completed 144/144 deterministic observations in an unprivileged clean room with
legacy unavailable. V2 reconstructed the same inputs and produced byte-identical
texts to V0 for all 48 cases, so it added components without improving safety,
sufficiency, context size, fallback, or abstention.

V1 reduced mean context from 226.48 to 200.79 tokens, but primary sufficiency
fell from 62.5% to 33.3% and fallback rose from 37.5% to 66.7%. Its deterministic
required-span recall was 75.36%, below the frozen 90% threshold.

## Architecture implication

The active minimal route remains `SourcePacket -> R2 -> verifier -> accepted
setup / extractive fallback / abstain`. EvidencePacket and the bounded selector
remain diagnostic-only. There is no demonstrated overflow niche in this pack:
the largest V0 context was 250 tokens, and V2 was identical to V0.

The deterministic verifier identified residual R2 failures, especially entity
substitution and incomplete numeric reconciliation. These justify keeping the
verifier and fallback, not introducing the tested selector.

Claims are limited to the 48 self-contained development/replay fixtures and the
published deterministic literal/required-span scorer. No naturalistic transfer,
parent selection, promotion, or active VNext integration is claimed.
