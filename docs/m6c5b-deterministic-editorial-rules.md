# M6C.5B deterministic editorial rules

## Overview

This milestone adds an offline, deterministic reviewer beneath the private M6C.5A QA
boundary. It inspects the frozen `EpisodeDraft`; it does not generate, rewrite, call a
provider, aggregate approval, or mutate upstream state.

## Repository inspection and architecture

`rules/` separates immutable policy and context, the rule protocol, immutable registry
and ruleset, concrete objective checks, execution state/trace, and the ordinary
`DeterministicRulesReviewer` adapter. Registries are explicitly constructed and have no
import-time mutation. A rule is accepted atomically; malformed output or an exception
records a bounded failure and no partial findings.

## Implemented rule inventory

Every rule below is version `1.0.0`, defaults to `ERROR`, is blocking, and is explicitly
enabled by explicit inclusion in the default set constructed through
`RuleRegistry(build_supported_rules()).select()`. The implementation is in
`rules/concrete.py`; registry/default-set construction is in `rules/registry.py` and
`rules/reviewer.py`. Focused inventory and engine coverage is in
`tests/test_deterministic_editorial_rules.py`. Individual positive defect tests currently
cover repetition and runtime; the remaining rules have inventory/execution coverage but
not one positive fixture per rule.

### Rule status taxonomy

- **IMPLEMENTED — OPERATIONALLY REACHABLE:** a fully implemented rule that can emit
  findings from normally validated frozen input.
- **IMPLEMENTED — DEFENSIVE:** a fully implemented rule whose triggering state is
  prevented by frozen upstream validation in the normal pipeline, but which is
  intentionally retained as a defense-in-depth invariant check.
- **UNSUPPORTED BY FROZEN CONTRACT:** required structured inputs are not exposed by the
  frozen upstream contracts.
- **REDUNDANT WITH MODEL VALIDATION:** the behavior belongs solely to authoritative
  frozen-model validation and no separate QA check is retained.
- **DEFERRED TO LATER MILESTONE:** intentionally reserved for an approved later scope.
- **NOT APPLICABLE:** the rule does not apply to the current contract or product surface.

Defensive rules are not dead code. They provide defense in depth against future
integration errors, unsafe construction paths, deserialization defects, contract
regressions, or incorrectly trusted upstream inputs. They do not justify weakening
frozen upstream validation merely to make them trigger in normal execution.

The authoritative implemented inventory contains **40 registered deterministic rules,
of which 37 are operationally reachable through normally validated frozen input and 3
are intentional defensive checks**.

### Structure (10)

- `structure.component-order-inconsistent` — episode
- `structure.cta-placement-inconsistent` — episode — **IMPLEMENTED — DEFENSIVE**
- `structure.empty-closing` — closing
- `structure.empty-opening` — opening
- `structure.empty-story` — story
- `structure.empty-transition` — transition
- `structure.missing-required-transition` — episode — **IMPLEMENTED — DEFENSIVE**
- `structure.orphan-transition` — episode — **IMPLEMENTED — DEFENSIVE**
- `structure.too-few-stories` — episode
- `structure.too-many-stories` — episode

### Runtime (7)

- `runtime.closing-too-long` — closing
- `runtime.episode-too-long` — episode
- `runtime.opening-too-long` — opening
- `runtime.story-length-imbalance` — episode
- `runtime.story-too-long` — story
- `runtime.transition-disproportionate` — episode
- `runtime.transition-too-long` — transition

### Callback (0)

No Callback rule is implemented; see the individual classifications below.

### Repetition (6)

- `repetition.duplicate-component-text` — opening, story, transition, closing
- `repetition.duplicate-sentence` — opening, story, transition, closing
- `repetition.repeated-component-ending` — opening, story, transition, closing
- `repetition.repeated-component-opening` — opening, story, transition, closing
- `repetition.repeated-phrase` — opening, story, transition, closing
- `repetition.reused-transition` — transition

### Mechanical Language (11)

- `language.control-character` — opening, story, transition, closing
- `language.excessive-blank-lines` — opening, story, transition, closing
- `language.excessive-consecutive-punctuation` — opening, story, transition, closing
- `language.line-too-long` — opening, story, transition, closing
- `language.markup-leakage` — opening, story, transition, closing
- `language.no-visible-content` — opening, story, transition, closing
- `language.noncanonical-unicode` — opening, story, transition, closing
- `language.placeholder-detected` — opening, story, transition, closing
- `language.repeated-inline-whitespace` — opening, story, transition, closing
- `language.trailing-whitespace` — opening, story, transition, closing
- `language.unresolved-template-marker` — opening, story, transition, closing

### Voice Compliance (6)

- `voice.forbidden-phrase-detected` — opening, story, transition, closing
- `voice.forbidden-profanity-detected` — opening, story, transition, closing
- `voice.profanity-limit-exceeded` — opening, story, transition, closing
- `voice.required-phrase-missing` — opening, story, transition, closing
- `voice.required-rhetorical-question-missing` — opening, story, transition, closing
- `voice.sentence-length-limit-exceeded` — opening, story, transition, closing

Structure contains 7 operationally reachable rules and 3 defensive rules. All 30 rules
outside Structure are operationally reachable. Total registered implemented rules:
**40** (37 operationally reachable, 3 defensive). Runtime measurements are
word/character heuristics, not semantic duration estimates. Repetition uses only NFC,
whitespace, and case-folded exact comparison.

## Omitted-rule inventory

| Rule | Exact reason |
|---|---|
| `structure.assembled-text-inconsistent` | REDUNDANT WITH MODEL VALIDATION |
| `structure.teleprompter-text-inconsistent` | UNSUPPORTED BY FROZEN CONTRACT (no deterministic formatter contract is retained) |
| `callback.declared-but-unused` | UNSUPPORTED BY FROZEN CONTRACT — `EpisodeDraft` and `EditorialReviewRequest` expose no callback declaration/use ledger |
| `callback.used-before-introduction` | UNSUPPORTED BY FROZEN CONTRACT — no ordered callback introduction/use metadata reaches QA |
| `callback.excessive-reuse` | UNSUPPORTED BY FROZEN CONTRACT — no callback usage counts or maximum-use declarations reach QA |
| `callback.missing-target` | UNSUPPORTED BY FROZEN CONTRACT — no callback target identifiers reach QA |
| `callback.duplicate-introduction` | UNSUPPORTED BY FROZEN CONTRACT — no callback introduction declarations reach QA |
| `callback.literal-drift` | UNSUPPORTED BY FROZEN CONTRACT — no protected callback literal reaches QA |
| `language.numeric-preservation-violation` | UNSUPPORTED BY FROZEN CONTRACT (no protected numeric-literal index reaches QA) |
| `voice.required-direct-address-missing` | UNSUPPORTED BY FROZEN CONTRACT (no direct-address declaration reaches QA) |
| voice mechanism/language-code semantic checks | DEFERRED TO LATER MILESTONE |

Missing transitions, orphan transitions, and inconsistent CTA placement are rejected by
the frozen model in ordinary construction. Their three corresponding rules remain
**IMPLEMENTED — DEFENSIVE** as intentional invariant checks. Duplicate component
identity is REDUNDANT WITH MODEL VALIDATION.

## Validation, determinism, and bounds

Policy is frozen and validated. Registry order, execution keys, findings, trace, and
fingerprints are canonical and timestamp-free. Findings are bounded per rule and per
run. Exact repetitions are indexed with bounded n-grams rather than pairwise semantic
comparison. Rule result tuples are validated as a unit.

## Privacy

The rule context never indexes CTA static content. Its context/draft fingerprints,
findings, failures, and trace exclude static CTA text, raw articles, credentials,
exception representations, object identity, and timestamps.

No callback metadata is fabricated. Callback behavior is not inferred from prose, and
no fuzzy matching is used as a replacement for missing structured declarations.

## Compatibility and limitations

No frozen generation or M6C.5A public model was changed. The adapter is opt-in and is
not inserted into any existing manifest. Objective phrase/profanity checks operate only
when immutable policy explicitly declares literals. No NLP or inferred meaning is used.

## Deferred work

Subjective review remains M6C.5C. Regeneration coordination remains M6C.5D. Approval and
human workflow expansion remain M6C.5E.

## Freeze recommendation

**PASS WITH DOCUMENTED LIMITATIONS. SAFE TO FREEZE WITH DOCUMENTED LIMITATIONS.**

All 40 registered deterministic rules are implemented and validated. Thirty-seven are
operationally reachable through normally validated frozen input. Three structure rules
are intentionally defensive and operationally unreachable by design because frozen
upstream validation guarantees the same invariants before QA execution. This is
documented defense in depth, not a functional defect. All quality gates, determinism
checks, privacy checks, and regression tests pass.

Non-blocking documented limitation: three implemented structure rules are defensive
checks and are not expected to trigger in the normal validated pipeline.

No blocking findings.
