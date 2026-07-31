# Spoken Communication Engine

The Spoken Communication Engine is Scout Editor's language-neutral policy layer for transferring approved meaning through speech. Its canonical identity is `pastila-acida-spoken-communication-engine` version `1.0.0`.

## Responsibility boundary

The Decision Framework determines justified editorial meaning. Story Architecture determines the narrative units and their order. This engine determines how information should travel through sequential spoken communication. It does not realize Romanian or any other language, and it does not create sentences, vocabulary, syntax, dialogue, transitions, humor, hooks, punchlines, or scripts.

Romanian conversational realization belongs to Module 2.7B. Script composition policy and eventual text generation remain downstream responsibilities.

## Canonical principles

Twenty ordered principles make comprehension primary, acknowledge sequential speech and limited working memory, keep dependencies local, grow complexity gradually, use variation, pauses, rhythm, and emphasis intentionally, require recognizable setup for callbacks and payoffs, preserve orientation, value communication quality over speed, and retain Editor-in-Chief authority.

## Policy models

`WorkingMemoryModel` contains explicit editorial capacity heuristics for concepts, entities, references, context, numbers, and carry-over. They are not neuroscientific claims. Overload thresholds and recovery strategies restore orientation before new information arrives.

`CommunicationFlowModel` separates orientation, fact, context, consequence, emotion, reflection, satire, payoff, and closure dependencies. `RhythmModel` and `PauseModel` govern cognitive timing rather than performance, punctuation, or wording.

`AttentionModel` describes gain, preservation, fatigue, recovery, reset, and overload without predicting listener behavior. `OrientationModel` keeps topic, speaker, timeline, entity, context, and reasoning position visible.

`ReferenceContinuityModel` governs introduction, continuation, retirement, refresh, ambiguity prevention, and proportionate recall support. `CommunicationContinuityModel` preserves topic, reasoning, context, emotion, satire, and closure continuity.

`CommunicationTransitionModel` describes reasoning movement between fact, context, contrast, cause, effect, chronology, reflection, satire, callback, and payoff. It contains no transition language. `PayoffTimingModel` requires recognized setup and prevents premature payoff. `EmotionTimingModel` changes pacing boundaries without generating emotional wording.

`TeleprompterCognitionModel` models reading, visual, breathing, working-memory, and scanning continuity. It produces no layout, rendering, or formatting instructions.

## Risks and readiness

Communication risks cover listener and memory overload, attention collapse, orientation loss, reference ambiguity, callback and transition overload, rhythm monotony, pause starvation or excess, emotional instability, fragmentation, late clarification, premature complexity, and teleprompter overload.

Readiness is derived in this order:

1. `blocked` for explicit blockers and blocking or critical risks.
2. `requires_editor_review` for any major review requirement.
3. `ready_with_advisories` for non-blocking risks or advisories.
4. `ready` only when no findings remain.

## Profile integration

The engine exposes bounded tuning points for pacing, rhythm, pause and callback density, communication tempo, attention recovery, explanation density, and transition density. It does not implement learning. Only established, evidence-linked guidance is accepted, and guidance cannot change Story Architecture, factual content, or Persona, Philosophy, Voice, Audience, and Decision safeguards.

## Lineage and determinism

A `CommunicationAssessment` links to an immutable Story Architecture Plan using its architecture identity, version, and semantic SHA-256 fingerprint. Validation prevents upstream mutation, generated content, language specialization, and teleprompter formatting.

All renderers use stable UTF-8 output without timestamps or examples. Fingerprints normalize unordered risk and guidance collections while preserving meaningful canonical principle order. This package has no provider, network, persistence, CLI, benchmark, or prompt dependency.
