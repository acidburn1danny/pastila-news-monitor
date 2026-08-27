# Semantic Admission V2 — Gate F V2.4 candidate and zero-inference preflight

## Outcome

The evaluation-only Gate F V2.4 prompt/contract candidate is complete. Zero-inference identity, terminal-padding, request-construction, strict-schema, reason-namespace, and constrained-trie compatibility checks passed.

No model was loaded or invoked. No probe, provider call, generation, runtime change, curriculum exposure, or training occurred.

## Candidate semantic behavior

V2.4 implements the frozen proposition-and-scope design:

- Inventory every real-world proposition carried through assertion, presupposition, entailment, or necessary implication.
- Keep contained metaphor, analogy, personification, counterfactual language, hyperbole, wordplay, emotive color, and editorial evaluation inside protected creative scope.
- End that protection when the construction embeds, presupposes, entails, necessarily implies, or returns to an unsupported real-world proposition.
- Classify every unsupported proposition by its own semantic head, including embedded heads, rather than nearby tone or the sentence's surface head.
- Emit separate decisive and materially supporting records for all governed proposition classes.

## Preserved boundaries

The Core V1.2 model, constrained runner, streaming grammar, strict response parser, reason-code namespace, immutable factual authority, gate precedence, and fail-closed behavior are unchanged. Gate S remains unchanged and separate.

The exact acceptance contract preserves PASS for Cases 01, 02, and 04 and the frozen governed reason sets for Cases 03 and 05–10. Expected labels are evaluation evidence only and do not enter rendered prompts.

## Zero-inference evidence

- Gate F candidate evaluator: `abc7441d98b387d76de3b176068a4a93235f0f46be6dad30b7873dc0e26b1bba`.
- Execution prompt identity: `sha256:aed34f51c1c56c53b01347074daae234271b820fe35abc20db2d4af9618f0861`.
- Ten exact case requests and rendered prompts were bound.
- Three canonical response forms, including a three-reason factual failure, reached terminal states under the unchanged constraint.
- Gate S identities remained `313c6817c7c2ddf75c736dd2c823e25f8ceaf7ac295e09625415f23f32a66b51` and `sha256:db09a481768e6d1c021b8eacac23be8449288993bec7eaa5ea4ad96866e8b2dc`.
- Executor invocations, model calls, and provider calls: zero.

## Authority boundary

This bundle authorizes no model probe. It grants no Core/Voice generation, Gate S, runtime, production, curriculum, or training authority.

## Recommended next step

After owner review, authorize only the frozen two-case Gate F probe defined by the remediation design: the mandatory positive Case 01 and one hard factual-return negative. Freeze its exact case choice, expected evaluation annotations, identities, call ceiling, and durable evidence path before execution. Do not run Gate S or the full ten-case contract yet.
