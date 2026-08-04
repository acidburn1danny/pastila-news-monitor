# Module 3.1 Phase B — Opt-in Producer migration

Status: **implemented — awaiting independent verification**

Phase B adds a separate, explicit application composition entry point:

```text
Producer compatibility request
    -> provider_compatibility_execution_v1
    -> injected ProviderExecutorV2
    -> validated ProviderExecutionResultV2
    -> injected Producer gateway projector
    -> frozen Phase A projection contracts
```

The existing OpenAI Producer API, imports, SDK client factory, cache, runtime,
exceptions, exports, and default route are unchanged. Importing the new package
does not activate it. Callers must explicitly compose it with the authoritative
request, executor, diagnostics authority, monotonic clock, cancellation token,
retry decider, sleeper, gateway projector, and optional observer.

Producer owns orchestration, retry policy, backoff ordering, diagnostics
aggregation, and lifecycle. The injected lower runtime owns provider clients,
timeout enforcement, transport reuse, and cleanup. The compatibility layer
does not close, compose, cache, inspect, or discover provider resources.

Rollback is removal of the opt-in call site. The legacy default requires no
change. This revision introduces no credentials, SDK imports, networking,
provider registration, CLI routing, or other consumer migration.

Revision 2 hardens three existing boundaries without changing this architecture:
successful outputs must reconcile exactly with authoritative request units and
ordering; configuration failures delete injected authorities before raising the
fixed public error; and lower cancellation preserves its validated outcome and
safe failure-code provenance in the top-level cancelled result.
