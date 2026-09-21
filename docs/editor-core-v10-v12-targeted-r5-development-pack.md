# Editor Core V10 V1.2 targeted R5 development pack

R2 step-9 remains the development parent. R3 and R4 are rejected as parents.
R4's independent comparison showed attribution improvements on cases 21 and
23, a regression on case 19, and unresolved behavior on cases 15 and 17.
These cases inform the design only. Their frozen requests and targets are not
copied into R5 training.

R5 contains 12 newly authored examples: six attribution/denial/finality
repairs and six preliminary/contest/pending gain guards. Twenty-four
deterministic replay anchors come only from accepted V10, R1 and R2 training
sources, eight per source. The training corpus totals 36 rows. A separate
12-case holdout balances the two patterns and keeps answer keys outside the
future inference runtime. The holdout is for development comparison against
R2, not for training or release certification.

The proposed recipe is one epoch with fresh optimizer state, BF16, no packing,
micro-batch one, gradient accumulation six, six expected optimizer steps, and
constant learning rate `5e-7`. This is a conservative hypothesis after R4's
`1e-6` round improved two cases but introduced a regression. Training is not
authorized by this pack. A future executable route must bind the published
dataset/config identities and pass a fresh pre-training preflight.

Dataset closure requires byte-exact rebuild, tokenizer/EOS audit under the
frozen rootfs, source and replay projection checks, and anti-contamination
against prior frozen holdouts and retained corpora. The R5 holdout must be
evaluated independently against R2 and any R5 candidate. R2 remains parent
unless the new candidate improves semantics without relevant regressions.
