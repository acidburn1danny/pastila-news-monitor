# Editor Core targeted R2 failure-mining pack

This development pack continues from the evaluated targeted R1 checkpoint 8.
It contains 36 new examples, with 12 examples for each of the three failure
classes that remained after independent evaluation: epistemic calibration,
transition without new facts, and unsupported material claims.

The 36 replay anchors are split evenly between the original V10 V1.2 training
corpus and the R1 targeted additions. A new 18-case independent holdout contains
six cases per remaining class. Its targets are separate, are absent from request
rows, and reuse none of the prior holdout targets.

The pack is development material. It creates no training, inference,
adjudication, certification, or promotion authority. The intended next round is
one epoch at learning rate `3e-6`, batch size 1, gradient accumulation 8, BF16,
no packing, and seed 271828, for nine optimizer steps. Training remains stopped
until tokenizer and anti-contamination closure pass.
