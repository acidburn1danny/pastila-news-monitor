# V15 attempt execution boundary

This is a separate signed source and runtime binding over the published V15
driver authority and preflight. It preserves the V13 qualification generation,
2,400 rows, 12 checkpoints, V14 runner limits, V14 terminal evidence, and the
V15 ext4 driver snapshot. It grants no candidate execution or attempt.

The V15 executor projects the validated V14 comparative mechanics to the V15
shell. It passes the frozen qualification identity and all 16 shell arguments,
including the snapshot path, manifest helper path, and helper SHA256. The V15
validator accepts only V15 executable source keys. The executor checks the
new signed boundary and runs the published V15 preflight before the inner
comparative preflight. Its output lock is an exclusive Linux flock. An attempt
is consumed only when `attempt.json` is durably published with a no-clobber
hard link under that lock. The first V15 shell subprocess follows that write;
there is no candidate execution before it.
Any later invocation with a nonempty output fails closed. Accepted checkpoints
remain evidence of the consumed attempt; this boundary does not authorize a
restart or another execution after `attempt.json` exists.

The fixture smoke uses a distinct temporary directory under `/tmp` and never
invokes the candidate shell or model. It proves that a second process cannot
own the same output and that an existing fixture `attempt.json` cannot be
overwritten. The real V15 output remains empty. A terminal fixture process
checks nonzero exit propagation. Smoke evidence is not qualification evidence.

The signed boundary is pre-consumption only. Local materialization, tests,
signature verification and audit do not authorize a candidate or attempt.
Commit, push, a post-push audit, a fresh final preflight and owner authorization
are distinct later steps.
