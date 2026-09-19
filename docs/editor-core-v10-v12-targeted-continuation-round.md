# Editor Core V10 V1.2 targeted continuation round

This is a development training preparation, not a qualification or certification
boundary. Training has not been authorized or executed.

The parent is the preserved V10 V1.2 adapter with content identity
`8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f`
and final checkpoint identity
`6925fca8c5b6c9e94e96255cb21ec9442aff5d0ac2f7bd0f2038ce45475a7dd1`.

The prepared round contains 64 new targeted examples, 64 exact replay anchors
from the V10 V1.2 training corpus, and 32 independent holdout requests. The
holdout answer key is stored separately and holdout requests contain no assistant
message. Eight failure families receive eight new training examples and four
holdout cases each.

The anti-contamination audit compares case identities, canonical INPUT objects,
and normalized five-token shingles against every existing JSONL training,
development, shadow, and remediation corpus plus the 200 frozen R4 requests.
The only authorized overlap is the exact set of 64 replay anchors with their
declared V10 V1.2 source.

Recommended training parameters are one epoch, a new paged AdamW 8-bit optimizer,
learning rate `5e-6`, constant schedule without warmup, BF16, micro-batch size 1,
gradient accumulation 8, maximum sequence length 3072, no packing, and seed
314159. Save a checkpoint every eight optimizer steps and the final adapter.

Evaluation must compare the resulting adapter with both its V10 V1.2 parent and
the retained V10 V1.1 control. The 32-case holdout is the first independent gate;
the existing 72-row development and 240-row shadow corpora remain evaluation-only.
R4 requests, outputs, and human receipts remain excluded from training.
