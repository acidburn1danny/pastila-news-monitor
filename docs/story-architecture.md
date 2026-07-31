# Story Architecture

Story Architecture is Scout Editor's deterministic intermediate layer between editorial judgment and writing. It converts a validated Editorial Decision Plan, Audience Assessment, and optional Satirical Opportunities into a traceable narrative sequence. It neither generates language nor changes facts, decisions, audience judgments, or voice safeguards.

## Boundaries and ownership

The Decision Framework decides what the evidence means and which editorial actions are justified. The Audience Model identifies comprehension, attention, trust, fatigue, and emotional constraints. Satirical Voice determines permissible targets and mechanisms. Story Architecture assigns evidence references to narrative units, orders those units, and records their purpose. A future Spoken Language Engine may realize the plan as natural Romanian speech, and a future Script Composer may produce text. Neither responsibility belongs here.

The Editor-in-Chief retains final authority over opening, pacing, context, satire, secondary angles, and payoff, subject to immutable factual and safety boundaries.

## Canonical architecture

The canonical identity is `pastila-acida-story-architecture` version `1.0.0`. Its twenty ordered principles require early relevance and editorial core, context on demand, factual setup before satire, visible consequence, evidence-safe chronology and escalation, one primary spine, functional units, economical background, intentional strong beats, protected serious space, logical transitions, earned payoff and closure, one clear takeaway, causal integrity under compression, and Editor-in-Chief authority.

The explicit stages are: opening, orientation, factual setup, context, consequence, development, contradiction, satirical development, escalation, payoff, and closure. Stage rank is a stable semantic contract rather than an incidental enum ordering.

## Narrative structures

A `StoryUnit` is an immutable evidence-reference container. It records unit type, stage and rank, primary and secondary narrative functions, upstream material/decision/core/opportunity identifiers, dependencies, sensitivity, compression policy, attribution, restraint, and review requirements. It contains no hook, transition, joke, punchline, or script prose.

Every plan has exactly one ordered `NarrativeSpine`. Secondary angles remain subordinate and carry explicit placement and review limits. The eight canonical patterns are:

- fact → consequence → contradiction → payoff
- consequence → fact → context → payoff
- official claim → reality contrast → payoff
- chronology → revelation → consequence → payoff
- absurd detail → systemic problem → payoff
- individual case → public pattern → payoff
- accusation → response → evidence → resolution
- serious event → institutional failure → reflection

Patterns are sequencing templates, not genre inference and not generated text.

## Placement contracts

Opening strategies include event-first, consequence-first, contradiction-first, verified-quote-first, concrete-detail-first, chronology-break-first, question-first, and restrained-gravity-first. Every opening references supported units and records audience need, risks, context dependencies, tonal limits, and prohibited interpretations.

Context placements exist only for a documented comprehension dependency. Indispensable context precedes dependent interpretation; optional background may not hide the core. Consequence plans retain evidence and sensitivity boundaries. Satire placements require validated opportunities and completed setup, preserve protected subjects and grave tonal space, and respect Audience and Voice calibration. Transitions state a controlled logical relationship without writing transition language. Causal transitions require evidence and chronological transitions may not distort sequence.

A payoff resolves earlier setup and cannot introduce unsupported facts or explain a joke. Callback payoff requires callback-capable setup. The Audience Takeaway records one evidence-earned recognition; it cannot command opinion, guarantee emotion, or erase uncertainty.

## Compatibility and profile guidance

Decision Plan and Audience Assessment identifiers and semantic fingerprints are validated. Blocked upstream artifacts block architecture; review states propagate. Indispensable material remains represented, while removed or held material cannot re-enter through any placement. Allegations and disputes preserve attribution. Validated Satirical Opportunities remain immutable and are the sole authority for satire.

Only established, evidence-linked Editorial Profile findings may tune permitted preferences. Emerging findings cannot change canonical defaults. Guidance cannot remove indispensable evidence, distort chronology or causality, or bypass Audience or Voice safeguards. Contradictory established guidance requires Editor-in-Chief review.

## Readiness

Readiness is derived with strict precedence:

1. `blocked` for upstream blockers, structural dependencies, absent core/spine, or critical/blocking risks.
2. `requires_editor_review` for upstream or local review requirements and contradictory guidance.
3. `ready_with_advisories` for non-blocking risks or advisories.
4. `ready` only when every dependency is satisfied and no review or advisory remains.

Supplied readiness is checked against this deterministic calculation.

## Validation, rendering, and fingerprints

Validation checks canonical identity and ordering, unique identifiers, complete upstream references, acyclic prerequisites, spine order, opening support, early core, evidence-linked consequence and takeaway, validated satire, transition logic, payoff setup, profile boundaries, and absence of upstream mutation or generated prose.

Reference-only renderers produce deterministic UTF-8 text for the canonical architecture, pattern selection, and plan. Semantic SHA-256 fingerprints normalize unordered evidence/risk collections while preserving meaningful principle, stage, spine, transition, and setup-to-payoff order. There are no timestamps, paths, network calls, persistence, AI calls, or hidden state.
