# Module 2.9 — Phase 7.1 Revision 8 Freeze

**Status: FROZEN**

## Independent verification

Independent verification status:

```text
PHASE_7_1_REVISION_8_VERIFIED
```

Phase 7.1 Revision 8 may now be frozen.

## Architectural guarantees

### Provider-neutral architecture

The frozen dependency direction is:

```text
provider_v2
    ↑
provider_adapters_v2
    ↑
provider_composition_v2
```

The generic core does not import concrete adapters. Concrete adapters do not
import peers or the composition root. `provider_composition_v2` remains the sole
composition point.

### Registry authority

The frozen registry:

- composes providers deterministically;
- exposes an immutable, read-only provider mapping;
- remains provider-neutral;
- performs no provider execution;
- performs no networking;
- performs no persistence;
- performs no runtime discovery or automatic registration.

### Lifecycle authority

The frozen lifecycle contract guarantees:

- validation of actual wrapper code shape;
- static lifecycle-member and metadata inspection;
- deterministic rejection of invalid descriptors;
- deterministic rejection of abstract lifecycle implementations;
- deterministic, value-safe diagnostics;
- no lifecycle, descriptor, property, or abstract-body execution during
  composition.

### Annotation authority

The frozen annotation boundary guarantees:

- immutable registry-owned trusted symbol tables;
- no adapter-global annotation authority;
- no adapter-builtins annotation authority;
- no closure annotation authority;
- no `__wrapped__` annotation or shape authority;
- no `__signature__` annotation or shape authority;
- no annotation-expression evaluation;
- no annotation-bytecode execution;
- deterministic rejection when deferred annotations require `__annotate__`
  execution;
- static normalization only for explicitly materialized annotations.

### Result semantics

All Revision 3 request/result authority, reconstruction, contradiction,
deterministic-diagnostic, and artifact-immutability invariants remain frozen.

## Frozen V1 compatibility

- The frozen Script Composer remains unchanged.
- All eight delegated OpenAI V1 builder and validator callable identities remain
  preserved exactly.
- No V2 symbol shadows a frozen V1 public symbol.

## Public API baseline

- `pastila_scout.provider_v2`: exactly **42** public symbols.
- `pastila_scout.provider_adapters_v2.__all__`: `()`.
- `pastila_scout.provider_composition_v2.__all__`:
  `("build_provider_registry",)`.

## Default providers

The frozen default provider order is:

1. `claude`
2. `gemini`
3. `ollama`
4. `openai`

## Verification summary

| Gate | Frozen result |
|---|---|
| Focused Phase 7.1 | 116 passed |
| Complete Module 2.9 | 2,544 passed; 1,777 deselected |
| Complete repository | 4,321 passed |
| Ruff | Passed |
| Black check | Passed; 530 files unchanged |
| compileall | Passed |
| pip check | Passed; no broken requirements |

No failures, skips, xfails, warnings, or collection anomalies were reported.

## Frozen production files

The following 15 production files constitute the Phase 7.1 Revision 8 baseline:

- `src/pastila_scout/provider_v2/__init__.py`
- `src/pastila_scout/provider_v2/authority.py`
- `src/pastila_scout/provider_v2/canonical.py`
- `src/pastila_scout/provider_v2/errors.py`
- `src/pastila_scout/provider_v2/identity.py`
- `src/pastila_scout/provider_v2/interface.py`
- `src/pastila_scout/provider_v2/models.py`
- `src/pastila_scout/provider_v2/registry.py`
- `src/pastila_scout/provider_adapters_v2/__init__.py`
- `src/pastila_scout/provider_adapters_v2/base.py`
- `src/pastila_scout/provider_adapters_v2/claude.py`
- `src/pastila_scout/provider_adapters_v2/gemini.py`
- `src/pastila_scout/provider_adapters_v2/ollama.py`
- `src/pastila_scout/provider_adapters_v2/openai.py`
- `src/pastila_scout/provider_composition_v2.py`

Their authoritative hashes are recorded in
`Phase7_1_Revision8_Integrity.md`.

## Freeze policy

Phase 7.1 Revision 8 is frozen. Future work must not modify the frozen production
files in place. Any behavioral change requires either a new phase or a new
architectural revision outside this baseline. A bug fix affecting a frozen
guarantee begins a new explicitly reviewed revision; it is not applied silently to
this baseline.

## Excluded from this freeze

This freeze does not implement or approve future execution-layer behavior,
including:

- provider execution;
- provider SDK integrations;
- networking;
- retries or fallback policies;
- streaming;
- telemetry;
- persistence or caching;
- runtime provider implementations or discovery.

Those capabilities belong to Phase 7.2 or later.
