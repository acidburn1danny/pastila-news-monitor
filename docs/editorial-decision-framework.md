# Editorial Decision Framework

The Editorial Decision Framework is Scout's evidence-linked judgment layer before
writing. It classifies supplied material, records the primary editorial core,
assigns importance and actions, identifies risks and missing information, and
reports deterministic production readiness. It does not generate or rewrite text.

## Material and factual status

Immutable material units distinguish facts, quotations, context, chronology,
allegations, responses, statistics, consequences, contradictions, uncertainty, and
other editorial roles. Factual status is independent from recommendation confidence:
a confident decision about handling an allegation does not make the allegation true.
Attributed, alleged, and disputed claims retain explicit attribution.

## Editorial core and decisions

The primary core records what happened, involved parties, relevance, consequence,
central tension, factual boundaries, unresolved questions, and supporting material
IDs. Secondary angles cannot replace those evidence references. Decisions use
explicit stage and rank, constrained importance and action vocabularies, rationale,
evidence, Persona principles, relevant tensions, confidence, consequences, and
dependencies.

The 25 canonical rules preserve indispensable facts, attribution, quotations,
uncertainty, source disagreement, verified responses, victim safety, and factual
meaning. They permit compression, combination, delay, or removal only when those
boundaries survive.

## Risks, readiness, and escalation

Risks cover distortion, omission, inference, allegation handling, quotation and
chronology integrity, victim/privacy harm, tone, sensationalism, excess explanation,
weak cores, pacing, source conflicts, missing response or attribution, insufficient
verification, and Profile–Persona conflict.

- `blocked`: critical/blocking risk or missing indispensable dependency.
- `requires_editor_review`: no blocker, but authority escalation is required.
- `ready_with_advisories`: safe to proceed with non-blocking issues.
- `ready`: no blockers, review requirements, or advisories.

Readiness is editorial workflow status, never a guarantee of factual truth.

## Architecture boundary

Plans reference a supplied validated Persona and Philosophy but never mutate them or
Editorial Memory. Renderers reproduce material verbatim for inspection and do not
create a script. Future generation may consume a validated plan as an intermediate
artifact; it must not bypass evidence links, escalation requirements, or factual
boundaries. The package has no provider, network, database, persistence, benchmark,
CLI, or generation dependencies.
