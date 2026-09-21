# Editor Core V10 V1.2 targeted R6 development pack

R2 step-9 remains the only development parent. R3, R4, and R5 remain rejected
as parents. On the frozen R5 development holdout, R2 and R5 each preserved the
epistemic distinctions in 12/12 responses, while 10 responses were identical.
R5 changed only cases 13 and 15, with weaker Romanian attribution wording and
no semantic gain. Several R2 attribution sentences were also ungrammatical.
This is a development failure cluster; no frozen holdout target is a training
label for R6.

R6 authors 18 new examples, six each for petition attribution, contested
preliminary reports, and witness attribution. Every target uses a grammatical
past-tense attribution, preserves the allegation as an allegation, keeps the
subject's response separate, and states the unresolved procedural status.
The 18 replay anchors come deterministically from accepted V10, R1, and R2
training sources, six from each. R3/R4/R5 adapters and holdout targets are
excluded. The combined training corpus has 36 rows.

A distinct 12-case holdout has four cases per pattern. Its requests and answer
key are separate, and the key must not be mounted in a future inference
runtime. The holdout is for independent R2-versus-R6 development comparison,
not training or release certification. Evaluation must check grammar and
source attribution as well as JSON structure, factual fidelity, denial or
contest, and non-finality. Lexical markers alone cannot select a parent.

The proposed recipe is one epoch, a fresh paged AdamW 8-bit optimizer,
micro-batch one, gradient accumulation six, six expected optimizer steps,
BF16, no packing, constant learning rate `5e-7`, and seed `314159`. Keeping
the R5 learning rate isolates the hypothesis that broader grammatical
examples and replay coverage address the observed weakness. This config is
prepared only; training and optimizer creation are unauthorized here.

Before any future run, require byte-exact rebuild, replay provenance, source
and train/holdout anti-contamination checks against the frozen R2–R5
holdouts and retained corpora, plus tokenizer/EOS and token-budget closure.
R2 remains parent unless independent semantic evidence demonstrates a
meaningful gain without relevant regression. Stable attribution behavior
belongs in weights; current authority and source facts stay in runtime input.
