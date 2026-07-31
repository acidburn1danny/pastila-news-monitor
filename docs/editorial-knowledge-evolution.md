# Editorial Knowledge Evolution Framework

The evolution framework adds immutable history around the Editorial Knowledge Base
without rewriting its entries. Each event records identity, timestamp, previous and
new state, trigger, experiments, manifests, artifacts, reason, confidence transition,
evidence accumulation, evolution version, and deterministic SHA-256 fingerprint.

Every current entry receives a creation backfill from its original repository evidence.
`EK-002` receives one additional `EXPERIMENT_REFINED` event because Part 7H.4 explicitly
classified its causal mechanism as `PARTIALLY_CONFIRMED` and its knowledge outcome as
`REFINED`. Its confidence remains `MEDIUM`; no unsupported confidence change is made.
All other entries remain `ACTIVE`.

Evidence count is the number of distinct experiment, manifest, artifact, and scenario
references known at each snapshot. Confirmation statistics count explicit evolution
triggers rather than inferring them from related entries.

The entry-history fingerprint excludes only its own fingerprint field. The root history
fingerprint additionally excludes generation time. The global timeline sorts immutable
knowledge and relationship events by timestamp and stable event ID. Validators enforce
version continuity, timeline ordering, state continuity, unique events, evidence paths,
fingerprints, and the zero-execution boundary.

Artifacts:

- `docs/artifacts/editorial-knowledge-history.json`
- `docs/artifacts/editorial-knowledge-timeline.json`
- `docs/artifacts/editorial-knowledge-statistics.json`

Future experiments append evidence-driven events; they never edit or delete historical
events. Part 7I.2 can build confidence weighting on these histories.
