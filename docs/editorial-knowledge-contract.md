# Editorial Knowledge Contract

The Editorial Knowledge Base stores only reusable findings extracted from completed,
repository-backed experiments. It does not store ideas, speculative hypotheses, or
prompt drafts. Each immutable entry has a stable `EK-NNN` identity and version,
controlled finding type/status/confidence values, evidence, scenario and category
dimensions, confidence justification, usage guidance, and a deterministic SHA-256
fingerprint.

Supported statuses are `ACTIVE`, `SUPERSEDED`, `DEPRECATED`, and `INVALIDATED`.
Supported findings include prompt behavior, editorial failure, trade-off, causal
relationship, prompt interaction, prompt limitation, best practice, and anti-pattern.
Confidence is `HIGH`, `MEDIUM`, `LOW`, or `INSUFFICIENT_EVIDENCE`.

Every entry must link an experiment, canonical manifest, supporting artifact, and valid
scenario evidence where applicable. Relationships are `SUPPORTS`, `REFINES`,
`CONTRADICTS`, `SUPERSEDES`, `DEPENDS_ON`, or `RELATED_TO`. Broken relationships,
self-links, duplicate IDs/findings, missing evidence, invalid scenarios, fingerprint
mismatches, and circular supersession fail validation.

Entry fingerprints exclude only their own fingerprint field. The knowledge-base
fingerprint excludes its own fingerprint and generation timestamp. Both use canonical
UTF-8 JSON with sorted keys and SHA-256. Evidence paths are repository-relative and
are never fetched or executed.

Historical evolution creates a new version or entry and uses explicit relationships;
previous evidence remains traceable. Superseded and deprecated findings are retained
and never silently rewritten.
