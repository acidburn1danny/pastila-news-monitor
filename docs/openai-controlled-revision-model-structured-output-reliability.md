# OpenAI Controlled Revision model structured-output reliability

## Assessment question

Part 5I measures whether explicitly selected models reliably satisfy the frozen
Controlled Revision provider DTO. Structural DTO success is measured separately
from authorization, reconstruction, gateway, and editorial acceptance.

## Frozen configuration

The production prompt, component-shape correction, schema, DTO, projection,
interpreter, authorization, reconstruction, domain models, gateway, runtime,
credentials, timeout, retry, and fallback behavior remain unchanged.

- Schema SHA-256: `3a643d39384e92fddbabd9e176a1cbda6e7bc2539d1a3937c88fdc025f07d31c`
- DTO schema SHA-256: `3973409a1069fd0d9b965aeddb554604dda452bdb570631c443056288fdca6ee`

## Sample plan

The proposed explicit matrix contains `gpt-4.1-mini` and `gpt-4.1`, scenarios
E2E-01 through E2E-04, and five samples per model/scenario, for a maximum of 40
live requests. Ordering is deterministic and interleaved by sample, scenario, then
model. Every trial has one runtime attempt, SDK retries disabled, and no provider
or model fallback. Sampling parameters not already owned by production remain at
provider defaults.

## Metrics

The harness records content-free lifecycle stages, result categories, safe Part 5G
DTO diagnostics, latency, optional token counts, and availability flags. It reports
DTO and end-to-end rates separately and calculates deterministic 95% Wilson score
intervals. External failures remain visible in conservative denominators.

## Privacy and artifacts

The assessment never records source or revised prose, provider output, prompts,
requests, responses, JSON payloads, raw validation inputs, exceptions, component
references, request IDs, credentials, or synthetic secret markers. A completed live
run writes approved metadata only to
`docs/artifacts/openai-controlled-revision-model-reliability.json`.

## Preflight status

I01-I30 pass. Schema, DTO, prompt, component-shape, safe diagnostic, adapter,
runtime, architecture, and scenario checks pass. The dry run loaded the proposed
two-model/four-scenario/five-sample matrix, calculated a 40-request budget, and made
zero provider or SDK requests.

- Focused regression: 196 passed
- Full regression: 907 passed
- Ruff: passed
- Black: passed
- compileall: passed
- dependency validation: passed

## Live status

Live execution is pending explicit confirmation of the model list, scenario list,
runs per scenario, and 40-request maximum. No reliability conclusion is valid until
the configured assessment completes. Current conclusion: `ASSESSMENT_INCOMPLETE`.

Small samples will produce broad confidence intervals. The assessment covers only
the configured synthetic scenarios, does not prove general model reliability, and
does not evaluate retry or fallback policy. Provider behavior may change over time.
