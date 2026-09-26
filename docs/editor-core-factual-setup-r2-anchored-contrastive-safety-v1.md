# EDITOR R2 Anchored Contrastive Safety Diagnostic v1

## Purpose

This development-research diagnostic tests whether explicit rejection of
minimal factual errors and explicit anchoring to R2 logits can separate
learning from retention better than positive-only T1/S0 weighted SFT.

It has no development-parent, promotion, release, or naturalistic-transfer
authority. R2 step-9 remains the development parent. The weighted-SFT T1/S0
line is closed and appears only as a frozen reference condition.

## Factorial

The design is `2 contrastive levels × 2 R2-KL levels`, with the same three
seeds (`161803`, `271828`, `314159`), S0 recipe, R2 parent, row order, corpus,
and frozen evaluator in every cell.

| Arm | Pairwise rejection | R2 KL | Role |
|---|---:|---:|---|
| P0/K0 | no | no | frozen existing T1/S0 reference |
| P1/K0 | yes | no | contrastive effect |
| P0/K1 | no | yes | retention effect |
| P1/K1 | yes | yes | interaction |

The 48 corrective rows produce byte-bound chosen/rejected pairs. Each rejected
response changes only the editorial `text` value and instantiates exactly one
failure class. The 24 replay rows bind online frozen-R2 forward KL to the
editorial text tokens and terminal EOS. Reference logits are not persisted in
the design pack.

## Gradient conflict probe

The probe measures corrective versus replay-preservation gradients for six
failure classes across attention/MLP groups in early, middle, and late model
depths. Replay cross-entropy is used for the at-R2 conflict measurement because
R2-to-R2 KL has zero gradient at equality. KL curvature is measured after a
non-mutating functional virtual corrective displacement; no optimizer is
created and no parameter is changed.

Required receipts report gradient norms, cosine values, strong conflicts,
pairwise-margin gradient norms, and virtual-step KL drift. Missing, nonfinite,
or zero required gradients fail closed.

## Decision rules

`STOP` applies to any material factual, epistemic, or replay regression, any
novel actor or degeneration, or an invalid gradient probe. `REVISE` applies
when pairwise margins improve but retention fails, or when strong negative
gradient conflict remains unresolved. `CONTINUE_RESEARCH` requires replicated
development gain in at least two seeds, positive margins in all six failure
classes, full replay retention, and no material safety regression.

The current boundary is fixture-only. Model load, backward, optimizer creation,
training, inference, historical holdout access, and parent selection remain
unauthorized.
