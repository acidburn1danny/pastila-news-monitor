# Editorial Knowledge Lifecycle

Editorial knowledge is versioned evidence, never permanent truth. The canonical states
are `PROPOSED`, `ACTIVE`, `REFINED`, `SUPPORTED`, `SUPERSEDED`, `DEPRECATED`, and
`INVALIDATED`.

Deterministic evidence rules currently support:

- `PROPOSED + STATUS_TRANSITION → ACTIVE`;
- `ACTIVE|REFINED + EXPERIMENT_CONFIRMED → SUPPORTED`;
- `ACTIVE|SUPPORTED + EXPERIMENT_REFINED → REFINED`;
- `ACTIVE|SUPPORTED + EXPERIMENT_CONTRADICTED → REFINED`.

Unsupported transitions fail closed. Supersession, deprecation, and invalidation remain
available lifecycle states but require future explicit evidence rules; the framework
does not infer them from rejection or partial confirmation.

Confidence is tracked in every before/after snapshot. A confidence change requires
experiment evidence and justification. Confidence may increase or decrease; status
and confidence are independent dimensions.

Relationship evolution is recorded separately with immutable `ADDED`/future removal
events. Current relationships are backfilled as `ADDED`; no removal is fabricated.
