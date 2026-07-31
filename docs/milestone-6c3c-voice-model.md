# Milestone 6C.3C — deterministic Pastila Acidă voice model

`VoiceModelBuilder` is a private stage after the generic editorial and commentary
blueprints. It consumes only frozen public inputs and deterministic upstream
artifacts, returns the public `EditorAgentOutputV1` unchanged, and adds a private
`EpisodeVoicePlan` plus `VoiceDecisionTrace`.

The plan contains controlled voice execution metadata: register, orality, rhythm,
marker families, rhetorical-question functions, curiosity timing, humor and sarcasm
ceilings, empathy switches, Romanian expression/reference families, callbacks,
perspective shifts, emotional temperature, endings, and shared repetition budgets.
It never contains generated wording.

Sensitivity comes solely from the explicit upstream commentary classification.
Agency needed for behavior-level roast eligibility comes solely from explicit Scout
event extensions. Missing facts cause a conservative institution-only or prohibited
roast plan. Protected dimensions always prohibit person-level roast, reduce sarcasm,
and require clean language and a non-joke-only ending.

Validation checks flow order, one-to-one story coverage, episode budgets, protected
dimensions, roast eligibility, audience respect, and sensitive-story safeguards.
The implementation uses no NLP, LLM, clock, randomness, external API, persistence,
or semantic guessing. Tests cover integration, controlled vocabularies, safety,
budgets, trace integrity, and reproducibility.
