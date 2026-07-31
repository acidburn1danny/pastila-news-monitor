# Controlled Provider Benchmark Corpus Compatibility

## Executive Summary

The Part 7A corpus is now compatible with the frozen production Controlled Revision pre-provider pipeline. All 24 scenarios pass production target authorization, instruction validation, invocation construction, OpenAI request projection, and deterministic acceptance-specification validation offline. No provider, SDK, or network request was made.

## Frozen Identity

Scenario IDs `SYN-01` through `SYN-24`, their order, paired 12-category layout, scenario intent, quality dimensions, failure taxonomy, and deterministic fixture expectations are unchanged.

## Target Compatibility

Every scenario authorizes only `story:101`. Each synthetic draft also contains protected opening and closing components, so the target is a strict editable subset and cannot imply full regeneration. Invocation construction uses `ControlledRevisionTarget`, `ControlledRevisionPolicy`, `DraftPreservationRequirements`, `ControlledRevisionRequest`, and `ControlledRevisionInvocation`; no benchmark authorization substitute exists.

## Concrete Instructions

Each category now owns a directly executable Romanian provider instruction. Instructions explicitly scope edits and preserve relevant meaning, facts, quotes, numbers, dates, chronology, structure, or source authority. The existing instruction-class metadata remains for aggregation.

## Deterministic Acceptance

Each immutable scenario contains character-length bounds, protected quotations, numeric facts, dates, structural requirements, exact editable targets, forbidden edit classes, no-op behavior, and proportionality requirements. The compatibility adapter also translates these properties into the existing deterministic editorial acceptance specification without changing its implementation.

## Production Request Projection

The offline validator constructs the exact Part 5N single-attempt `gpt-4.1-mini` configuration, a production invocation, and the real `OpenAIControlledRevisionProjector` request DTO. It never constructs an OpenAI client, resolves credentials, or invokes transport.

## Pricing Specification

`config/controlled-revision-provider-pricing-v1.yaml` freezes USD pricing under `openai-gpt-4-1-mini-2026-07-28`: $0.40 per million uncached input tokens, $0.10 per million cached input tokens, and $1.60 per million output tokens. GPT-4.1 mini has no separately billed reasoning-token rate; if future responses expose reasoning accounting, the versioned estimator treats it at the output rate. The source is the official OpenAI GPT-4.1 mini model pricing page accessed 2026-07-28.

## Compatibility Results

- Scenarios: 24/24
- Categories: 12/12
- Concrete instructions: 24/24
- Production authorization: 24/24
- Production invocation construction: 24/24
- Provider request projection: 24/24
- Acceptance specifications: 24/24
- Pricing resolution: pass
- Provider, SDK, and network requests: zero

## Privacy

Compatibility records contain scenario keys and booleans only. They exclude prompt bodies, synthetic episode prose, provider output, request identifiers, component reference values, and credentials. The pricing specification contains no endpoint or secret.

## Regression

Part 7A, Parts 6A/6B and 5K–5N, the full suite, Ruff, Black, compileall, and pip check pass. Exact counts are retained in the safe artifact.

## Architecture Impact

None. Only benchmark contracts, corpus metadata, offline compatibility helpers, tests, configuration, and documentation changed. Production code is untouched.

## Root Conclusion

`BENCHMARK_CORPUS_COMPATIBLE`

## Final Recommendation

`READY_FOR_PROVIDER_BASELINE`
