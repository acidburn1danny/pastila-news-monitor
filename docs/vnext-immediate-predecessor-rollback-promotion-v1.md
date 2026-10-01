# VNext Immediate-Predecessor Canonical Rollback Promotion & Prior Canonical Reclassification Boundary v1

This boundary promotes `/root/pastila-vnext/.rollback-pre-contract-e180a1e5` as the sole canonical rollback.
The prior canonical root `/root/pastila-vnext/.rollback-pre-exchange-5e31722e` becomes `HISTORICAL_NON_CANONICAL_RETIREMENT_PENDING_SEPARATE_AUTHORITY`.
Retired-root references are removed. Runtime behavior, workflow contracts, SQLite, graph, R2, and platform bytes remain unchanged.
Prospective installation, rollback, and restore use isolated OverlayFS views. No active or rollback root is modified or deleted.
Installation and retirement remain separate owner-authorized gates.
