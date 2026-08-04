# Phase 4.2 — Editor Operational Specification V1

Status: **normative specification — ready for independent review**

Baseline: `module-4.1-rank-events-r1-verified` / `4b4ffd927a76f9e1cbfa2201546b106642db2628`

This document specifies the missing application boundary between the frozen
Scout-to-Editor contract and the existing Editor domain. It does not authorize
runtime, CLI, persistence, provider, Producer, or schema changes.

## 1. Normative language and scope

The words **MUST**, **MUST NOT**, **SHALL**, **SHALL NOT**, and **MAY** are
normative. The operational workflow specified here is additive. Existing Scout,
Editor, Producer, provider, and public-contract behavior remains frozen.

Exactly one future application-owned coordinator is specified:
`EditorOperationalCoordinatorV1`. In Revision 2 it receives validated
deterministic inputs, invokes `SelectionEngine` exactly once, constructs one
immutable generation plan, and returns one preparation result. Revision 2 does
not invoke `ControlledGenerator` or any provider. The coordinator owns no
provider, retry loop, persistence, CLI, Producer handoff, or GUI behavior.

## 2. Repository inspection and current architecture

### 2.1 Existing Scout export path

```text
EventRankingReport
  -> export-editor-input CLI command
  -> export_editor_input(report, EditorInputExportContext)
  -> assign_scout_input_identity
  -> ScoutEditorInputV1
  -> write_contract (atomic canonical UTF-8 JSON)
```

`pastila_scout.exporters.editor_input.export_editor_input` is the sole discovered
production conversion from the private ranking report to the public Editor
input. It preserves ranked-event order while assigning public ranks and builds
the frozen contract fields. `pastila_scout.contracts.identity` assigns and
verifies content-derived report identity. `pastila_scout.contracts.io` performs
strict bounded local-file loading and atomic canonical writing.

The CLI can export, import, validate, and re-export contracts. It does not run
an Editor workflow.

### 2.2 Existing public contracts

The public Scout-to-Editor input is `ScoutEditorInputV1`. It contains the frozen
contract version, report identity and fingerprint, creation and source-run
metadata, Scout and ranking schema versions, selection parameters, AI mode,
event counts, and ordered `RankedEditorialEvent` values. Its model validators
enforce ranking, count, and identity invariants.

The existing public Editor decision contract is `EditorAgentOutputV1`. It binds
to the source Scout contract, selection profile, and episode context and carries
status, proposal or failure details. `validate_editor_output_against_input`
performs cross-contract validation. This is a deterministic selection contract;
it is not a generated episode draft and MUST NOT be repurposed as one.

`SelectionProfileV1` and `EpisodeContextV1` are existing explicit deterministic
inputs. No repository boundary currently selects or persists their values for
an operational Editor invocation.

### 2.3 Existing deterministic Editor preparation

The intended sequence is evidenced by the exported Editor APIs and their
integration tests:

1. `SelectionEngine.select` validates the public input/profile/context and
   deterministically produces `EditorialSelectionResult` containing
   `EditorAgentOutputV1` and a private `DecisionTrace`.
2. `EpisodeFlowOptimizer` deterministically resolves the episode order.
3. `EditorialBlueprintBuilder` derives the editorial blueprint.
4. `CommentaryBlueprintBuilder` derives commentary constraints and intentions.
5. `VoiceModelBuilder` derives the voice plan.
6. Those prepared artifacts are inputs to `ControlledGenerator.generate`.

Selection, ordering, blueprints, metadata, identity, factual constraints,
budgets, and contract validation are deterministic authorities. AI MUST NOT
replace, reorder, reinterpret, or repair them.

### 2.4 Existing generation boundary

`ControlledGenerator` is a library service; no production application composes
or invokes it. It:

- checks agreement between deterministic flow orders;
- constructs component contexts and a `GenerationManifest`;
- uses `PromptBuilder` for stories, transitions, opening, closing, and optional
  call-to-action bridge generation;
- requires structured Pydantic results for each component;
- runs the existing component validators after generation;
- updates immutable `EpisodeGenerationState` only after acceptance;
- assembles `EpisodeDraft` deterministically; and
- returns `ControlledGenerationResult` with draft, trace, manifest, and final
  state.

`DraftAssembler` and `TeleprompterFormatter` are deterministic. The assembled
text is derived from accepted components and is validated by `EpisodeDraft`.

### 2.5 Existing prompt and output authority

`PromptBuilder` is the existing prompt authority. It emits an ordered
`GenerationPrompt` with these layers:

1. immutable rules;
2. episode context;
3. local component context;
4. approved facts;
5. forbidden claims;
6. editorial intentions;
7. conversation intentions;
8. voice intentions;
9. accepted episode state;
10. the component's Pydantic output schema;
11. the local generation task; and
12. only on an existing corrective attempt, validation failures and corrective
    constraints.

The rendered prompt fingerprint is SHA-256 over deterministic canonical JSON.
The operational workflow MUST reuse this builder, layer order, text rendering,
fingerprint, component schemas, Romanian language setting, and validation. It
MUST NOT introduce a system prompt, provider-specific instruction, prompt
rewrite, output repair, normalization, Markdown processing, or schema coercion.

### 2.6 Existing provider abstractions and adapters

`LanguageModelProvider.generate_structured` is the protocol currently consumed
by `ControlledGenerator`. It accepts an exact `GenerationPrompt`, exact output
schema type, and `LanguageGenerationConfig`, and returns an instance of that
schema. `ScriptedLanguageModelProvider` is an offline test implementation.

The repository also contains legacy Editor AI-provider adapter and OpenAI
composition infrastructure, plus the frozen Producer compatibility packages.
None is composed by a production Editor caller. The new operational path MUST
not call or extend a concrete OpenAI/Ollama adapter. A future narrow adapter MAY
implement `LanguageModelProvider`, but its only execution authority is section
5.

### 2.7 Existing persistence, Producer, and CLI boundaries

No operational episode-draft persistence or export contract was discovered.
The editorial-memory store is a separate, narrowly scoped memory snapshot store
and MUST NOT be reused for drafts. Generic `write_contract` accepts only the
existing public contract union and therefore is not a draft persistence API.

Producer compatibility contracts describe controlled-revision provider
execution. They do not define a handoff from `EpisodeDraft` or an operational
Editor result. No production Producer caller consumes an Editor draft.

The sole console entry point is `pastila-scout`. It has Scout commands,
contract commands, `export-editor-input`, and the verified explicit provider
command. It has no Editor execution command.

### 2.8 Existing, missing, and proposed boundaries

| Classification | Boundary |
|---|---|
| Existing | ranking report -> `export_editor_input` -> `ScoutEditorInputV1` |
| Existing | strict public-contract load, identity verification, and validation |
| Existing | deterministic selection, flow, editorial, commentary, and voice preparation |
| Existing | `PromptBuilder`, component schemas and validators |
| Existing | `ControlledGenerator` -> `ControlledGenerationResult` / `EpisodeDraft` |
| Existing | verified application request authority, workflow bridge, selector, OpenAI and Ollama executors |
| Missing | application composition of the full Editor preparation/generation sequence |
| Missing | adapter from `LanguageModelProvider` to the verified application execution chain |
| Missing | one operational result and failure boundary |
| Missing | durable draft export/persistence contract |
| Missing | Producer-facing draft handoff contract |
| Missing | explicit Editor CLI rollout |
| Proposed | the coordinator and result in sections 3 and 4 |
| Proposed | phased boundaries in section 13; none is implemented by this specification |

The current end-to-end architecture is therefore:

```text
Scout ranking
  -> export-editor-input
  -> ScoutEditorInputV1
  -> [missing operational coordinator/composition]
  -> existing deterministic Editor preparation
  -> existing ControlledGenerator
  -> EpisodeDraft
  -> [missing caller-owned persistence/export]
  -> [missing Producer handoff]
```

## 3. `EditorOperationalCoordinatorV1`

The future coordinator SHALL be the sole application coordinator for one
Editor preparation. In Revision 2 it MUST be explicitly constructed from only
one injected `EditorSelectionEngineV1`. No generation boundary is injected.
It MUST have no global registry, singleton, environment lookup, provider
discovery, service locator, or import-time work.

Its operation SHALL accept exactly the already validated operational inputs:

- `ScoutEditorInputV1`;
- `SelectionProfileV1`;
- `EpisodeContextV1`; and
- no generation configuration in Revision 2.

Its Revision 2 responsibilities are exactly those in section 15.9:

1. strictly reconstruct and validate inputs and source identity;
2. invoke `SelectionEngine.select` exactly once after valid input;
3. validate the exact `EditorialSelectionResult`;
4. construct one immutable `EditorGenerationPlanV1`; and
5. return one `EditorOperationalPreparationResultV1`.

The remaining deterministic preparation sequence and `ControlledGenerator`
belong to later revisions. Revision 2 performs no generation.

It MUST NOT persist, write, print, retry, sleep, select a provider, read a
credential, construct a provider client, poll cancellation, enforce a second
timeout, clean up provider resources, invoke Producer, or emit GUI behavior.

## 4. Future `EditorOperationalResultV1`

This generated-result boundary is deferred to Revision 3 and is not a Revision
2 symbol. Section 18 defines its minimum semantic content and makes Revision 3
entry conditional on a separate exact contract specification. The following
table is informative only:

| Field | Existing source | Meaning |
|---|---|---|
| `source_report_id` | `ScoutEditorInputV1.report_id` | Exact source identity |
| `source_report_fingerprint` | `ScoutEditorInputV1.report_fingerprint` | Exact source fingerprint |
| `selection_output` | `EditorialSelectionResult.output` | Existing validated `EditorAgentOutputV1` metadata/selection result |
| `draft` | `ControlledGenerationResult.draft`, or absent | Existing `EpisodeDraft`; present only for completed generation |
| `generation_status` | closed application status | Exactly `completed`, `failed`, or `cancelled` |
| `diagnostics` | existing selection trace plus controlled generation trace/manifest, safely projected | Deterministic and generation diagnostics without raw provider objects |

No persisted path, filename, provider credential, provider client, raw SDK
object, raw exception, selector, executor, request body, or Producer object may
be retained. A completed result MUST contain a fully validated draft. A failed
or cancelled result MUST contain no draft. The status MUST NOT be inferred from
provider text; it is projected from validated execution/generation state.

This result is application-owned and distinct from both the public
`EditorAgentOutputV1` selection contract and Producer execution contracts.

## 5. Provider-neutral generation execution

Every AI component call on the future neutral path MUST use only:

```text
ApplicationProviderRequestV1
  -> ApplicationRequestAuthorityV1
  -> ProviderExecutionRequestV2
  -> ScoutRuntimeRequestV1
  -> ScoutWorkflowExecutionV1.execute_provider_neutral()
  -> ScoutRuntimeExecutionBridgeV1
  -> ProviderSelectorV1
  -> exactly one selected verified provider
```

The `LanguageModelProvider` adapter SHALL serialize the exact existing
`GenerationPrompt` semantics and request the exact existing Pydantic output
schema. Application authority construction occurs exactly once for each
component provider execution. The adapter SHALL return generated content to the
existing schema validator unchanged and SHALL perform no selection, retry,
fallback, JSON repair, editorial transformation, or provider-specific behavior.

OpenAI composition and credential access MUST occur only after explicit OpenAI
selection. Ollama composition MUST not access OpenAI credentials. Both paths
MUST reuse Module 3.6 command-time composition ownership and remain offline in
normal tests.

## 6. Deterministic and AI authority separation

| Responsibility | Sole authority |
|---|---|
| Public input identity and schema validation | Existing contract/identity validators |
| Selection and selected-event ordering | `SelectionEngine` |
| Flow optimization | `EpisodeFlowOptimizer` |
| Editorial blueprint | `EditorialBlueprintBuilder` |
| Commentary blueprint | `CommentaryBlueprintBuilder` |
| Voice plan | `VoiceModelBuilder` |
| Prompt construction and fingerprint | `PromptBuilder` |
| Component output schema | Existing component Pydantic model |
| Component semantic validation | Existing generation validators |
| State acceptance | `EpisodeGenerationState` |
| Draft assembly and teleprompter formatting | Existing deterministic assemblers |
| Editorial prose generation | Selected provider through the verified chain |

AI output is candidate structured content only. It cannot change source facts,
event selection/order, metadata, budgets, schema, validation rules, manifest,
lineage, or persistence policy.

## 7. Ownership matrix

| Concern | Sole owner | Rule |
|---|---|---|
| Revision 2 operational preparation | `EditorOperationalCoordinatorV1` | One validation, selection, and plan-construction operation |
| Existing editorial corrective attempts | `ControlledGenerator` | Preserve current bounded component-attempt policy; coordinator adds none |
| Lower provider retry | None | Verified runtime is called once per component attempt; no fallback/retry there |
| Timeout | Verified provider execution chain | Application authority carries the single timeout intent and the selected verified runtime enforces it; coordinator/adapter MUST NOT duplicate it |
| Cancellation | Existing Scout runtime cancellation dependency | Coordinator/adapter MUST NOT poll or snapshot independently |
| Provider/client cleanup | Verified Module 3.6 provider composition owner | Exactly once; coordinator MUST NOT guess ownership |
| Generation diagnostics | Existing `GenerationTrace` and manifest | Coordinator only validates/projects them |
| External observation | Operational caller | Coordinator has no observer side effects |
| Draft persistence/export | Operational caller | Persist only a completed, validated result |
| Producer invocation | Future Producer-handoff caller | Coordinator MUST NOT invoke Producer |
| CLI parsing/rendering | Future CLI command boundary | Coordinator MUST not print or parse arguments |

The existing `ControlledGenerator` timeout retry is part of its frozen legacy
behavior. Provider-neutral integration MUST not create a second transport retry.
Before Revision 3 is implemented, an independent review MUST determine whether
that legacy retry can be used unchanged with the one-call neutral adapter. If it
would cause duplicate neutral execution after a lower timeout, Revision 3 is
blocked until retry authority is reconciled without changing a frozen module.

## 8. Persistence and atomicity

Persistence belongs only to the operational caller, not the coordinator or
Producer. This follows the discovered architecture: no draft store exists, the
coordinator is a computation boundary, and Producer has no Editor-draft input
contract.

The future caller SHALL persist only after receiving a completed, fully
validated `EditorOperationalResultV1`. It MUST use a separately specified
atomic export contract. Failure, cancellation, malformed generation, or
validation failure MUST produce no partial draft. This specification does not
choose a directory, database, filename, encoding envelope, overwrite policy, or
transaction implementation because the repository defines none.

## 9. Future Producer handoff

The future handoff SHALL be a contract boundary from one completed
`EditorOperationalResultV1` to a Producer-owned input. It MUST carry only:

- exact source report identity/fingerprint;
- the validated `EditorAgentOutputV1` selection metadata required downstream;
- the exact validated `EpisodeDraft`; and
- explicit lineage needed to bind the draft to its source operation.

It MUST NOT carry provider choice, credential, executor, selector, raw provider
result, prompt, retry policy, persistence path, or CLI state. No existing
Producer contract accepts these values, so the exact Producer input contract
must be specified and independently reviewed in Revision 5 before any handoff
implementation.

## 10. Future CLI boundary

An `editor-run` command is justified because the repository already uses the
single `pastila-scout` CLI as the explicit application boundary for local
contract workflows and provider opt-in. It SHALL not be implemented before the
inert coordinator and provider-neutral execution are verified.

Its future surface is limited to:

```text
pastila-scout editor-run --provider {openai,ollama} --input INPUT --output OUTPUT
```

Provider, input, and output MUST be explicit. Accepted provider values are
exactly lowercase `openai` and `ollama`; there is no default, alias, trimming,
case folding, discovery, `auto`, or fallback. `--input` loads one existing
public `ScoutEditorInputV1`. `--output` is owned by the caller under the future
atomic export contract. Help and imports MUST remain passive.

Selection profile, episode context, and generation configuration still require
an explicit application configuration authority. Their CLI representation is
not defined by the repository and MUST be specified before Revision 4; hidden
defaults or environment discovery are forbidden.

## 11. Failure model

The future operational result/failure boundary SHALL distinguish these safe
categories without retaining raw exceptions or content:

| Failure | Owner/classification | Required behavior |
|---|---|---|
| Provider failure/unavailable | Verified execution projection | Failed result; no retry/fallback/persistence |
| Timeout | Verified timeout authority | Failed result; no duplicate enforcement or fallback |
| Cancellation | Scout runtime cancellation authority | Cancelled result; no persistence |
| Malformed lower result/invalid lineage | Verified bridge/authority validation | Failed result before Editor schema parsing |
| Malformed generated output/schema failure | Existing output schema and component validator | Existing controlled-generation outcome; no repair |
| Deterministic input/preparation validation | Existing deterministic validator | No provider call and no draft |
| Result/draft validation | Coordinator | Failed result and no persistence |
| Persistence failure | Operational caller | Valid in-memory result remains; no partial destination; coordinator is unaffected |
| Cleanup failure | Verified cleanup owner | Safe failure projection; coordinator does not close again |

Public messages MUST be fixed application-owned text. Error graphs and
tracebacks exposed outside the boundary MUST retain no credential, client,
executor, selector, workflow, bridge, request, public Editor input, prompt,
generated output, raw exception, or persistence handle.

## 12. Required verification properties

Each implementation revision MUST test passive imports, strict immutable
composition, copied-invalid reconstruction, safe address-free representation,
explicit copy/deepcopy policy, explicit pickle rejection, deterministic
equality, exact call cardinality, traceback hygiene, and frozen-module
integrity. Normal tests require no credential, network, Ollama service, local
model, or localhost listener.

Differential tests MUST prove that identical deterministic inputs and generated
component outputs yield identical selection, preparation artifacts, component
validation, draft, manifest, diagnostics, and failure behavior regardless of
legacy or neutral execution. Provider choice MUST never enter prompt semantics
or public Editor contracts.

## 13. Implementation roadmap

### Revision 2 — Contracts and deterministic preparation coordinator

- Add the exact section 15 contracts, protocol, and immutable injected
  coordinator composition.
- Reconstruct inputs, invoke `SelectionEngine` exactly once, and construct the
  deterministic `EditorGenerationPlanV1` only.
- Perform no controlled generation, provider composition, networking,
  persistence, CLI registration, observer work, or Producer handoff.
- Verify exact deterministic artifacts, cardinality, passive imports, object
  safety, and frozen integrity.

### Revision 3 — Provider-neutral generation

- Add one narrow `LanguageModelProvider` adapter to the verified application
  request/workflow/runtime/selector chain.
- Preserve exact `GenerationPrompt`, schema, output, validation, and lineage.
- Resolve the section 7 timeout-retry compatibility gate before execution.
- Verify OpenAI/Ollama with offline fakes, exact one selected execution per
  authorized component attempt, zero unselected execution, no lower retry or
  fallback, and exact cleanup ownership.

### Revision 4 — Explicit CLI rollout and caller-owned export

- Add only `editor-run` to the existing CLI after specifying explicit profile,
  context, generation configuration, and atomic result export contracts.
- Require exact provider, input, and output arguments.
- Preserve every existing CLI command and passive help behavior.
- Keep persistence entirely in the command/caller after a completed result.

### Revision 5 — Producer handoff

- First specify and independently verify the missing Producer-facing input
  contract.
- Add an explicit caller-owned handoff from a completed operational result.
- Do not add provider behavior, persistence ownership, retry, routing, or
  fallback to the coordinator or Producer boundary.

Each revision requires its own implementation prompt, independent verification,
freeze, and baseline. This document itself implements none of them.

## 14. Non-goals

This specification does not authorize production code, tests, runtime wiring,
new packages, public-schema changes, persistence design, model discovery,
provider defaults, direct OpenAI/Ollama use, fallback, automatic routing,
additional retry loops, prompt changes, output repair, ranking, polling, queue,
GUI, reporting, or Producer execution.

## 15. Normative implementation contract

Sections 15–22 close the implementation-readiness findings and are controlling
where an earlier roadmap statement is less specific. They do not authorize an
implementation under this documentation revision.

### 15.1 Exact Revision 2 package

Revision 2 SHALL add exactly this production package:

```text
src/pastila_scout/editor_operational_v1/
    __init__.py
    coordinator.py
    errors.py
    models.py
    protocols.py
```

It SHALL add exactly one focused test file:

```text
tests/test_editor_operational_v1.py
```

No existing production file or test may change. `__init__.py` SHALL import and
expose exactly this ordered tuple:

```python
__all__ = (
    "EditorGenerationPlanV1",
    "EditorOperationalConfigurationError",
    "EditorOperationalCoordinatorV1",
    "EditorOperationalFailureCodeV1",
    "EditorOperationalFailureV1",
    "EditorOperationalLifecycleStateV1",
    "EditorOperationalPreparationResultV1",
    "EditorSelectionEngineV1",
)
```

No other public symbol is authorized. `models.py` owns the five value contracts,
`protocols.py` owns `EditorSelectionEngineV1`, `coordinator.py` owns
`EditorOperationalCoordinatorV1`, and `errors.py` owns the configuration error.
Imports SHALL depend only on existing public contract and Editor types. Frozen
packages MUST NOT import this package.

### 15.2 Common object rules

Every non-enum Revision 2 value contract and the coordinator SHALL use
`@dataclass(frozen=True, slots=True, init=False, repr=False)`. Enums SHALL derive
from `StrEnum`. Constructors SHALL accept only exact declared types; primitive
subclasses and coercion are forbidden. Existing Pydantic inputs SHALL be
reconstructed using `model_dump(mode="python", warnings=False)` followed by the
exact model's `model_validate(..., strict=True)`. Existing dataclass inputs SHALL
be reconstructed by their declared fields. Nested reconstruction failure SHALL
be translated to the fixed application failure assigned below.

Each value contract SHALL retain a private SHA-256 seal over its canonical
semantic representation. Reconstruction SHALL read declared fields without
dynamic lookup, construct a fresh instance through its public constructor, and
compare the retained seal. Missing fields, extra retained state, type changes,
or seal mismatch SHALL be rejected. The seal is private and is not serialized,
printed, compared as a semantic field, or exported.

Canonical representation is UTF-8 JSON with `ensure_ascii=False`,
`sort_keys=True`, separators `(",", ":")`, `allow_nan=False`, enum values as
strings, tuples as arrays, and nested existing models represented by strict
Python-mode dumps. No timestamp, UUID, PID, path, memory address, environment
value, or unordered iteration may enter it. Ordered tuples preserve order.

Value-contract equality SHALL compare exact types and declared semantic fields
only. `copy.copy` and `copy.deepcopy` SHALL return a freshly reconstructed equal
value. Pickle SHALL be rejected by `__reduce_ex__` with a fixed `TypeError`
message `<ClassName> does not support pickle`. Repr SHALL be a fixed,
address-free summary containing lifecycle/status and counts only; it SHALL
redact Scout input, selection output, traces, failures beyond their safe code,
and dependencies.

The coordinator SHALL validate retained state before every public operation.
Its equality SHALL use exact type and selection-engine identity without calling
dependency hooks. Copy and deepcopy SHALL construct a new coordinator retaining
the same injected engine identity. Pickle SHALL be rejected with
`EditorOperationalCoordinatorV1 does not support pickle`. Its repr SHALL be
exactly
`EditorOperationalCoordinatorV1(selection_engine=<injected EditorSelectionEngineV1>)`.

All public errors SHALL be raised `from None`, set
`__suppress_context__ = True`, and retain no input, engine, result, trace, or raw
exception in exception attributes or package-owned traceback locals.

### 15.3 Exact lifecycle and failure enums

`EditorOperationalLifecycleStateV1` SHALL contain, in this order, exactly:

```python
ACCEPTED = "accepted"
VALIDATED = "validated"
SELECTED = "selected"
PLANNED = "planned"
FAILED = "failed"
```

The only valid lifecycle tuples are:

- success: `(ACCEPTED, VALIDATED, SELECTED, PLANNED)`;
- invalid input: `(ACCEPTED, FAILED)`;
- selection exception: `(ACCEPTED, VALIDATED, FAILED)`; and
- invalid selection result or internal plan construction failure:
  `(ACCEPTED, VALIDATED, SELECTED, FAILED)`.

`EditorOperationalFailureCodeV1` SHALL contain, in this order, exactly:

```python
INVALID_INPUT = "editor_operational_invalid_input"
SELECTION_FAILED = "editor_operational_selection_failed"
INVALID_SELECTION_RESULT = "editor_operational_invalid_selection_result"
PLAN_CONSTRUCTION_FAILED = "editor_operational_plan_construction_failed"
```

No provider, timeout, cancellation, observer, persistence, cleanup, or retry
code is permitted in Revision 2.

### 15.4 `EditorOperationalFailureV1`

Exact fields, in order:

```python
code: EditorOperationalFailureCodeV1
safe_message: str
retryable: bool = False
```

`retryable` MUST be exact `False`. The code/message table is closed:

| Code | Exact message |
|---|---|
| `INVALID_INPUT` | `Editor operational input is invalid.` |
| `SELECTION_FAILED` | `Editor deterministic selection failed.` |
| `INVALID_SELECTION_RESULT` | `Editor deterministic selection returned an invalid result.` |
| `PLAN_CONSTRUCTION_FAILED` | `Editor generation plan construction failed.` |

No cause, details, raw exception, input content, trace, provider data, or partial
output is retained.

### 15.5 `EditorGenerationPlanV1`

Exact fields, in order:

```python
source_input: ScoutEditorInputV1
selection_profile: SelectionProfileV1
episode_context: EpisodeContextV1
selection_output: EditorAgentOutputV1
selection_trace: DecisionTrace
source_report_id: str
source_report_fingerprint: str
selected_event_ids: tuple[int, ...]
backup_event_ids: tuple[int, ...]
rejected_event_ids: tuple[int, ...]
```

All fields are required and have no defaults. `source_report_id` and
`source_report_fingerprint` MUST equal the reconstructed source input.
`selection_output` MUST pass `validate_editor_output_against_input` with the
reconstructed source/profile/context. The three ID tuples MUST exactly equal
the corresponding tuples in `selection_trace`, preserve their order, contain
exact positive built-in integers, contain no duplicates within or across
selected/backup tuples, and reference events in `source_input`. Rejected IDs
MUST equal the trace exactly and MUST reference source events. No generation
prompt, draft, provider value, timeout, cancellation, observer, or persistence
state is present.

`selection_output.status` MUST be exact `ContractStatus.SUCCESS` and its
`episode_proposal` MUST be present. Every other valid selection status is a
deterministic non-generation outcome and maps to
`PLAN_CONSTRUCTION_FAILED`; no plan is returned and no later stage runs.

This is a deterministic preparation plan, not a provider request. Later
deterministic flow, blueprint, commentary, and voice preparation consumes it;
Revision 2 does not perform those later stages.

### 15.6 `EditorOperationalPreparationResultV1`

Exact fields, in order:

```python
source_report_id: str
source_report_fingerprint: str
lifecycle: tuple[EditorOperationalLifecycleStateV1, ...]
plan: EditorGenerationPlanV1 | None
failure: EditorOperationalFailureV1 | None
```

All fields are required and have no defaults. The source identity fields MUST
equal the accepted reconstructed source input even on a post-validation
failure. For `INVALID_INPUT`, where no trusted source identity exists, both
fields MUST be the exact empty string; empty identity is forbidden otherwise.

For the success lifecycle, `plan` is required, `failure` is absent, and source
identity MUST equal the plan. For every failed lifecycle, `plan` is absent and
`failure` is required with the code matching the lifecycle cause. Partial plans
are forbidden. A Revision 2 result contains no draft, generated component,
provider result, diagnostics object, observer event, persistence handle, or
cleanup state.

### 15.7 `EditorSelectionEngineV1`

This runtime-checkable shape is a structural injection protocol and has exactly
one method:

```python
def select(
    self,
    scout_input: ScoutEditorInputV1,
    profile: SelectionProfileV1,
    context: EpisodeContextV1,
) -> EditorialSelectionResult: ...
```

Coordinator construction SHALL validate the descriptor statically with
`inspect.getattr_static(type(value), "select")`, `inspect.signature` with
`follow_wrapped=False`, and resolved exact annotations. The descriptor MUST be
an ordinary instance function with exact parameter names, order, kinds,
defaults, and annotations shown above. Properties, cached properties,
staticmethods, classmethods, partials, wrapped functions, forged
`__signature__`, dynamic attributes, callable instances, and subclasses that do
not independently satisfy the exact descriptor check are rejected. Validation
MUST NOT invoke `select`, attribute hooks, equality, repr, copy, or other
dependency behavior.

### 15.8 `EditorOperationalConfigurationError`

This SHALL be the only raised application-owned configuration exception in
Revision 2. It subclasses `Exception` and its only permitted message is:

```text
Editor operational configuration is invalid.
```

It has no extra fields. It is used for invalid coordinator construction or
copied-invalid coordinator state. Operational input and selection failures are
returned as `EditorOperationalPreparationResultV1`, not raised.

### 15.9 `EditorOperationalCoordinatorV1`

Exact public signatures:

```python
def __init__(self, selection_engine: EditorSelectionEngineV1) -> None: ...

def prepare(
    self,
    scout_input: ScoutEditorInputV1,
    selection_profile: SelectionProfileV1,
    episode_context: EpisodeContextV1,
) -> EditorOperationalPreparationResultV1: ...
```

The only field is the injected `selection_engine`. The exact call order is:

1. append `ACCEPTED` locally;
2. strictly reconstruct `scout_input`, `selection_profile`, and
   `episode_context`, and verify Scout input identity;
3. on failure, return `INVALID_INPUT` with `(ACCEPTED, FAILED)` and no call;
4. append `VALIDATED`;
5. call `selection_engine.select(reconstructed_input,
   reconstructed_profile, reconstructed_context)` exactly once;
6. on exception, discard it and return `SELECTION_FAILED` with no plan;
7. append `SELECTED`;
8. require exact type `EditorialSelectionResult`, strictly reconstruct its
   `EditorAgentOutputV1` and `DecisionTrace`, and cross-validate output against
   input/profile/context;
9. on invalidity, return `INVALID_SELECTION_RESULT` with no plan;
10. construct and reconstruct `EditorGenerationPlanV1`;
11. on failure, return `PLAN_CONSTRUCTION_FAILED` with no plan;
12. append `PLANNED` and return the success result.

`SelectionEngine` therefore constructs `EditorAgentOutputV1` inside
`EditorialSelectionResult`. The coordinator neither duplicates nor modifies
selection. It calls no flow optimizer, blueprint builder, `PromptBuilder`,
`ControlledGenerator`, provider, workflow bridge, selector, persistence,
observer, cleanup, clock, timer, thread, process, filesystem, database,
credential, environment, network, logging, or warning boundary. Construction is
inert. Imports are passive. Revision 2 performs deterministic preparation only.

## 16. Exact Revision 3 structured-generation mapping

Revision 3 MAY begin only after Revision 2 is independently verified and the
configuration-preservation gate below is satisfied. It adds one application
adapter implementing the existing `LanguageModelProvider` protocol. The
coordinator never imports a provider implementation.

For each `generate_structured` call, the mapping is exactly:

1. validate exact `GenerationPrompt`, exact `output_schema` subclass of the
   existing frozen generation model family, and exact
   `LanguageGenerationConfig`;
2. use `prompt.text` unchanged as the single application prompt; there is no
   additional system message, user message, wrapper, prefix, suffix, schema,
   role, or provider-specific branch—the existing `OUTPUT_SCHEMA` prompt layer
   already contains `output_schema.model_json_schema()`;
3. construct one `ApplicationProviderRequestV1`; the verified authority owns
   its one `generation` role message and its single NFC canonicalization;
4. execute exactly one `ScoutWorkflowExecutionV1.execute_provider_neutral`
   operation through the verified runtime bridge and selected executor;
5. require a completed/success result with exactly one generated output at
   ordinal zero and exact matching source lineage;
6. copy that output text without trimming or normalization;
7. reject if it is empty, differs from `text.strip()`, contains leading/trailing
   whitespace, or is not one JSON document;
8. parse once using `json.loads`; require an exact built-in `dict` at the top
   level; duplicate JSON object keys MUST be rejected with an `object_pairs_hook`;
9. call `output_schema.model_validate(parsed, strict=True)` exactly once; and
10. return that validated Pydantic instance to `ControlledGenerator`.

There is no Markdown-fence stripping, repair, second parse, field insertion,
coercion, model-specific transformation, or retention of raw text. JSON parse
or schema failure raises `ProviderStructuredOutputError` with the fixed message
`Provider returned invalid structured output.` from no cause. Lower failure
maps to the existing safe `ProviderError` subtype without raw messages. Thus
generated text is preserved up to exact parsing; `LanguageModelProvider`
correctly returns the validated model, not raw text.

`ApplicationProviderRequestV1` currently carries prompt, timeout, cancellation,
provider choice, reference, and time but not temperature, top-p, maximum output
tokens, seed, or structured-output mode. Revision 3 is HARD BLOCKED until an
independently verified public application authority can preserve every
supported `LanguageGenerationConfig` value or an independently reviewed policy
defines exact rejected configurations. Revision 3 MUST NOT silently drop,
default, infer, or provider-configure those fields and MUST NOT modify a frozen
authority within Phase 4.2.

## 17. Exact Revision 3 retry, timeout, cancellation, cleanup, and observer

`ControlledGenerator` is the sole retry owner. Its existing behavior is
normative: each component has at most `GenerationPolicy.max_attempts_per_component`
editorial/schema attempts; additionally, `_provider_call` may call the adapter
exactly twice only when the first adapter call raises `ProviderTimeoutError`.
The adapter and lower runtime never retry. There is no backoff because the
existing generator defines none.

Timeout is per adapter/lower attempt and comes from the exact generation
configuration through the application authority. There is no total-operation
timer. Each adapter call creates a fresh application request, fresh
`ProviderExecutionRequestV2`, fresh request reference, and fresh cancellation
snapshot. The same composed selector/executor may be reused for all calls in
one `ControlledGenerator.generate` operation.

Cancellation is checked by the existing runtime before each dispatch. Before a
timeout retry, the adapter MUST obtain a fresh cancellation snapshot; requested
cancellation prevents the second dispatch and maps to cancellation, not
timeout. Cancellation is never retryable and takes precedence over retry.

The lower composition owner closes exactly once after the entire generator
operation, on success or failure. Neither coordinator, generator adapter, nor
observer closes or traverses dependencies. No cleanup occurs between adapter
calls when the runtime is intentionally reused.

Revision 2 has no observer. Revision 3 may inject exactly one
`EditorOperationalObserverV1.emit(event)` sink at its application composition
boundary. Its closed event enum and order are:

```text
OPERATION_ACCEPTED
PREPARATION_COMPLETED
GENERATION_STARTED
GENERATION_COMPLETED | GENERATION_FAILED | GENERATION_CANCELLED
```

The Revision 3-only contracts are exact:

```python
class EditorOperationalEventCodeV1(StrEnum):
    OPERATION_ACCEPTED = "operation_accepted"
    PREPARATION_COMPLETED = "preparation_completed"
    GENERATION_STARTED = "generation_started"
    GENERATION_COMPLETED = "generation_completed"
    GENERATION_FAILED = "generation_failed"
    GENERATION_CANCELLED = "generation_cancelled"

@dataclass(frozen=True, slots=True)
class EditorOperationalEventV1:
    code: EditorOperationalEventCodeV1
    source_report_fingerprint: str
    failure_code: str | None = None

class EditorOperationalObserverV1(Protocol):
    def emit(self, event: EditorOperationalEventV1) -> None: ...
```

Observer injection is optional and absence means no event calls. Static
dependency validation follows section 15.7 with exact `emit` annotations and
must not execute the observer.

Each applicable event occurs once. Events contain only event code, source
report fingerprint, and safe failure code or null. They contain no prompt,
input, output, provider message, exception, client, executor, or timing.
Observer exceptions are ignored and suppressed; they never affect execution,
retry, result, cleanup, or persistence. Lower-runtime events are not forwarded
or duplicated. This observer is not part of Revision 2 public API.

Revision 3 entry gates are: verified Revision 2; resolved configuration
preservation; offline proof of exact prompt/JSON/schema mapping; and proof that
timeout retry, cancellation precedence, and cleanup match this section. Exit
gates are: exact OpenAI/Ollama fake executions; one lower call per adapter call;
at most two calls only for timeout; fresh request/cancellation per call; zero
fallback; exact observer sequence; exact cleanup once; full offline suite and
static gates; independent verification. Failure of any gate prohibits runtime
rollout.

## 18. Persistence, Producer, and CLI contracts

Revisions 2 and 3 perform zero persistence and expose no persistence field.

Revision 4's `editor-run` caller owns output. The exact command is:

```text
pastila-scout editor-run --provider {openai,ollama} --input INPUT --output OUTPUT
```

All three arguments are required. Input must be one canonical
`ScoutEditorInputV1`. Provider accepts exactly lowercase `openai` or `ollama`.
There is no default, alias, normalization, environment selection, discovery, or
fallback. Before Revision 4, explicit authorities for selection profile,
episode context, and generation configuration MUST be specified; until then
Revision 4 is blocked.

The caller serializes one completed `EditorOperationalResultV1` as canonical
UTF-8 JSON using the section 15.2 rules, ending with one LF. `--output` is the
sole destination authority. Existing files are never overwritten; existence is
a configuration failure. The caller writes a temporary file in the destination
directory, flushes and closes it, and atomically replaces a nonexistent
destination. Any failure removes only that owned temporary file and leaves no
partial destination. No failed/cancelled result is written.

Revision 4 exit codes are exact: `0` completed and written; `2` invalid CLI,
configuration, input, provider, destination, or serialization; `3` provider or
generation failure; `4` timeout; `5` cancellation; `6` output-write failure.
Output is fixed and content-safe. Help/import performs no credential access,
composition, provider selection/execution, network, input read, output write,
thread, subprocess, warning, or logging.

`EditorOperationalResultV1` is a Revision 3 contract containing exact source
lineage, `EditorAgentOutputV1`, completed `EpisodeDraft` or absence, closed
status, safe failure or absence, and safe generation trace/manifest projection.
Its exact implementation contract MUST be independently specified before
Revision 3; Revision 2 does not export it.

Revision 5 source is exactly one completed `EditorOperationalResultV1` in
memory. No existing Producer destination accepts it. Revision 5 is therefore
HARD BLOCKED until an exact Producer-owned input contract, transformation
owner, validation owner, lineage, structured-component policy, and
absence/failure behavior are specified and independently reviewed. No
destination contract is invented here; Producer is never modified in Revision
2–4.

## 19. Exact Revision 2 adversarial test matrix

`tests/test_editor_operational_v1.py` SHALL cover all of the following offline:

1. exact package exports and ordered `__all__`;
2. valid coordinator construction with a statically valid fake engine;
3. rejection of missing method, wrong callable kind, name, count, layout,
   default, or annotation;
4. rejection of property, cached property, staticmethod, classmethod, partial,
   wrapped callable, forged signature, dynamic attribute, and callable object;
5. dependency validation invokes no dependency body or hooks;
6. exact-type/no-coercion validation for every contract field;
7. copied-invalid source/profile/context, plan, failure, result, and coordinator
   rejection;
8. exact success lifecycle and deterministic canonical representation;
9. every closed failure lifecycle/code/message/retryability/absence invariant;
10. exact call order and reconstructed argument identity/value behavior;
11. `SelectionEngine.select` exactly once on valid input and zero on invalid
    input;
12. exact `EditorAgentOutputV1` cross-validation and trace/ID lineage;
13. deterministic repeated preparation equality;
14. `ControlledGenerator`, `PromptBuilder`, provider selector/executor,
    credentials, network, persistence, cleanup, observer, filesystem, database,
    clock, timer, thread, and subprocess call counts all zero;
15. repr is address-free and contains no input, output, trace, dependency repr,
    path, credential, or generated content;
16. exact copy/deepcopy behavior and pickle rejection for every public object;
17. recursively sanitized errors, explicit cause/context suppression, and no
    authorities or content retained in package traceback locals;
18. passive package/submodule import and inert construction with no output,
    warning, logging, filesystem, environment, credential, network, or runtime
    access;
19. dependency graph contains no provider implementation, SDK, CLI,
    persistence, private frozen helper, registry, discovery, or service locator;
20. all frozen module regression tests and hash/export integrity; and
21. required focused/full tests and static quality gates.

## 20. Exact phase gates

### Revision 2 — deterministic preparation foundation

- Entry: this specification independently implementation-ready; Phase 4.1
  baseline exact and clean.
- Authorized: the five files in section 15.1 and the one focused test.
- Forbidden: every provider/runtime/CLI/persistence/Producer/observer/generation
  execution change and every existing file.
- Exit: section 19 passes, full suite/static gates pass, production API exact,
  no generation side effects.
- Review: independent verification before any freeze.
- Rollback: remove only the additive package and focused test.
- Commit/tag: prohibited until verified; then one scoped commit/tag under a
  separately authorized Git operation.

### Revision 3 — provider-neutral generation

- Entry: verified Revision 2 and every section 16–17 hard gate closed.
- Authorized files, once their exact contracts receive independent review:
  `src/pastila_scout/editor_operational_execution_v1/{__init__.py,adapter.py,composition.py,errors.py,models.py,observer.py}`,
  `src/pastila_scout/editor_operational_v1/{__init__.py,coordinator.py,models.py}`
  only for explicitly specified additive Revision 3 exports/execution, and
  `tests/test_editor_operational_execution_v1.py`; frozen provider/application
  modules remain unchanged.
- Forbidden: CLI, persistence, Producer handoff, fallback, routing, provider
  changes, prompt/schema/validator changes.
- Exit: exact structured mapping, retry/cancellation/observer/cleanup tests,
  OpenAI/Ollama offline paths, full suite/static gates, independent verification.
- Rollback: remove Revision 3 additive files and explicitly authorized Revision
  2 extensions only.
- Commit/tag: only after independent verification and separate authorization.

### Revision 4 — CLI and caller-owned atomic export

- Entry: verified Revision 3 plus independently reviewed explicit configuration
  and `EditorOperationalResultV1` serialization contracts.
- Authorized files:
  `src/pastila_scout/editor_cli_run_v1/{__init__.py,command.py,errors.py,rendering.py,serialization.py}`,
  the minimal `editor-run` parser/dispatch additions in
  `src/pastila_scout/cli.py`, and `tests/test_editor_cli_run_v1.py`.
- Forbidden: existing command changes, provider/runtime changes, Producer,
  database persistence, fallback/routing.
- Exit: exact arguments/exits/output/atomicity/passivity, offline provider fakes,
  legacy CLI regression, full suite/static gates, independent verification.
- Rollback: remove command package and its isolated registration/tests.
- Commit/tag: only after independent verification and separate authorization.

### Revision 5 — Producer handoff

- Entry: verified Revision 4 and an independently implementation-ready exact
  Producer destination specification; otherwise blocked.
- Authorized files, after the destination contract review:
  `src/pastila_scout/editor_producer_handoff_v1/{__init__.py,composition.py,errors.py,mapping.py,models.py}`
  and `tests/test_editor_producer_handoff_v1.py`; no existing Producer file.
- Forbidden: provider, generation, CLI, persistence, retry, routing, Scout,
  ranking, queue, or GUI changes.
- Exit: exact lineage/transformation/validation/absence tests, no failed-result
  handoff, full suite/static gates, independent verification.
- Rollback: remove only additive handoff files/tests.
- Commit/tag: only after independent verification and separate authorization.

Every revision SHALL run its focused tests, `pytest -p no:cacheprovider`, Ruff,
Black, compileall, pip check, and `git diff --check`, with exact results reported.

## 21. Contradiction closure

The following rules are final and non-overlapping:

- Revision 2 coordinator invokes `SelectionEngine` once and never invokes
  `ControlledGenerator`.
- Revision 2 returns `EditorOperationalPreparationResultV1`; it does not return
  a draft or `EditorOperationalResultV1`.
- Revision 3 `LanguageModelProvider` adapter parses exact generated JSON once,
  strictly validates it, and returns the validated model to
  `ControlledGenerator`; raw text is not its return type.
- `ControlledGenerator` is the sole retry owner, including its one immediate
  timeout retry; each adapter call performs one lower execution.
- Revision 2 failures use the exact closed failure contract and never contain a
  plan or draft.
- Revision 2 has no observer. Revision 3 has at most the single observer and
  exact events/failure policy in section 17.
- Persistence is absent in Revisions 2–3 and caller-owned only in Revision 4.
- Producer handoff is absent through Revision 4 and blocked until its
  destination contract exists.

## 22. Revision 2 passive behavior

Importing any Revision 2 module and constructing any valid or invalid Revision
2 object SHALL perform zero provider execution or selection, networking,
credential/environment access, client construction, prompt construction or
execution, generation, persistence, filesystem or database access, cleanup,
observer emission, clock/timer access, threads, subprocesses, polling, logging,
warnings, stdout, or stderr. `prepare` performs only the exact deterministic
operations in section 15.9. No import-time instance, registry, cache, singleton,
or mutable module state is permitted.
