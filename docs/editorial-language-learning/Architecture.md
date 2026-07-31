# Architecture

## Responsibilities

`models.py` owns immutable contracts; `engine.py` pure derivation; `validator.py` acceptance; `fingerprint.py` semantic identity; `render.py` reference-only presentation; and `readiness.py` dependency propagation. The pipeline is correction import → ordered graph → observation → aggregation → evidence/counter-evidence → derived confidence → inactive candidate → accepted preference → profile → advisory guidance.

## Dependencies, limitations, and guarantees

Relationships use identifiers rather than object mutation. There is no clock, random source, provider, repository, or generated-language dependency. Every stage preserves lineage and fingerprints; historical evolution creates a new artifact retaining the old sequence as a prefix.
