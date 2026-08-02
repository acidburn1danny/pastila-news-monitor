# Module 2.9 Phase 7.5 Revision 2 — Opt-in OpenAI Smoke-Test Boundary

Status: Implemented — awaiting independent verification

## Purpose and dependency direction

Revision 2 defines the contract and authorization boundary for a future live OpenAI
smoke test. It is intentionally non-operational:

```text
provider_v2
    ↑
provider_execution_v2
    ↑
provider_execution_openai_v2
    ↑
provider_execution_openai_sdk_v2
    ↑
provider_runtime_openai_v2
    ↑
provider_runtime_openai_smoke_v2
    ↑
future CLI
```

No lower layer imports the smoke-test package. Revision 2 changes no provider,
execution adapter, SDK adapter, runtime composition, or existing CLI behavior.

## Configuration contract

`OpenAISmokeTestConfigurationV2` is immutable, extra-forbidding, and defensively
revalidated. It contains only:

- `confirm_live`: an exact boolean, defaulting to `False`;
- `model`: an exact nonblank, unpadded string;
- `timeout_seconds`: a positive exact integer or finite float.

It contains no credential, prompt, message, headers, retry policy, endpoint,
organization, project, transport, client, or response data. Configuration errors
are translated to the fixed public message `invalid OpenAI smoke-test
configuration`.

## Explicit confirmation

Future live execution requires an explicit `confirm_live=True` configuration. If
confirmation is absent, `OpenAISmokeTestRunnerV2.run()` raises
`OpenAISmokeTestConfirmationError` with the fixed message `explicit live OpenAI
smoke-test confirmation is required`.

Confirmation is necessary but is deliberately insufficient in Revision 2. After a
valid confirmed configuration, the runner immediately raises
`OpenAISmokeTestDependencyError` with `OpenAI live smoke test is not operational`.
It does not continue into any operational boundary.

## Non-operational runner

`OpenAISmokeTestRunnerV2` is immutable and stateless. `run(configuration)` performs
only defensive configuration reconstruction and confirmation validation. Revision 2
does not:

- retrieve `OPENAI_API_KEY` or any other credential;
- inspect or enumerate the environment;
- construct an OpenAI SDK client;
- compose `provider_runtime_openai_v2`;
- create a provider request;
- call the Responses API;
- perform authentication or networking;
- retry, stream, log, persist, trace, or emit telemetry.

All public failures are freshly created with fixed messages. Their context and cause
are cleared and suppression is enabled. Configuration evaluation is isolated from
public error dispatch: the evaluator returns only a private immutable outcome
category, and the dispatch frame retains no runner, configuration, configuration
field, hostile input, or derived secret-bearing value. The runner has a fixed
deterministic representation, copy and deep-copy preserve identity, serialization is
rejected for every pickle protocol, and repeated calls retain no state.

## Future CLI contract

The future command boundary is:

```text
pastila-scout openai smoke --confirm-live
```

Revision 2 does not register or wire this command. The existing CLI remains
unchanged. A future CLI must map `--confirm-live` to the exact confirmation field,
must reject its absence before credential or runtime access, and must preserve
stdout/stderr and exit-code conventions established by the application.

## Public API

The package exports only:

- `OpenAISmokeTestConfigurationError`;
- `OpenAISmokeTestConfigurationV2`;
- `OpenAISmokeTestConfirmationError`;
- `OpenAISmokeTestDependencyError`;
- `OpenAISmokeTestError`;
- `OpenAISmokeTestRunnerV2`.

The private structural runner protocol and implementation helpers are not exported.

## Planned revisions

Revision 3 may define an explicitly injected operational composition interface and
offline execution harness. It must preserve confirmation-first behavior and may not
silently acquire credentials or introduce a default live path.

Revision 4 may wire the documented CLI only after the operational layer has passed
independent verification. Any live validation must remain explicitly opted in,
bounded, separately invoked, and excluded from automated tests.

## Explicit exclusions

Revision 2 includes no live request, real credential access, environment-backed
source invocation, SDK construction, runtime composition, Responses operation,
networking, Ollama work, application retry, streaming, persistence, logging,
telemetry, or CLI registration. Automated tests use no real OpenAI credential and
perform no network operation.

## Test-selector accounting

The canonical historical selector remains:

```text
pytest -k "editorial_script_composer or provider_execution or provider_runtime_openai_v2"
```

By design, it excludes the focused smoke tests because the new package name is
`provider_runtime_openai_smoke_v2`. The explicit expanded selector is:

```text
pytest -k "editorial_script_composer or provider_execution or provider_runtime_openai_v2 or provider_runtime_openai_smoke_v2"
```

Both counts are reported separately during validation; the canonical selector is
not silently redefined.
