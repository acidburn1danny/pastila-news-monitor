# VNext VOICE STOP_FACTUAL_DRIFT Closed-Evidence Taxonomy v1

This publication-safe checkpoint classifies the 74 frozen `STOP_FACTUAL_DRIFT` receipts without changing any review verdict, score, receipt, inference output, or terminal rule. It is bound to the published 216-item review, scoring closure `a94d44bcf6e677d62a7715a1631544e7f6659a59d277fd674e46bc51f25ac768`, and terminal result `5f521de2625e73db9d6958536b57799b190a0583fc26e2c03fea1fbaf8923ea3`.

The taxonomy result identity is `d86681d1eda554357077bbacd8cb64ae4dce21b7a3977e041b6ee6e966f01530`.

The receipt-weighted closure is `27 + 44 + 3 = 74`: R2/Ministral step-9 has 27 stops, Qwen3-8B non-thinking has 44, and Qwen2.5-7B-Instruct has 3. The taxonomy contains 24 unsupported concrete additions, 9 numeric mutations, 9 epistemic or procedural recasts, 15 unsupported causal or evaluative assertions, 12 figurative implications with a factual reading, and 5 `EVIDENCE_LIMITATION` receipts.

The five limitations consist of three Qwen3 receipts whose normative label commentary has no preserved reviewer rationale and two Qwen3 receipts for a byte-identical parliamentary commentary that received `PASS` in the third seed. Their frozen STOP verdicts remain unchanged, but the checkpoint makes no stronger causal claim about them.

This taxonomy demonstrates observable source-bound failure mechanisms. It suggests, but does not prove, that one-pass commentary generation blurs factual anchors and rhetorical realization. Internal model causes, figurative-commentary false-rejection rate, and reviewer rationale remain undetermined. `STOP_ALL_CANDIDATES` remains active, no candidate is selected, and `LEGACY_DEPENDENCY_COUNT` remains zero.
