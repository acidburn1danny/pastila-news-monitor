# Readiness

## Responsibilities and contract

Readiness precedence is `blocked`, `requires_editor_review`, `ready_with_advisories`, then `ready`. A blocked compatibility dependency or blocking issue blocks the session; review issues require review; advisories remain runnable.

## Dependencies, limitations, and guarantees

Sessions capture immutable upstream readiness. Validation recomputes readiness and rejects manual inconsistency. Readiness never erases diagnostics, promotes preferences, or bypasses editor authority.
