# Module 2.9 Phase 7.5 Revision 4 — Hardened Injected Offline Smoke Boundary

Status: Implemented — awaiting independent verification

## Purpose and dependency direction

Revision 4 defines an executable orchestration boundary for a future live OpenAI
smoke test. It is operational only through explicitly injected offline dependencies:

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

No lower layer imports the smoke-test package. Revision 4 changes no provider,
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

Confirmation authorizes one injected offline orchestration. It never selects a
concrete provider implementation or enables a live path.

## Injected operational runner

`OpenAISmokeTestRunnerV2` is an immutable authority holder with no mutable per-run
state or execution history. It accepts exactly a credential source and a runtime
composer. Constructor inputs are untrusted until their required methods pass static,
descriptor-safe validation. Validation reads class namespaces and cloned function
code without invoking properties, descriptors, lookup hooks, method bodies,
`__signature__`, or `__wrapped__`. Accepted authorities are ordinary, inherited, or
overridden instance methods and exact static/class methods with compatible
synchronous signatures. Dynamic, instance-injected, abstract, async, generator,
descriptor-backed, and incompatible authorities are rejected.

The validated raw function and exact receiver are pinned. Ordinary instance or
class method replacement after construction does not replace the pinned authority.
This is a same-process trusted-composition boundary, not protection against hostile
private-state or module mutation.

For a valid confirmed configuration the runner performs exactly:

```text
credential_source.get_api_key()
runtime_composer.compose(api_key, model, timeout)
composition.executor.execute()
composition.close()
```

Credential output is independently accepted only when it is an exact, nonempty,
nonblank, unpadded built-in string. The composer receives only the exact credential,
model, and timeout as keyword-only arguments.

Composer output is untrusted. The runner accepts ownership only after a plain
instance-held executor plus synchronous zero-argument `execute()` and `close()`
methods have all been statically validated and pinned. Before that ownership point,
cleanup is not guessed through malformed or descriptor-backed handoffs; the composer
retains responsibility. After ownership transfers, cleanup runs exactly once after
success, ordinary failure, malformed output, or BaseException. `execute()` receives
no arguments. It must return an exact, nonblank, unpadded built-in string.

The injected test harness uses a deterministic fake executor returning `SMOKE_OK`;
fakes exist only in tests. A cleanup failure takes lifecycle precedence over an
execution result or failure. There is no retry or fallback.

Revision 4 does not:

- retrieve `OPENAI_API_KEY` or any other credential;
- inspect or enumerate the environment;
- construct an OpenAI SDK client;
- compose `provider_runtime_openai_v2`;
- create a provider request;
- call the Responses API;
- perform authentication or networking;
- retry, stream, log, persist, trace, or emit telemetry.

`OpenAISmokeTestResultV2` is immutable, strict, instance-revalidating, and contains
only `success` and `response_text`; it carries no provider response or runtime
object. Pydantic's low-level `model_copy(update=...)` may construct an unchecked
internal copy, so every public boundary defensively reconstructs it before return.
All public
failures are freshly created with fixed messages. Their context and cause
are cleared and suppression is enabled. Configuration evaluation is isolated from
public error dispatch: the evaluator returns only a private immutable outcome
category, and the dispatch frame retains no runner, configuration, configuration
field, hostile input, or derived secret-bearing value. The runner has a fixed
deterministic representation, copy and deep-copy preserve identity, serialization is
rejected for every pickle protocol, and repeated calls retain no execution history.

Ordinary dependency exceptions become fixed public smoke errors with no raw
exception or runtime authority retained. `KeyboardInterrupt`, `SystemExit`, and
`GeneratorExit` preserve identity and propagate, but their prior tracebacks,
context, and cause are detached before runtime-bearing frames exit. Their own
payload remains unchanged. The public re-raise frames retain only the safe outcome
token and exception.

Reentrancy is supported: every invocation uses independent local state. Nested runs
must still satisfy configuration and confirmation rules, and each successfully
owned composition is closed exactly once.

## Future CLI contract

The future command boundary is:

```text
pastila-scout openai smoke --confirm-live
```

Revision 4 does not register or wire this command. The existing CLI remains
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
- `OpenAISmokeTestResultV2`;
- `OpenAISmokeTestRunnerV2`.

The private structural runner protocol and implementation helpers are not exported.

## Planned revisions

Revision 5 is reserved for the first explicitly authorized live request. It may be
implemented only after this injected offline boundary passes independent
verification. Any live validation must remain opted in, bounded, separately
invoked, and excluded from automated tests.

## Explicit exclusions

Revision 4 includes no live request, real credential access, environment-backed
source invocation, concrete production runtime composition, SDK construction,
Responses operation, networking, Ollama work, application retry, streaming,
persistence, logging, telemetry, or CLI registration. Automated tests use only
injected offline fakes and perform no network operation.

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
