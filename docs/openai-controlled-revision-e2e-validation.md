# OpenAI Controlled Revision provider-backed E2E validation

Part 5 validates four short, synthetic Romanian revision scenarios through the
frozen production OpenAI composition, provider-neutral runtime, interpreter, and
Controlled Revision gateway. It contains no production news or user content.

The harness is standalone and never runs under normal pytest or CI. It loads the
approved model from `config/config.yaml` and resolves `OPENAI_API_KEY` through the
environment or repository `.env` fallback. It uses one attempt and one fresh
execution-scoped SDK client per scenario. SDK retries, provider fallback, and model
fallback remain disabled.

Dry run with zero provider requests:

```powershell
.\.venv\Scripts\python.exe scripts\validate_openai_controlled_revision_e2e.py
```

Explicit four-request live validation:

```powershell
$env:SCOUT_RUN_LIVE_OPENAI_E2E='1'
.\.venv\Scripts\python.exe scripts\validate_openai_controlled_revision_e2e.py
Remove-Item Env:SCOUT_RUN_LIVE_OPENAI_E2E
```

The target and absolute milestone budget are four live requests. There is no
contingency request. The harness stops at the first failed scenario and never
retries it.

Assertions are deterministic and scenario-specific: normalized required phrases,
exact values, ordered stage markers, narrow forbidden-fact sets, authoritative
fingerprints, domain gateway validation, and safe-report/observer inspection. They
do not claim general hallucination detection or subjective editorial scoring.

Only content-free counters, availability flags, durations, classifications, and
token usage are printed. Credentials, sources, revisions, instructions, prompts,
provider request IDs, raw responses, and raw exceptions are never printed.

External failure categories include configuration, authentication, authorization,
model access, schema rejection, transport, timeout, rate limit, provider
unavailability, refusal, and incomplete response. Domain failures include malformed
structured output, interpretation, lineage, output-contract, editorial
preservation, editorial scope, and safe reporting failures.

After live validation, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_openai_controlled_revision_adapter.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_ai_provider_adapter_runtime.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_ai_provider_adapter_architecture.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check .
.\.venv\Scripts\python.exe -m compileall -q src tests scripts
.\.venv\Scripts\python.exe -m pip check
```

## Corrected provider-output path

The exercised production path is:

`ControlledRevisionInvocation` → OpenAI projection → Responses API →
`OpenAIControlledRevisionProviderOutput` validation → exact reference
authorization → deterministic `EpisodeDraft` reconstruction → normal domain
validation → `ControlledRevisionGatewayResult` validation.

The provider DTO contains only authorized editorial edits. Identity, structure,
ordering, protected state, lineage, fingerprints, assembled text, and
teleprompter text remain locally owned.

## Scenarios

- E2E-01 targets only an opening containing a synthetic Brașov library schedule
  and exact capacity facts.
- E2E-02 targets one story for a substantial rewrite while protecting a second
  story, opening, transition, closing, and CTA.
- E2E-03 targets one story, one transition, and the closing of a three-stage
  episode while preserving dates, times, IDs, order, and endpoints.
- E2E-04 targets one story containing an untrusted embedded instruction and
  verifies source-authority boundaries and exact factual preservation.

## Resumed Part 5 result — 27 July 2026

Preflight succeeded with OpenAI SDK 2.48.0, provider `openai`, configured model
`gpt-4.1-mini`, a resolved credential, a 30-second timeout, one maximum attempt,
SDK retries disabled, and four unique valid invocations. The dry run made zero
SDK requests. The focused suite passed 90 tests and the full suite passed 755
tests; Ruff, Black, compileall, and pip check also passed.

The live run stopped after E2E-01 as required. One semantic execution, projection,
credential resolution, SDK client construction, runtime attempt, SDK request,
provider DTO validation, reference authorization, reconstruction, normal
`EpisodeDraft` validation, and gateway-result construction completed. Provider
request ID, returned model ID, and usage metadata were available. Usage was 941
input tokens, 76 output tokens, and 1,017 total tokens. Duration was 3,278 ms.

E2E-01 failed the combined deterministic editorial-contract acceptance check
after the integration and reconstruction stages succeeded. The harness retained
no returned prose, so the failing editorial sub-assertion cannot be narrowed
without another paid run. No retry is authorized. E2E-02 through E2E-04 were not
run. This is classified as a blocker for Part 5 completion and requires a
targeted editorial-contract correction milestone; it does not invalidate the
provider DTO ownership or deterministic reconstruction layers.

No source draft, revised output, prompt, instruction, raw response, raw validation
value, raw exception, request identifier, or credential was emitted. The
deterministic unsupported-fact checks are intentionally bounded to scenario
allowlists and forbidden sets; they are not a general semantic hallucination
detector.

## Clean restart result — 28 July 2026

The clean restart used only `SCOUT_RUN_LIVE_OPENAI_PART5_RESTART=1`. Preflight
confirmed OpenAI SDK 2.48.0, provider `openai`, configured model
`gpt-4.1-mini`, credential availability, a 30-second timeout, one attempt per
scenario, SDK retries disabled, no fallback, four unique invocations, valid
scenario contracts, decomposed predicates, and corrected time normalization. The
dry run made zero requests. Focused suites and the full 807-test suite passed,
along with Ruff, Black, compileall, and pip check.

E2E-01 passed every applicable predicate. Its required interval matched once,
through an approved representation, and all workflow, gateway, editorial,
language, structure, domain, and privacy checks passed. It used one request and
one attempt, 941 input tokens, 75 output tokens, and 1,016 total tokens; duration
was 2,721 ms.

E2E-02 made one request and failed during provider DTO schema validation with the
safe classification `openai_provider_output_schema_invalid`. No provider metadata
or usage was available from the failed interpretation. Duration was 2,280 ms.
The harness stopped immediately. E2E-03 and E2E-04 were not run, and no retry or
fallback occurred.

Aggregate counts were two semantic executions, projections, credential
resolutions, SDK client constructions, runtime attempts, and SDK requests; and one
provider DTO validation, authorization, reconstruction, domain validation, and
gateway result. No production change was made. The evidence supports a targeted
provider-instruction correction investigation for E2E-02 rather than an
architecture change.
