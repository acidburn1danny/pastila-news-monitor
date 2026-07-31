# Editorial Composition Engine

Module 2.8 is the final deterministic planning stage before Script Composer. It converts validated upstream identities, approved segments, rules, and guidance into an immutable `CompositionPlan` containing segment, beat, EpisodeArc, transition, callback, priority, tone, emphasis, rhythm, delivery, conflict, readiness, and traceability contracts.

It owns structural planning only. It performs no generation, I/O, persistence, network, provider, environment, or SQLite work and contains no episode prose.
