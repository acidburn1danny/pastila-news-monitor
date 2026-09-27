# EDITOR VNext Minimal Source-Bound Verifier Diagnostic v1

This fixture-only diagnostic tests the smallest verifier justified by closed evidence: strict structure, Romanian numeric source binding, actor/entity novelty, and narrow qualification/status anchor preservation.

It emits `PASS_PROVEN`, `FAIL_PROVEN`, or `UNPROVEN`. `UNPROVEN` is not a model failure. A rejected payload is represented only by its SHA-256 and bounded finding records. The payload itself is not persisted in a receipt.

The verifier has no EvidencePacket, selector, factual ledger, general lexical score, required-span gate, NLI, model judge, embeddings, semantic sufficiency judge, or derived numeric reasoning. Qualification and status handling are finite lexical anchors rather than an ontology.

The diagnostic is not integrated into active VNext. Its fixture corpus separates true model failures, historical verifier false rejections, and cases that this minimal verifier cannot prove. Source-preserving fallback copies the complete source only when it is already one to three sentences; otherwise the route abstains.

## Fixture-only closure

- Verdict: `PASS`
- Result identity: `2abd2a882e0759ca44b32b2e086229678a3771acd9f786d1efcd4c59e3c6499e`
- True model failure fixtures: 4/4 correctly classified
- Historical verifier false-rejection fixtures: 3/3 accepted
- Unproven fixtures: 3/3 kept distinct from failure
- Fixture false positives: 0
- Fixture false negatives: 0
- Legacy dependencies: 0
- Model load, inference, optimizer, and training: none

The first diagnostic run exposed an unsound default: an output with no checkable hard anchor could receive `PASS_PROVEN`. The corrective action changed absence of a checkable source anchor to `UNPROVEN`. This prevents “no detected defect” from being treated as proof of factual safety.

The closure supports continued evaluation of this verifier. It does not yet authorize active V0 integration: the actor detector and finite qualification/status markers require measurement against closed naturalistic V0 evidence to establish operational false-rejection and miss rates.
