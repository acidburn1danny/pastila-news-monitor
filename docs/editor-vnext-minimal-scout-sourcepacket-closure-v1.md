# VNext Minimal SCOUT + SourcePacket Orchestration Closure v1

This closure keeps only the active product path: RSS discovery and capture, conservative deterministic grouping, explicit user event selection, self-contained SourcePacket handoff, R2 V0 invocation, and the structural output boundary.

The runtime is standard-library only and uses SQLite for current operational state. Historical databases and migrations are not required. The acceptance fixture exercises the same RSS/Atom parser, capture, grouping, persistence, selection, and SourcePacket builder as the live path. Network reachability is deliberately outside the deterministic acceptance claim.

Legacy AI ranking, reconciliation history, editorial queues, EventAuthorityBundle, EvidencePacket, selectors, factual ledgers, semantic authority systems, HTML adapters, and desktop applications are not dependencies of this closure.

The frozen acceptance boundary uses two local RSS/Atom feeds and one unrelated article. It demonstrates parser reuse, capture, SQLite persistence, conservative grouping, explicit event-ID selection, self-contained SourcePacket creation, R2 invocation, and structural EDITOR output. It does not claim live source reachability, semantic correctness, verifier enforcement, or production factual acceptance.

All active SCOUT bytes live under `/root/pastila-vnext/v1/runtime/scout-v1`; operational state is created under `/root/pastila-vnext/v1/state/scout-v1`. Acceptance databases, packets, model outputs, and intermediate receipts are ephemeral. The single terminal closure receipt and dependency locks are the persistent evidence.
