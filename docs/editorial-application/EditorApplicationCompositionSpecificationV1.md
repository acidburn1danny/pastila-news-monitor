# Phase 4.3 — Editor Application Composition Specification V6

Status: **normative specification — implementation-ready**

Baseline: `phase-4.3-editor-application-export-r4-verified` /
`d9fe8d613da972ec2728dd08e1b82e96fb53aca5`

## 1. Scope and normative language

The words **MUST**, **MUST NOT**, **SHALL**, and **SHALL NOT** are normative.
This document specifies the first application-owned boundary above the verified
Editor operational execution coordinator. It implements nothing. Producer,
GUI, queue, scheduling, database persistence, provider behavior, prompt
behavior, retry, and lower cleanup are outside its scope.

The aggregate execution-request authority and Revision 2--4 application
prerequisites are verified. Coordinator implementation remains revision-gated
by the serialized-result authority in section 6.6 and the roadmap in section
20; no checksum authority remains implicit.

## 2. Repository grounding

### 2.1 Existing Scout input boundary

`export_editor_input(EventRankingReport, EditorInputExportContext)` produces one
`ScoutEditorInputV1` without recalculating Scout scores. Its authoritative
identity is `report_id` plus `content_fingerprint`, calculated by
`contracts.identity.assign_scout_input_identity`. `verify_scout_input_identity`
recomputes both.

`contracts.io.load_contract(path)` is the existing public file authority for:

- `ScoutEditorInputV1`, maximum 25 MiB;
- `SelectionProfileV1`, maximum 1 MiB; and
- `EpisodeContextV1`, maximum 1 MiB.

It accepts one local regular non-symlink UTF-8 JSON file, rejects duplicate
keys, network/device paths and unsupported contract versions, validates with
strict Pydantic mode, and verifies Scout identity. It is reused; Phase 4.3 does
not implement competing loaders.

`contracts.identity.canonical_json_bytes` is the existing canonical JSON
primitive: UTF-8, `ensure_ascii=False`, sorted keys, compact separators, and
nonfinite-number rejection. `contracts.io.write_contract` adds one LF, writes a
same-directory temporary file, flushes and fsyncs, and calls `Path.replace`.
It is not directly reusable for Phase 4.3 because it does not accept
`EditorOperationalResultV1`, creates parents, and silently replaces an existing
destination.

### 2.2 Existing deterministic Editor preparation

`EditorOperationalCoordinatorV1(selection_engine)` exposes exactly:

```python
prepare(
    scout_input: ScoutEditorInputV1,
    selection_profile: SelectionProfileV1,
    episode_context: EpisodeContextV1,
) -> EditorOperationalPreparationResultV1
```

It invokes the existing `SelectionEngine` once and returns a sealed preparation
result containing an `EditorGenerationPlanV1` on success. Its safe preparation
failure contract remains authoritative.

The deterministic artifacts required by generation are currently built by the
existing public `EpisodeFlowOptimizer`, `EditorialBlueprintBuilder`,
`CommentaryBlueprintBuilder`, and `VoiceModelBuilder`, in that order. Phase 4.3
must compose them without changing their logic.

### 2.3 Existing generation and runtime authorities

`EditorGenerationExecutionRequestV1` has, in order:

```text
preparation, plan, flow_result, editorial_blueprint,
commentary_blueprint, voice_plan, generation_configuration,
runtime_options, provider, requested_at, request_reference,
cancellation, request_fingerprint
```

`LanguageGenerationConfig` carries provider, model identifier/revision,
temperature, top-p, maximum output tokens, seed, structured-output mode, and
timeout. `EditorGenerationRuntimeOptionsV1` is the authoritative provider-neutral
runtime option contract. `ProviderChoiceV1` accepts exactly `openai` or
`ollama`. Timeout and cancellation remain lower verified authorities.

The provider adapter, request-fingerprint authority for
`EditorGenerationApplicationRequestV1`, runtime session factory, runtime
session, `ControlledGenerator`, Scout workflow bridge, selector, OpenAI and
Ollama composition, attempt recorder, retry, and cleanup are frozen.

`EditorGenerationExecutionRequestAuthorityV1` is the sole verified public
aggregate request authority. It is stateless and passive. Its keyword-only
`construct(...)` accepts the twelve semantic fields preceding
`request_fingerprint`, owns the aggregate canonical projection and fingerprint,
calls the frozen constructor once, public-copy reconstructs once, and returns
one validated `EditorGenerationExecutionRequestV1`. Its keyword-only
`reconstruct(request=...)` returns one new validated request. Callers receive
only the fixed `EditorGenerationExecutionRequestAuthorityError` on failure and
can never provide a fingerprint.

### 2.4 Existing operational execution

`EditorOperationalExecutionCoordinatorV1` is constructed with an exact runtime
session factory and controlled-generator factory. It exposes exactly:

```python
execute(request: EditorGenerationExecutionRequestV1) -> EditorOperationalResultV1
```

It reconstructs the request, opens one runtime session, invokes one controlled
generator, snapshots attempt provenance once, closes the session once, and only
then publishes its result. The application never sees or closes the session.

`EditorOperationalResultV1` contains source/preparation/request lineage,
generation status and lifecycle, validated `EpisodeDraft`, trace, manifest,
final state revision, attempt observations, timeout retry count, safe failure,
cleanup status, and its frozen result fingerprint.

### 2.5 Existing CLI conventions

The single `pastila-scout` parser uses subcommands. Provider-neutral commands
accept exact lowercase `openai` and `ollama`. `export-editor-input` requires an
input report and explicit output. `provider-run` is explicit and opt-in.
Imports and help are passive. Commands return integer codes; the library does
not call `sys.exit`. Safe diagnostics go to stderr and canonical files—not
editorial drafts—are the durable output.

## 3. Existing, missing, and future classification

Existing and frozen:

- Scout input export, identity, and contract file loading;
- selection profile and episode context contracts;
- deterministic selection/preparation and artifact builders;
- generation configuration, runtime options, provider selection, timeout and
  cancellation contracts;
- aggregate request construction and reconstruction through
  `EditorGenerationExecutionRequestAuthorityV1`;
- provider-neutral adapter, runtime session, `ControlledGenerator`, lower
  retry and cleanup;
- operational execution and `EditorOperationalResultV1`.

Missing and specified here:

- application configuration authority;
- application request/result contracts and composition root;
- operational-result canonical envelope serializer;
- fail-if-exists atomic filesystem publisher;
- later thin `editor-run` CLI adapter and exit-code projection.

Explicitly future:

- Producer input/mapping/handoff;
- GUI, scheduler, queue, database, cache, history, report registration, or
  automatic execution.

## 4. Dependency direction and ownership

```text
public Scout/Editor contracts
    -> application configuration values
    -> editor_application_v1
    -> frozen preparation and artifact boundaries
    -> EditorGenerationExecutionRequestAuthorityV1
    -> frozen operational execution boundary
    -> application serializer
    -> application atomic publisher
    -> future CLI adapter
```

Lower packages never import `editor_application_v1`. There is no registry,
service locator, provider discovery, mutable singleton, private cross-package
import, fallback, or circular dependency.

Singular owners:

| Authority | Owner |
|---|---|
| Scout/profile/context file parsing | `contracts.io.load_contract` |
| application configuration validation | Phase 4.3 configuration contracts |
| deterministic selection | frozen preparation coordinator |
| deterministic artifact construction | package-private application artifact preparer using frozen builders |
| generation execution-request construction | `EditorGenerationExecutionRequestAuthorityV1` |
| provider selection/execution | frozen runtime |
| provider retry | `ControlledGenerator` |
| runtime cleanup | Revision 3D/lower runtime |
| operational-result serialization | application serializer |
| temporary file and publication | application atomic publisher |
| CLI streams and argument parsing | future CLI adapter |

## 5. Application configuration authorities

### 5.1 Selection profile

`EditorSelectionProfileAuthorityV1.load(*, path: Path) -> SelectionProfileV1`
delegates
exactly once to `load_contract`, requires exact returned type, then reconstructs
with strict Python-mode validation. Its file representation is the existing
`editor-selection-profile-v1` JSON contract. Every existing field and existing
contract default remains frozen; the application adds no default or editorial
normalization. No environment/global profile is permitted.
It also exposes `reconstruct(*, profile: SelectionProfileV1) ->
SelectionProfileV1` for in-memory callers; both operations return a new exact
validated value and share one neutral failure boundary.

### 5.2 Episode context

`EditorEpisodeContextAuthorityV1.load(*, path: Path) -> EpisodeContextV1`
follows the
same rule for `episode-context-v1`. Existing field order and tuple order remain
semantic. It performs no current-date, timezone, locale, language, audience,
theme, or prior-episode inference. Cross-validation requires profile and
context target story counts to agree and all mandatory/excluded/avoid IDs to
be valid against the reconstructed Scout input under existing validators.
It also exposes `reconstruct(*, context: EpisodeContextV1) -> EpisodeContextV1`
with the same exact copied-invalid and safe-failure policy.

### 5.3 Generation configuration

One new immutable `EditorApplicationGenerationConfigurationV1` represents only
caller choices. Its exact ordered fields are:

```python
contract_version: str  # exactly "editor-application-generation-config-v1"
provider: ProviderChoiceV1
model_identifier: str
model_revision: str | None
temperature: float
top_p: float
max_output_tokens: int
seed: None
structured_output_mode: bool
timeout_seconds: float
```

Every field is required, including explicit nullable fields. There are no
application defaults. `temperature` and `top_p` must each be exact built-in
`float`; subclasses, `int`, `bool`, strings, decimal-like objects and every
other type are rejected without coercion or `float(value)`. Both must be
finite. `temperature` is in the frozen inclusive range `0.0 <= value <= 2.0`.
The intersection of the frozen lower contracts requires `top_p == 1.0`:
although `LanguageGenerationConfig` alone accepts `0.0 < top_p <= 1.0`,
`EditorGenerationRuntimeOptionsV1` requires equality to one. Consequently
`top_p=0.5` is invalid in Phase 4.3 and cannot become valid without a separately
authorized frozen-contract revision. `NaN`, positive/negative infinity and
out-of-range floats are rejected. `max_output_tokens` is exact positive
built-in `int` with `bool` rejected; `timeout_seconds` is exact finite positive
built-in `float`; and `seed` is exactly `None`. `structured_output_mode` must
be `True`; V1 supports no stop sequences.

The JSON file is a strict UTF-8 object with no duplicate/extra keys and the
literal contract version. JSON numeric tokens for `temperature`, `top_p` and
`timeout_seconds` must deserialize through the standard JSON decoder as exact
built-in `float`. Thus `1`, which decodes as `int`, is rejected for these
fields, while `1.0` or an exponential token that decodes as `float` may proceed
to range validation. The loader never converts a decoded integer to float, and
canonical configuration representation retains these fields as JSON numbers
originating from exact floats; integer-token and float-token authority remain
distinguishable at loading. A package-owned loader applies the same local-path,
device, symlink, 1 MiB, and duplicate-key safety rules as `load_contract`.
This loader may reuse public path/JSON behavior but may not import its private
helper. It does not read credentials or environment.

The sole owner is
`EditorApplicationGenerationConfigurationAuthorityV1`. Its public
`load(*, path: Path) -> EditorApplicationGenerationConfigurationV1` and
`reconstruct(*, configuration: EditorApplicationGenerationConfigurationV1) ->
EditorApplicationGenerationConfigurationV1` perform exact reconstruction. Its
package-private materialization operation constructs together, exactly once,
the matching `LanguageGenerationConfig` and
`EditorGenerationRuntimeOptionsV1` (with `stop_sequences=()`, exact timeout
policy and exact provider identity). It passes the same already-validated exact
float objects as `temperature` and `top_p` inputs to both constructors, then
requires the reconstructed lower values to satisfy:

```python
type(generation_configuration.temperature) is float
type(runtime_options.temperature) is float
generation_configuration.temperature == runtime_options.temperature
type(generation_configuration.top_p) is float
type(runtime_options.top_p) is float
generation_configuration.top_p == runtime_options.top_p == 1.0
```

There is no post-construction normalization and no second numeric owner. The
coordinator consumes that neutral pair.

`requested_at`, operation reference, and cancellation are live application
authorities and therefore are not stored in this configuration file.
Fingerprints are never caller fields.

An integer `temperature` or `top_p`, Boolean, string, nonfinite float,
out-of-range float, `top_p` other than exact `1.0`, or copied-invalid numeric
state maps only to `invalid_generation_configuration`. Validation occurs before
preparation, so preparation, artifact construction, execution-request
authority, operational execution, serialization, temporary-write and
publication call counts are all zero. The lower request authority is never
used as the primary numeric validator.

## 6. Application request and construction gate

### 6.1 Supporting contracts

```python
class EditorOverwritePolicyV1(StrEnum):
    FAIL_IF_EXISTS = "fail_if_exists"
```

V1 has no default overwrite policy and no replace mode.

`EditorOutputDestinationV1` has exactly:

```python
path: Path
overwrite_policy: EditorOverwritePolicyV1
```

The path is caller-owned, local, already absolute, nonempty, and
must name a nonexistent regular-file destination in an existing local regular
directory. Paths, including Unicode paths, remain exact filesystem authority;
they are never normalized as editorial text.

Reconstruction requires `Path.is_absolute()` and performs no `absolute`,
`resolve`, `expanduser`, environment expansion, or current-directory lookup. It rejects UNC, device, extended
device and drive-relative forms; V1 therefore does not opt into Windows
extended-length paths. `lstat` and, on Windows, `st_file_attributes &
FILE_ATTRIBUTE_REPARSE_POINT` reject symlinks, junctions and reparse parents.
The exporter captures parent identity `(st_dev, st_ino)` at publication entry
and rechecks it immediately before the native call. OS path-length
failure maps to `invalid_destination` before lower work. No path appears in an
error message or repr. Contract construction performs lexical checks only and
is passive. The coordinator's explicit step-6 destination validator performs
the first `lstat` checks before lower work; the exporter independently repeats
them and owns race-safe publication.

### 6.2 `EditorApplicationRequestV1`

Exact ordered fields:

```python
scout_input: ScoutEditorInputV1
selection_profile: SelectionProfileV1
episode_context: EpisodeContextV1
generation_configuration: EditorApplicationGenerationConfigurationV1
destination: EditorOutputDestinationV1
requested_at: datetime
operation_reference: str
cancellation: CancellationTokenV2
```

All nested values are authoritatively reconstructed. The request verifies
Scout identity, profile/context/source cross-lineage, exact provider/config
consistency, aware injected timestamp, safe nonempty operation reference, and
non-cancelled/cancelled token type. It contains no trusted fingerprint, client,
credential, selector, executor, session, factory, serializer, or file handle.

`requested_at` is exact built-in `datetime`, aware with a defined UTC offset,
and is preserved without application conversion. `operation_reference` is an
exact NFC built-in string, nonempty, already stripped and at most 120 code
points. `cancellation` is exact `CancellationTokenV2` and publicly
reconstructed. No clock, reference, path, cancellation, or configuration
default exists in the request constructor.

### 6.3 Object policy

All new values are frozen, slotted, have no `__dict__`, reject subclasses and
coercion, validate retained state before public operations, reject copied-invalid
state, have deterministic equality, return reconstructed copies for copy and
deepcopy, reject pickle, and use fixed address-free content/path-redacted repr.

One package-private application-request reconstruction primitive validates in
field order and returns a neutral finite status plus either one reconstructed
request or `None`. Public copy/deepcopy and the coordinator share that primitive;
there is no second validator. This permits exact mapping to
`invalid_scout_input`, `invalid_selection_profile`, `invalid_episode_context`,
`invalid_generation_configuration`, `invalid_destination`, or
`invalid_application_request` without inspecting exception text. It clears
protected state before the coordinator constructs a public failure.

### 6.4 Cancellation before execution

If the reconstructed token is already cancelled, preparation, execution,
serialization and filesystem call counts are zero and exit code 5 is returned.
Complete request/nested/destination validation precedes that checkpoint, so an
invalid request cannot use an untrusted cancellation value to override its
specific invalid-input failure.
The token is frozen, not a mutable signal. During lower generation the exact
token is passed unchanged through execution-request authority; a lower
cancelled outcome maps to application cancellation and prevents serialization.
There is no application polling during serialization/publication and no
post-validation cancellation checkpoint. Once publication begins, publication
and owned temporary cleanup complete without a second cancellation owner.

### 6.5 Verified execution-request authority integration

The former construction blocker is closed by the verified
`EditorGenerationExecutionRequestAuthorityV1`. The application coordinator
calls its `construct(...)` exactly once after successful preparation and
artifact construction with this exact mapping:

| Authority parameter | Exact application source |
|---|---|
| `preparation` | reconstructed successful `EditorOperationalPreparationResultV1` |
| `plan` | the exact `preparation.plan` identity after public reconstruction |
| `flow_result` | package-private artifact preparer's exact `FlowOptimizationResult` |
| `editorial_blueprint` | artifact preparer's exact `EditorialBlueprint` |
| `commentary_blueprint` | artifact preparer's exact `EpisodeCommentaryBlueprint` |
| `voice_plan` | artifact preparer's exact `EpisodeVoicePlan` |
| `generation_configuration` | strict `LanguageGenerationConfig` derived once from application generation configuration |
| `runtime_options` | strict `EditorGenerationRuntimeOptionsV1` derived once from the same application configuration |
| `provider` | exact `ProviderChoiceV1` shared by configuration and runtime options |
| `requested_at` | exact aware timestamp from `EditorApplicationRequestV1` |
| `request_reference` | exact `operation_reference` from the application request |
| `cancellation` | exact reconstructed application request token |

Generation configuration and runtime options are constructed together by the
configuration authority and cross-validated before this call. No field has a
second application owner. An authority failure maps only to
`execution_request_construction_failed`; operational execution, serialization,
and destination mutation remain zero.

Immediately before the authority call, both lower objects have exact `float`
and equal values for `temperature` and `top_p`, with `top_p == 1.0`; a mixed
numeric-type pair is an `invalid_generation_configuration` and suppresses the
authority call. The verified authority therefore observes float-tagged
canonical values for both fields. The application neither calculates nor
inspects the resulting aggregate fingerprint, and no integer-tagged
representation for either field is possible in Phase 4.3.

A deterministic artifact reconstruction/builder failure maps exactly to
`preparation_failed` because it belongs to deterministic generation
preparation; it is never request-authority, provider, or operational failure.
A malformed injected artifact dependency, forged protocol, wrong static
signature, copied-invalid retained dependency, or post-construction dependency
substitution is rejected by the coordinator/factory's exact static state check
as `EditorApplicationConfigurationError`. Its body is never invoked, execution
does not begin, and no `EditorApplicationResultV1`, lifecycle, operational
result, output path or exit-code-bearing result is created.

The application MUST NOT calculate, accept, configure, validate, compare, or
log the aggregate fingerprint; import the authority's private canonical module;
duplicate its projection; call the frozen request constructor; mutate the
returned request; bypass the authority; or accept any CLI/configuration
fingerprint. It may later copy the public fingerprint from a validated lower
result solely as exported lineage.

## 6.6 Serialized operational-result authority closure

The verified Revision 3 serializer currently exposes only
`EditorOperationalResultSerializerV1.serialize(...) -> bytes`. Its canonical
envelope embeds `payload_sha256`, but that digest is calculated over the
canonical envelope with `payload_sha256` set to the empty string. Consequently,
SHA-256 of the final self-containing bytes does not recover the embedded
digest. No frozen public contract returns the payload and the serializer-owned
digest together. Revision 5 therefore cannot populate
`EditorApplicationResultV1.payload_sha256` without parsing serializer-owned
JSON, duplicating the placeholder algorithm, or trusting caller text.

Specification V5 closes that authority gap through one controlled public
signature revision (Model A). Revision 3A supersedes the Revision 3 serializer
contract:

```python
EditorOperationalResultSerializerV1.serialize(
    *, result: EditorOperationalResultV1,
) -> EditorSerializedOperationalResultV1
```

There is no compatibility method returning raw bytes, no second serialization
entry point, and no public extraction helper. All callers migrate to
`serialized.payload`. This intentionally breaks the Revision 3 raw-byte return
contract so payload construction and checksum calculation retain one owner.
An additive authoritative method (Model B) is rejected because it leaves two
public serialization entry points and ambiguous coordinator usage. A separate
extraction/reconstruction authority (Model C) is rejected because it adds a
second public operation over already-built bytes and is strictly more complex
than returning the serializer-owned pair at its point of creation.

`EditorSerializedOperationalResultV1` is defined in `serialization.py` and has
exactly these ordered fields:

```python
payload: bytes
payload_sha256: str
```

Its exact constructor is
`EditorSerializedOperationalResultV1(payload: bytes, payload_sha256: str)`.
It contains no schema-name, schema-version, operation-reference, execution
fingerprint, destination, provider, runtime or filesystem field: those values
are either already embedded authoritatively or are not needed across this
boundary.

The contract is frozen, slotted, exact-type validated and subclass-rejecting,
with no `__dict__` or mutable buffer. Its deterministic repr is exactly
`EditorSerializedOperationalResultV1(payload=<redacted>,
payload_sha256=<redacted>)`. Equality compares the two reconstructed public
values. `copy.copy` and `copy.deepcopy` return independent authoritative
reconstructions; pickle is rejected before payload traversal. Construction,
copy, equality and repr expose only `EditorApplicationSerializationError` on
invalid state, raised from `None` with cleared context and no payload, checksum,
schema or parser detail.

Construction requires exact built-in `bytes`, exact built-in `str`, and all
canonical payload rules in section 10. Every copy reconstruction additionally
requires the exact wrapper type and exact two-field slotted state.
Reconstruction parses and validates the envelope only inside
`serialization.py`, re-encodes it canonically, blanks `payload_sha256`, performs
the one reconstruction-owned checksum calculation, and requires public,
embedded and recomputed checksums to be identical. Hidden or additional object
state, copied-invalid payload/checksum state, noncanonical encoding and
equality-only validation are rejected.

## 7. Application composition root

`EditorApplicationCoordinatorV1` is the sole public
application coordinator. Its constructor receives exact statically validated:

- package-private preparation adapter retaining one exact
  `EditorOperationalCoordinatorV1`;
- package-private deterministic artifact preparer;
- exact `EditorGenerationExecutionRequestAuthorityV1` identity;
- package-private execution adapter retaining one exact
  `EditorOperationalExecutionCoordinatorV1`;
- application result serializer; and
- application atomic publisher.

The caller constructs these dependencies at command time through one
package-private factory. The factory composes provider-specific clients only
through the verified runtime-session factory; parsing/help constructs nothing.
The coordinator receives the already-composed execution coordinator and never
sees selectors, executors, clients, credentials, runtime sessions, adapters, or
generator factories.

Its exact constructor is keyword-only:

```python
EditorApplicationCoordinatorV1(
    *,
    preparation: _EditorPreparationDependencyV1,
    artifacts: _EditorArtifactDependencyV1,
    execution_request_authority: EditorGenerationExecutionRequestAuthorityV1,
    operational_execution: _EditorOperationalExecutionDependencyV1,
    serializer: _EditorSerializerDependencyV1,
    exporter: _EditorExporterDependencyV1,
)
```

It exposes only `execute(*, request: EditorApplicationRequestV1) ->
EditorApplicationResultV1`. The command-time package-private composition
factory creates the three configuration authorities, exact verified runtime
session/generator composition, the two lower coordinator adapters, artifact
preparer, exact request authority, serializer, exporter and application
coordinator once. The future CLI owns the injected clock/reference and initial
cancellation value. No other component constructs or retains these objects.

Coordinator retained-dependency identity is authoritatively checked before
application-request reconstruction on every `execute` call. Failure raises
`EditorApplicationConfigurationError` from `None` and performs zero request,
preparation, artifact, authority, operational, serialization or filesystem
work. Static construction-time rejection and this copied-invalid/substitution
boundary are configuration errors, never application execution outcomes.

Protocols use exact ordinary methods, keyword-only parameters, exact
annotations and exact return types. Static validation uses
`inspect.getattr_static`, rejects descriptors, wrappers, partials, forged
signatures, dynamic attribute classes and instance replacement, and invokes no
dependency body, repr, equality, or descriptor.

## 8. Exact execution sequence

1. reconstruct `EditorApplicationRequestV1`;
2. reconstruct and identity-check `ScoutEditorInputV1`;
3. reconstruct `SelectionProfileV1`;
4. reconstruct `EpisodeContextV1`;
5. reconstruct application generation configuration;
6. validate cross-object lineage, then reconstruct and validate the destination
   policy without mutation, then apply the single initial-cancellation
   checkpoint; destination rejection therefore precedes cancellation;
7. invoke `EditorOperationalCoordinatorV1.prepare` exactly once;
8. require a successful preparation and exact plan;
9. build flow, editorial blueprint, commentary blueprint and voice plan once
   through the package-private artifact preparer;
10. invoke `EditorGenerationExecutionRequestAuthorityV1.construct(...)`
    exactly once using section 6.5;
11. invoke `EditorOperationalExecutionCoordinatorV1.execute(...)` exactly once;
12. public-copy reconstruct `EditorOperationalResultV1`;
13. classify the application terminal state;
14. only for a completed, cleanup-successful result, serialize exactly once and
    receive one validated `EditorSerializedOperationalResultV1`;
15. invoke the sole package-private
    `_reconstruct_completed_application_candidate` integrity operation and
    construct the immutable completed `EditorApplicationResultV1` with its
    intended destination and exact `serialized.payload_sha256`, but do not
    expose it;
16. if and only if step 15 succeeds, atomically publish exactly once;
17. after successful publication, return the already validated completed result.

Invalid input calls every downstream dependency zero times. Preparation failure
is returned in memory and is not serialized. Execution failure/cancellation is
returned in memory and is not serialized. V1 exports only a completed,
cleanup-successful operational result containing a draft. There is no failure
artifact file.

There is no alternate sequence, application retry, direct provider execution,
direct frozen request construction, application-owned lower cleanup, or result
construction after successful publication. If step 16 fails, the prevalidated
completed candidate is discarded and the exact export failure result is
returned.

## 9. Application result and lifecycle

`EditorApplicationStatusV1` contains exactly `completed`, `failed`, and
`cancelled`. Lifecycle states are exactly `accepted`, `validated`, `prepared`,
`executed`, `serialized`, `exported`, `completed`, `failed`, `cancelled`.

`EditorApplicationFailureCodeV1` contains exactly:

```text
invalid_application_request
invalid_scout_input
invalid_selection_profile
invalid_episode_context
invalid_generation_configuration
preparation_failed
execution_request_construction_failed
operational_execution_failed
serialization_failed
invalid_destination
destination_exists
export_failed
export_cleanup_failed
internal_application_failure
cancelled
```

`EditorApplicationResultV1` exact ordered fields are:

```python
operation_reference: str | None
status: EditorApplicationStatusV1
lifecycle: tuple[EditorApplicationLifecycleStateV1, ...]
operational_result: EditorOperationalResultV1 | None
output_path: Path | None
payload_sha256: str | None
exported: bool
handoff_permitted: bool
failure: EditorApplicationFailureV1 | None
exit_code: EditorApplicationExitCodeV1
```

Completed requires an operational result, output path and checksum, exported
and handoff permitted true, no failure, and exit 0. Every other state has no
output path/checksum, exported and handoff false. Preparation failure has no
operational result. Operational failures retain only the reconstructed safe
operational result. Serialized bytes are never retained in the result.

Fixed messages and retryability:

| Code | Message | Retryable |
|---|---|---:|
| invalid_application_request | `Editor application request is invalid.` | false |
| invalid_scout_input | `Editor Scout input is invalid.` | false |
| invalid_selection_profile | `Editor selection profile is invalid.` | false |
| invalid_episode_context | `Editor episode context is invalid.` | false |
| invalid_generation_configuration | `Editor generation configuration is invalid.` | false |
| preparation_failed | `Editor preparation failed.` | false |
| execution_request_construction_failed | `Editor execution request construction failed.` | false |
| operational_execution_failed | `Editor operational execution failed.` | false |
| serialization_failed | `Editor result serialization failed.` | false |
| invalid_destination | `Editor output destination is invalid.` | false |
| destination_exists | `Editor output destination already exists.` | false |
| export_failed | `Editor output export failed.` | false |
| export_cleanup_failed | `Editor output cleanup failed.` | false |
| internal_application_failure | `Editor application execution failed.` | false |
| cancelled | `Editor application execution was cancelled.` | false |

Closed observability rules:

| Failure family | Operational result | Output/checksum | Destination mutation | Exit |
|---|---|---|---|---:|
| invalid application/Scout/profile/context/configuration/destination or initially existing destination | absent | absent | none | 2 |
| preparation failed | absent | absent | none | 3 |
| execution-request construction failed | absent | absent | none | 3 |
| operational failure | reconstructed safe result present | absent | none | 3 |
| lower timeout | reconstructed safe result present | absent | none | 4 |
| lower cleanup failure | reconstructed safe result present | absent | none | 7 |
| cancellation | lower safe result only when cancellation occurred below | absent | none | 5 |
| serialization failure | reconstructed completed result present | absent | none | 6 |
| destination-exists race at publication | reconstructed completed result present | absent | destination unchanged | 2 |
| export failure | reconstructed completed result present | absent | destination absent/unchanged | 6 |
| export cleanup failure | reconstructed completed result present | absent | destination absent/unchanged | 7 |
| completed-candidate integrity failure (the sole internal source) | exact reconstructed completed result present | absent | none; no temporary file exists | 7 |

Every failed/cancelled result has `exported=False` and
`handoff_permitted=False`. Serialized bytes, temporary paths and lower
exceptions are never retained. All retryability values are `False` in V1.

Lifecycle projection is closed and is not inferred by callers. A state is
appended only after its named phase succeeds; the terminal state is appended
exactly once:

| Outcome or failure point | Exact lifecycle |
|---|---|
| request or nested-authority reconstruction invalid | `(accepted, failed)` |
| destination invalid/existing before work | `(accepted, validated, failed)` |
| initially cancelled after complete validation | `(accepted, validated, cancelled)` |
| preparation or artifact construction failed | `(accepted, validated, failed)` |
| execution-request authority failed | `(accepted, validated, prepared, failed)` |
| operational execution failed, timed out, or lower cleanup failed | `(accepted, validated, prepared, executed, failed)` |
| operational execution returned cancelled | `(accepted, validated, prepared, executed, cancelled)` |
| serialization failed | `(accepted, validated, prepared, executed, failed)` |
| completed-candidate integrity failure (sole internal source) | `(accepted, validated, prepared, executed, serialized, failed)` |
| destination race, publication, or application cleanup failed | `(accepted, validated, prepared, executed, serialized, failed)` |
| completed | `(accepted, validated, prepared, executed, serialized, exported, completed)` |

`prepared` therefore means that preparation and all four deterministic
artifacts succeeded. `executed` means that the one operational invocation
returned a reconstructable result, including a failed or cancelled result; an
exception before such a result does not append `executed`.

`operation_reference` is `None` only when the application request or a nested
authority cannot be authoritatively reconstructed. Every outcome after
successful request reconstruction, including destination rejection and
initial cancellation, carries the exact reconstructed application operation
reference. No failure path derives, shortens, or replaces it.

### 9.1 Exhaustive internal-failure authority

`internal_application_failure` has exactly one permitted source. No future or
unenumerated source is implicitly included:

| Source identifier | Owning operation | Exact allowed condition | Lifecycle | Operational result | Private serialized bytes/checksum | Temporary file | Destination | Handoff | Retryable | Exit | Cleanup | Local precedence |
|---|---|---|---|---|---|---|---|---|---:|---:|---:|---|
| `completed_candidate_integrity_failed` | package-private `_reconstruct_completed_application_candidate(*, state: _CompletedApplicationCandidateStateV1)` called only at execution step 15 | that helper's explicit invariant checks raise exact package-private `_CompletedApplicationCandidateIntegrityError`; no other exception maps here | `(accepted, validated, prepared, executed, serialized, failed)` | exact reconstructed completed `EditorOperationalResultV1` | bytes may have existed privately on entry but are cleared; public payload and checksum are absent | none; exporter has not been called | absent/unchanged | false | false | 7 | none | emitted immediately after successful serialization; it cannot coexist with serialization, export or cleanup failure |

`_CompletedApplicationCandidateStateV1` is package-private, frozen and slotted
and contains only the exact reconstructed operational result, exact intended
destination and exact reconstructed `EditorSerializedOperationalResultV1`
needed to construct the completed candidate. The state type, helper and private
integrity error are
defined only in `application.py`. The helper calls no injected dependency, performs no
I/O, owns no resource, and validates only the application-owned completed-result
field parity from sections 9 and 10. It either returns one reconstructed
completed `EditorApplicationResultV1` or raises the exact private integrity
error from an explicit invariant check. It uses no broad catch. Failure locals
are cleared before the private error crosses the helper boundary, and it cannot
call or classify a dependency exception.

The coordinator catches only exact `_CompletedApplicationCandidateIntegrityError`
around this single helper call, clears the private error/state/bytes/checksum
locals, and constructs the one failed result combination below. Any other
exception follows `EditorApplicationCoordinatorError`; exception type, text,
cause, context or traceback is never inspected to select the internal code.

The failed `EditorApplicationResultV1` for this one source has the exact
operation reference, the exact reconstructed operational result, failure code
`internal_application_failure`, fixed safe message, lifecycle and exit above,
`output_path=None`, `payload_sha256=None`, `exported=False`, and
`handoff_permitted=False`. Authoritative reconstruction rejects every other
internal-code lifecycle, result-presence, path, checksum, exported, handoff,
retryability or exit-code combination.
If construction or authoritative reconstruction of this exact failed result
itself does not succeed, that is not a second internal source: no result is
returned and the fixed `EditorApplicationCoordinatorError` boundary in section
17 applies.

There is no private composition-state internal source. Retained dependency
state is handled only by the public configuration boundary in section 7.
Malformed definitions and injected/lower/request-authority/operational/
serializer/exporter/cleanup exceptions never map to
`internal_application_failure`; they use their exact existing category or the
unexpected-defect boundary in section 17.

## 10. Serialization and export envelope

`EditorOperationalResultSerializerV1.serialize(result) ->
EditorSerializedOperationalResultV1` reconstructs the exact result and accepts
only completed, cleanup-successful results with a draft. It produces one
serialized-result authority containing the final canonical payload and its
serializer-owned checksum. The payload contains this envelope:

```json
{
  "schema_name": "pastila-editor-operational-export",
  "schema_version": "1",
  "operation_reference": "<application authority>",
  "source_lineage": {
    "source_report_id": "<lower exact>",
    "source_report_fingerprint": "<lower exact>",
    "preparation_result_fingerprint": "<lower exact>",
    "execution_request_reference": "<lower exact>",
    "execution_request_fingerprint": "<lower exact>"
  },
  "operational_result": "<exact public field projection>",
  "payload_sha256": ""
}
```

No exported-at timestamp is included: it would introduce a second clock and
make bytes nondeterministic. The injected `requested_at` already participates
in lower request authority and is deliberately not duplicated as an
informational field. The envelope repeats lower lineage only as exact
copies for discoverability; validation requires equality with the nested
result. It fabricates no lineage.

Field ownership is exact: schema name/version are serializer constants;
`operation_reference` is the lower exact execution request reference;
source/preparation/execution fingerprints are copied authoritative lower
lineage; `operational_result` is the serializer's public projection;
`payload_sha256` is the sole derived application checksum. The execution
request fingerprint is copied, never recalculated or independently validated.

The serializer projects all and only the 17 public result fields. Enums use
their string values; tuples use arrays preserving order; `None` uses JSON
`null`; Pydantic draft/trace/manifest/attempts use strict public JSON-mode
projection; integers and booleans remain exact. Floats must be finite and use
Python JSON shortest round-trip form. All strings are already reconstructed;
the serializer applies NFC to JSON string values and keys without mutating
sources and rejects any normalization-created key collision. It uses sorted keys, compact separators, `ensure_ascii=False`,
`allow_nan=False`, UTF-8, and exactly one terminal LF.

`payload_sha256` is calculated over canonical bytes with that field set to the
empty string, then stored as lowercase `sha256:<64 hex>`, and the final bytes
are reserialized. Reconstruction blanks and recomputes it. No `repr`, raw
provider response/message, prompt, credential, exception, traceback, client,
executor, selector, runtime session, or private state appears.

The public payload is exact built-in `bytes`, nonempty UTF-8 without BOM, one
canonical JSON object and exactly one terminal LF. CRLF, missing or duplicate
LF, trailing data, invalid UTF-8, nonobject roots, duplicate keys, nonfinite
numbers, normalization-created key collisions, unknown top-level fields,
wrong schema name/version, and noncanonical re-encoding are invalid. The final
object contains exactly one `payload_sha256` field.

The checksum algorithm is singular and exact:

1. construct the semantic envelope with `payload_sha256=""`;
2. encode with UTF-8, sorted keys, compact separators, `ensure_ascii=False`,
   `allow_nan=False`, NFC string values/keys and exactly one terminal LF;
3. calculate SHA-256 exactly once over those placeholder bytes;
4. format `sha256:` followed by 64 lowercase hexadecimal characters;
5. insert that value into the envelope;
6. encode the final payload once using the identical canonical settings; and
7. construct `EditorSerializedOperationalResultV1(final_payload, checksum)`
   exactly once and return that directly constructed contract.

Nominal serializer cardinality is therefore: operational-result
reconstruction one, semantic projection one, placeholder encoding one,
serializer production SHA-256 calculation one, final encoding one,
serialized-result construction one, and constructor-owned validation SHA-256
calculation one. Total nominal SHA-256 calculations are exactly two: one
production calculation owned by the serializer and one validation calculation
owned by the public wrapper constructor. There is no second production
checksum, serialization, alternate bytes method, final-payload hash or
coordinator hash.

The constructor must validate through the public path. A trusted/private
constructor bypass, skipped validation or wrapper trust in caller checksum text
is prohibited. Later `copy.copy` or `copy.deepcopy` reconstruction performs
exactly one new validation SHA-256 calculation per invocation and performs no
production checksum calculation or payload construction. Production and
validation checksum calculations have distinct responsibilities even though
both use the same normative placeholder preimage and must produce the same
value.

Reconstruction parses only inside `serialization.py`. It requires exact schema
and field sets, reconstructs the canonical semantic projection, requires final
canonical re-encoding byte parity, reads the embedded checksum, substitutes the
normative blank value, canonically encodes that placeholder representation and
recomputes SHA-256 once. The embedded checksum, public `payload_sha256` and
recomputed checksum must be identical. In particular, SHA-256 of the final
self-containing payload is neither authoritative nor accepted as a substitute.

Invalid/ineligible operational results, canonical projection, placeholder
encoding, checksum calculation, final encoding, wrapper construction,
wrapper reconstruction, canonical mismatch, checksum-shape mismatch,
embedded/public mismatch, recomputed mismatch and finite package-owned
serialization corruption all raise only `EditorApplicationSerializationError`
with its fixed content-free message from `None`. Payload/checksum/schema,
result/draft/trace/manifest/fingerprint and raw parser/exception detail never
cross that boundary.

Revision 5 treats the wrapper as opaque authority. It calls `copy.copy` once in
the completed-candidate helper, uses `serialized.payload` only as the exporter
argument, and uses `serialized.payload_sha256` only as the completed
application-result checksum. It does not parse, textually extract, re-encode,
hash, compare, mutate or independently validate either field. Failed and
internal application results expose neither; a successful result retains only
the checksum and output path, never the payload.

The exact Revision 5 integration is:

```python
serialized = serializer.serialize(result=operational_result)
completed_candidate = _reconstruct_completed_application_candidate(
    state=_CompletedApplicationCandidateStateV1(
        operational_result=operational_result,
        destination=destination,
        serialized=serialized,
    )
)
exporter.publish(payload=serialized.payload, destination=destination)
return completed_candidate
```

The helper public-copy reconstructs `serialized` once, requires an exact
completed operational result and exact destination/result lineage, and builds
the prevalidated success result using only `serialized.payload_sha256`. It
delegates payload canonicality and checksum parity entirely to wrapper
reconstruction. It performs no JSON parsing, checksum calculation, textual
extraction, serializer-private import, dependency call or I/O. After successful
publication no result construction or reconstruction remains.

## 11. Atomic export and overwrite policy

`EditorAtomicExporterV1.publish(payload: bytes, destination:
EditorOutputDestinationV1) -> Path` owns filesystem publication. It requires
exact bytes ending in one LF and `FAIL_IF_EXISTS`.

Revision 5 passes exactly `serialized.payload`. The exporter remains opaque to
the envelope and checksum, receives no wrapper or checksum argument, and owns
no checksum validation or calculation.

Rules:

1. resolve a caller path without network/device prefixes;
2. require an existing regular parent directory; do not create parents;
3. reject an existing destination of any kind, symlink, junction, mount point,
   or other reparse point;
4. create exactly one exclusive temporary regular file with `tempfile.mkstemp`
   in the destination directory and an application-owned random suffix;
5. verify the opened temporary identity from its descriptor; write all bytes;
6. flush and `os.fsync` the open file, close it exactly once;
7. recheck destination absence and parent identity;
8. invoke one package-private `_NoReplaceAtomicPublisherV1.publish_existing`
   native adapter that transfers the same-directory temporary name to the
   destination atomically and refuses an existing destination;
9. on every pre-publication failure, close the owned descriptor and unlink
    only the exact owned temporary path.

The native adapter is required because portable Python rename APIs do not
provide cross-platform no-replace atomic publication. Its exact implementations
are:

- Windows: `MoveFileExW(temp, destination, MOVEFILE_WRITE_THROUGH)` with
  `MOVEFILE_REPLACE_EXISTING` absent; `ERROR_FILE_EXISTS` and
  `ERROR_ALREADY_EXISTS` map to `destination_exists`;
- Linux: `renameat2(AT_FDCWD, temp, AT_FDCWD, destination,
  RENAME_NOREPLACE)`; `EEXIST` maps to `destination_exists`;
- macOS: `renamex_np(temp, destination, RENAME_EXCL)`; `EEXIST` maps to
  `destination_exists`.

The adapter is selected statically by the package-private composition factory,
not discovered at execution. Unsupported platforms/filesystems fail closed as
`export_failed` before temporary creation. Native calls use exact absolute
same-parent paths and preserve the OS error only as a neutral private status.
Focused platform tests must exercise real or sealed adapter calls plus races.
V1 guarantees atomic visibility and fsynced file content, not directory-entry
crash durability; it performs no fallible operation after successful native
publication. Therefore a failed application result can never coexist with a
published destination.

Destination existence races map to `destination_exists`. Permission, disk
full, short write, native publication failure and unsupported atomicity map
to `export_failed`. If temporary cleanup then fails, `export_cleanup_failed` has final
precedence. A successfully published destination is never deleted during later
result construction. No partial destination is permitted.

The application does not support replacement, silent overwrite, parent
creation, database persistence, remote/UNC paths, symlinks/reparse points, or
cross-volume movement. Repeated execution against the same destination fails
without mutation.

## 12. Failure precedence and exit codes

Observed precedence follows the single sequence:

1. invalid application request, nested input/configuration, destination policy,
   or initially cancelled token before work;
2. preparation or deterministic artifact failure;
3. execution-request construction failure;
4. operational failure, timeout, cancellation, or lower cleanup failure;
5. serialization failure;
6. exact `completed_candidate_integrity_failed`, emitted only by the step-15
   helper after successful serialization and before exporter invocation;
7. destination race or native publication failure;
8. application-owned descriptor/temporary cleanup failure overriding the
   provisional pre-publication export failure.

No export is attempted for an operational failure, so operational and export
failures cannot coexist. Destination validity/existence is checked before lower
work and rechecked by the no-replace publisher for races. Successful
serialization followed by publication failure retains no public payload and
leaves the destination unchanged/absent. No fallible result construction or
cleanup occurs after successful publication.

The internal source is never selected by elimination and never overrides an
already observable failure: earlier failure suppresses its owning helper, and
its failure suppresses the exporter. Export cleanup therefore cannot coexist
with it. An internal application result after successful publication is
prohibited and rejected by reconstruction.

`EditorApplicationExitCodeV1(IntEnum)` is the single authority used by the
result and future CLI:

| Value | Meaning |
|---:|---|
| 0 | completed and exported |
| 2 | invalid request/configuration/input/destination or destination exists |
| 3 | preparation, artifact, request-authority, or operational failure |
| 4 | lower timeout |
| 5 | cancellation |
| 6 | serialization or export failure |
| 7 | cleanup, the one enumerated internal application failure, or future CLI projection of the fixed coordinator error |

The application library returns the enum and never calls `sys.exit`.
Exact lower projection is: cancelled operational status -> 5;
`TIMEOUT_EXHAUSTED` -> 4; `cleanup_failed=True` -> 7; every other reconstructed
operational failure -> 3. The application failure code remains
`operational_execution_failed` for these lower-owned outcomes and never parses
the lower safe message.

## 13. Cardinality

| Path | prepare | artifacts | request authority | execute | serialize | temp writes | publications |
|---|---:|---:|---:|---:|---:|---:|---:|
| completed | 1 | 1 each | 1 | 1 | 1 | 1 | 1 |
| invalid/cancelled input or destination | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| preparation failed | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| artifact failed | 1 | through failing stage only | 0 | 0 | 0 | 0 | 0 |
| request authority failed | 1 | 1 each | 1 | 0 | 0 | 0 | 0 |
| execution failed/cancelled | 1 | 1 each | 1 | 1 | 0 | 0 | 0 |
| serialization failed | 1 | 1 each | 1 | 1 | 1 | 0 | 0 |
| write/publication failed | 1 | 1 each | 1 | 1 | 1 | 1 | 0 |

There is zero application retry, provider fallback, routing, polling, output
repair, or duplicate cleanup.

## 14. Future `editor-run` CLI

After all implementation revisions are verified, add exactly:

```text
pastila-scout editor-run \
  --input INPUT \
  --selection-profile PROFILE \
  --episode-context CONTEXT \
  --generation-config CONFIG \
  --provider {openai,ollama} \
  --model MODEL \
  --timeout-seconds TIMEOUT \
  --cancelled {false,true} \
  --output OUTPUT \
  --overwrite-policy fail_if_exists
```

Every argument is required. Provider, model and timeout must exactly equal the
generation configuration file; they are explicit confirmation rather than a
second semantic owner, and conflicting authority is exit 2. Other generation
options and timeout come only from the file—there are no hidden CLI defaults.
The CLI exposes no direct `--temperature` or `--top-p` option and performs no
numeric conversion for either field. It passes the value returned by the
strict generation-configuration file authority unchanged. Text-to-float CLI
parsing is therefore not a second Phase 4.3 numeric boundary; a future command
may add such an option only through a separately specified contract revision.
`--cancelled` maps exact lowercase text to one frozen token and permits a
deterministic pre-cancelled request; it is not a mutable signal. The CLI injects
one aware UTC `requested_at` and one deterministic-format operation reference
through command-time clock/reference authorities. It never calculates
fingerprints.

The output file is the sole canonical artifact. On success stdout is exactly:

```text
Editor application completed.
```

On failure stdout is empty and stderr contains only the fixed application safe
message plus LF. No draft, path, provider message, exception, or traceback is
printed. There is no quiet or machine-readable stdout mode in V1.

Import, parser construction, `--help`, `--version`, and parse failure perform
zero file read/write, environment or credential access, provider selection,
networking, runtime composition, request-authority calls, database
access, threads, subprocesses, timers, logging side effects, or editorial
execution. Parse failure uses argparse's existing behavior and exit 2.

## 15. Cleanup, persistence, and Producer prohibition

- Runtime session/client cleanup remains exclusively below Revision 3D.
- The application coordinator never calls lower close/cleanup.
- The atomic publisher owns its descriptor, file handle and temporary file.
- The CLI owns only argument/file-authority construction and standard streams.
- No database, queue, history, cache, automatic report registration or other
  persistence is introduced; output is caller-owned filesystem publication.
- No Producer contract, mapping, call, validation, persistence, or automatic
  handoff exists. `handoff_permitted` is only a safe completed-result fact for
  a later separately specified boundary.

## 16. Public package and protocols

After prerequisites are verified, the proposed exact package is:

```text
src/pastila_scout/editor_application_v1/
    __init__.py
    application.py
    configuration.py
    errors.py
    export.py
    models.py
    protocols.py
    serialization.py
```

Exact ordered public API:

```python
__all__ = (
    "EditorApplicationConfigurationError",
    "EditorApplicationCoordinatorError",
    "EditorApplicationCoordinatorV1",
    "EditorApplicationExitCodeV1",
    "EditorApplicationExportError",
    "EditorApplicationFailureCodeV1",
    "EditorApplicationFailureV1",
    "EditorApplicationGenerationConfigurationV1",
    "EditorApplicationGenerationConfigurationAuthorityV1",
    "EditorApplicationLifecycleStateV1",
    "EditorApplicationRequestV1",
    "EditorApplicationResultV1",
    "EditorApplicationSerializationError",
    "EditorApplicationStatusV1",
    "EditorAtomicExporterV1",
    "EditorEpisodeContextAuthorityV1",
    "EditorOperationalResultSerializerV1",
    "EditorSerializedOperationalResultV1",
    "EditorOutputDestinationV1",
    "EditorOverwritePolicyV1",
    "EditorSelectionProfileAuthorityV1",
)
```

The tuple contains exactly 21 symbols. Revision 3A inserts
`EditorSerializedOperationalResultV1` immediately after
`EditorOperationalResultSerializerV1`; every Revision 2--4 symbol retains its
relative order and identity.

No lower provider/runtime type, factory, protocol, builder, client, serializer
helper, path helper, or composition helper is exported. The execution-request
authority prerequisite remains in its own public package.

Package-private protocols define preparation `prepare`, artifact `build`,
execution-request `construct`, operational `execute`, serializer `serialize`,
and publisher `publish`. The exact application-facing protocol signatures are:

```python
class _EditorPreparationDependencyV1(Protocol):
    def prepare(
        self, *, scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1: ...

class _EditorArtifactDependencyV1(Protocol):
    def build(
        self, *, plan: EditorGenerationPlanV1,
    ) -> _EditorDeterministicArtifactsV1: ...

class _EditorExecutionRequestAuthorityDependencyV1(Protocol):
    def construct(
        self, *, preparation: EditorOperationalPreparationResultV1,
        plan: EditorGenerationPlanV1,
        flow_result: FlowOptimizationResult,
        editorial_blueprint: EditorialBlueprint,
        commentary_blueprint: EpisodeCommentaryBlueprint,
        voice_plan: EpisodeVoicePlan,
        generation_configuration: LanguageGenerationConfig,
        runtime_options: EditorGenerationRuntimeOptionsV1,
        provider: ProviderChoiceV1, requested_at: datetime,
        request_reference: str, cancellation: CancellationTokenV2,
    ) -> EditorGenerationExecutionRequestV1: ...

class _EditorOperationalExecutionDependencyV1(Protocol):
    def execute(
        self, *, request: EditorGenerationExecutionRequestV1,
    ) -> EditorOperationalResultV1: ...

class _EditorSerializerDependencyV1(Protocol):
    def serialize(
        self, *, result: EditorOperationalResultV1,
    ) -> EditorSerializedOperationalResultV1: ...

class _EditorExporterDependencyV1(Protocol):
    def publish(
        self, *, payload: bytes, destination: EditorOutputDestinationV1,
    ) -> Path: ...
```

`_EditorDeterministicArtifactsV1` is package-private, frozen and slotted, with
exact fields `flow_result`, `editorial_blueprint`, `commentary_blueprint`, and
`voice_plan`; its constructor public-copy/strictly reconstructs each value and
validates plan lineage/order. The artifact dependency adapts the existing
builders in their frozen order and calls each once.

Constructor validation uses `inspect.getattr_static`, exact `FunctionType`,
`inspect.signature(..., follow_wrapped=False)`, and resolved type hints. It
rejects properties, cached properties, static/class methods, partials,
`__signature__`, `__wrapped__`, dynamic attribute classes, instance method
replacement, subclasses, copied-invalid dependencies and post-construction
substitution without invoking a descriptor, body, repr or equality hook.
Coordinator copy/deepcopy reconstructs dependency identity without traversal;
pickle is rejected before dependency traversal.

## 17. Error and traceback isolation

Public errors are fieldless and exact:

```text
EditorApplicationConfigurationError:
    Editor application configuration is invalid.
EditorApplicationCoordinatorError:
    Editor application coordinator failed.
EditorApplicationSerializationError:
    Editor operational result serialization failed.
EditorApplicationExportError:
    Editor output export failed.
```

Public result failure messages are section 9 constants. Translation must:

```text
authority-bearing work
  -> exact owned exception catch
  -> neutral built-in status
  -> clear request/content/path/dependency/exception locals
  -> leave protected frame
  -> construct safe public failure/error
```

The coordinator catches exact
`EditorGenerationExecutionRequestAuthorityError` only around the single
authority call, reduces it to `execution_request_construction_failed`, clears
the exception/request/artifact locals, and performs no retry, message
inspection, operational call, serialization, or filesystem action.

Raised errors have `__cause__ is None`, `__context__ is None`, and
`__suppress_context__ is True`. Recursive traceback/container/closure scans
must retain no Scout input, profile, context, generation configuration,
preparation/result/draft/serialized bytes, destination/temporary path, handle,
coordinator, serializer, publisher, runtime authority, credential or raw
exception. No broad catch may classify multiple ownership boundaries.

Unexpected unenumerated package programming defects are never converted to
`internal_application_failure`. The protected operation first clears all
content, path, dependency, lower-result and exception-bearing locals at its
owning boundary, then a package-private neutral signal causes the outer public
boundary to raise exact `EditorApplicationCoordinatorError` from `None` with
`__cause__ is None`, `__context__ is None`, and
`__suppress_context__ is True`. No `EditorApplicationResultV1` or library exit
code is fabricated. The future CLI catches only this exact public error outside
the protected execution frame, writes its fixed safe message, and returns exit
7 without inventing an application result.

It is normatively prohibited to use `except Exception` to return
`internal_application_failure` around coordinator execution, injected
dependencies, preparation, artifact builders, request authority, operational
execution, serializer, exporter or cleanup. Those boundaries catch only their
owned documented errors for their existing finite category. Arbitrary injected
or lower programming exceptions are reduced without content retention to
`EditorApplicationCoordinatorError`, not an application result. No broad catch
is permitted for internal-result mapping; the section 9.1 helper emits only its
explicit private invariant error.

## 18. Determinism and passivity

All timestamps/references are injected. Fingerprints/checksums are deterministic
over their stated semantics. No current clock, UUID, PID, random operation
identity, locale, environment, filesystem ordering, or provider value enters
semantic output. Randomness is permitted only in a private temporary filename,
which never enters results or serialized bytes.

Fresh import and valid/invalid construction perform zero file reads/writes,
provider selection, credential access, networking, runtime/session composition,
preparation, generation, serialization, publication, cleanup, database work,
threads, subprocesses, timers, stdout/stderr, logging, or warnings.

## 19. Implementation test matrix

Each revision must test, offline:

1. exact layout/exports and passive import/construction/help;
2. strict profile/context/config files, duplicates, extra/missing/coerced fields,
   Unicode, copied-invalid state, cross-lineage and identity; generation
   configuration tests include valid exact floats `temperature=0.0`, `1.0`,
   and `2.0` with `top_p=1.0`; reject integer `temperature` values `0` and `1`,
   integer `top_p` values `0` and `1`, Boolean/string/decimal-like inputs,
   `NaN`, both infinities, temperatures below `0.0` or above `2.0`, and every
   `top_p` other than exact float `1.0` (including `0.0`, `0.5`, values above
   `1.0`, and nonfinite values); JSON integer tokens such as
   `{"temperature":1,"top_p":1}` are rejected while corresponding `1.0`
   tokens are accepted; the future CLI is tested to expose no direct numeric
   option or conversion and to pass the file-authority floats unchanged;
   materialization proves exact-float/equality parity in both lower objects and
   a verified request-authority call succeeds;
3. request reconstruction, nested substitution, cancellation, destination and
   overwrite policy, safe repr/copy/deepcopy/pickle;
4. exact dependency identities/signatures and zero-body static validation,
   including descriptors, wrappers, partials, forged signatures, dynamic
   attributes, copied-invalid and post-construction replacement; every malformed
   or substituted dependency raises fixed `EditorApplicationConfigurationError`
   before execution and produces no application result, lifecycle or exit code;
5. exact request-authority identity, exact twelve-argument mapping, one call
   after valid preparation, zero before, no fingerprint input/recalculation,
   fixed authority-failure mapping and zero execution/serialization/export;
   invalid or copied-invalid generation numerics additionally prove zero
   preparation, artifact, authority, execution, serialization, temporary-write
   and publication calls;
6. exact order/cardinality: one preparation, each artifact once, one request
   authority, one execution, one serialization and one publication, with zero
   application retry and no direct lower calls;
7. successful OpenAI/Ollama-equivalent results, deterministic envelope bytes,
   checksum parity and output reconstruction;
8. every configuration/preparation/artifact/request-authority/operational
   failure, timeout and cancellation with exact downstream suppression;
9. serialization failure with zero destination mutation;
10. existing file/directory, missing parent, device/UNC path, permission, disk
   full, short write, long/Unicode path, symlink/junction/reparse point,
   temporary collision, rename/link race and failure;
11. Windows `MoveFileExW`, Linux `renameat2` and macOS `renamex_np` no-replace
    atomic publication, unsupported-platform failure, unchanged/absent target,
    one close/unlink, and cleanup precedence;
12. exact exit codes/stdout/stderr, CLI validation before provider composition,
    passive help and legacy command regression;
13. recursive traceback isolation for every input, dependency, request authority,
    operational result, serialization,
    write, publication and nested cleanup failure;
14. the actual `_reconstruct_completed_application_candidate` operation emits
    the sole `completed_candidate_integrity_failed` source only for its explicit
    private invariant error, with exact lifecycle, reconstructed operational
    result, no public payload/checksum/path, no temporary file or destination
    mutation, handoff/retry false, exit 7, fixed message, later-stage suppression
    and recursive isolation; tests may not monkeypatch a returned status;
15. arbitrary injected/lower exceptions and an unenumerated package defect
    produce fixed `EditorApplicationCoordinatorError`, never an internal result;
    no catch-all internal handler exists, fabricated internal combinations are
    rejected, and successful publication cannot coexist with internal failure;
16. zero Producer/database/GUI/fallback/discovery/retry/duplicate cleanup; and
17. frozen hashes/exports, full offline suite and all static gates.

## 20. Revision roadmap

The single historical and dependency order is:

```text
Revision 1 -> Revision 2 -> Revision 3 -> Revision 4 -> Revision 3A
-> Revision 5 -> Revision 6
```

`3A` denotes corrective ownership of the Revision 3 serialization boundary;
it does not denote chronology before Revision 4. Revision 3A requires the
verified Revision 4 baseline. Revision 5 requires the independently verified
Revision 3A milestone and does not depend directly on the superseded Revision 3
serializer contract. The graph is acyclic.

Before Revision 3A freeze, its focused matrix must materially cover exact API
and serializer signature; valid wrapper and exact field order; final payload
bytes; embedded/public/placeholder-preimage checksum parity; proof that the
final payload is not the checksum preimage; prefix and lowercase hexadecimal
shape; NFC keys/values; datetime, numeric and sequence projection; UTF-8 without
BOM; exactly one LF; canonical re-encoding; invalid UTF-8, BOM, CRLF,
missing/double LF and trailing data; malformed/nonobject/duplicate-key JSON;
wrong schema or schema version; missing/extra checksum field; invalid checksum
shape; embedded/public and recomputed mismatch; copied-invalid payload and
checksum; subclass rejection; copy/deepcopy; pickle rejection before traversal;
safe repr/equality; recursive traceback isolation; passive import/construction;
cross-process determinism; exactly two nominal SHA-256 calculations comprising
one serializer production calculation and one mandatory public-constructor
validation calculation; exactly one validation calculation for every later
wrapper reconstruction; prohibition of trusted constructor bypass; coordinator
prohibition from parsing or recalculating; unchanged checksum-blind exporter
behavior; exact API migration; and frozen/Git-scope integrity.

### Closed prerequisite

`EditorGenerationExecutionRequestAuthorityV1` is independently verified at
`phase-4.2-editor-generation-execution-request-authority-r2-verified`. No
Phase 4.3 revision may reopen or duplicate its fingerprint ownership.

### Revision 1 — specification revision and freeze

Authorize only this document. Exit requires implementation-ready independent
review, exact authority integration, Windows native-publication closure and
static gates. Rollback restores/removes only this untracked specification.

### Revision 2 — configuration and immutable contracts

Add only `configuration.py`, `models.py`, `errors.py`, minimal `__init__.py`,
and `tests/test_editor_application_contracts_v1.py`. Implement the three configuration authorities,
destination/overwrite policy, application request/result/failure/lifecycle and
exit contracts. `errors.py` defines all four already-fixed fieldless errors,
including inert `EditorApplicationCoordinatorError`, so Revision 5 needs no
retroactive error-file change. No execution, serializer, filesystem, CLI or
Producer.

### Revision 3 — canonical serialization authority

Add only `serialization.py`,
`tests/test_editor_application_serialization_v1.py`, and its normative additive
`__init__.py` exports. No filesystem or execution.
Verify byte/reconstruction/checksum determinism, then freeze.

### Revision 4 — atomic export authority

Add only `export.py`, `tests/test_editor_application_export_v1.py`, and its
normative additive `__init__.py` exports. Keep package-private native adapters
in `export.py`. No application execution or CLI. Verify
fail-if-exists races, unsupported platforms and cleanup, then freeze.

### Revision 3A — corrective serialized-result public authority

Revision 3A names serializer ownership but is chronologically implemented
after Revision 4. From the verified Revision 4 baseline, perform one controlled
superseding serialization revision before Revision 5. Modify only
`src/pastila_scout/editor_application_v1/serialization.py`,
`src/pastila_scout/editor_application_v1/__init__.py`, and
`tests/test_editor_application_serialization_v1.py`. Implement
`EditorSerializedOperationalResultV1`, change the sole `serialize` return type
from `bytes` to that contract, migrate all serializer-focused expectations and
freeze a new Revision 3A milestone. Raw-byte return compatibility is
intentionally removed; all callers use `.payload`. No compatibility method,
adapter, alias or second encoding path remains.

Because Revision 3A follows the verified Revision 4 milestone, the following
frozen tests require separately authorized, assertion-only maintenance where
their exact API/scope checks encode the earlier return type or public tuple:
`tests/test_editor_application_contracts_v1.py`,
`tests/test_editor_application_serialization_v1.py`, and
`tests/test_editor_application_export_v1.py`. Such maintenance may permit only
the exact new symbol, return annotation and bounded Revision 3A paths; it may
not weaken ordering, identity, frozen production or Git-scope ownership.

### Revision 5 — application coordinator

Add only `protocols.py`, `application.py`,
`tests/test_editor_application_v1.py`, and the remaining exact final
`__init__.py` exports. Keep private adapters/composition helpers in those two
modules. Compose frozen coordinators and the verified request authority
once; no CLI/Producer/database. Freeze only after independent argument mapping,
cardinality, traceback and frozen-integrity verification. Revision 5 requires
the independently verified Revision 3A milestone and consumes only the wrapper
fields; it performs no checksum or envelope work.

### Revision 6 — opt-in CLI

Add only `src/pastila_scout/editor_cli_run_v1/{__init__.py,command.py,
composition.py}`, modify only `src/pastila_scout/cli.py` for registration, and
add `tests/test_editor_cli_run_v1.py`. Preserve existing commands/help. No
Producer/database.

Later revisions may extend `editor_application_v1.__all__` only by the exact
ordered symbols already fixed in section 16. They never rename, reorder or
change earlier symbols or behavior; each revision explicitly authorizes that
single additive facade edit.

Every revision requires an exact clean baseline, scoped authorized paths,
focused/full offline tests, Ruff, Black, compileall, pip check,
`git diff --check`, independent verification, separate commit/tag authority,
and rollback by removing only its additive scope.

## 21. Contradiction scan and unresolved decisions

The document defines one application coordinator, one authority per
configuration class, one serializer, one atomic publisher, one fail-if-exists
policy, one failure/exit table, one sequence and one cleanup owner per resource.
It adds no Producer/database work and duplicates no lower retry or cleanup.

Search terms reviewed: `EditorApplication`, `SelectionProfile`,
`EpisodeContext`, `GenerationConfiguration`, `EditorOperationalResultV1`,
`serialize`, `serialization`, `atomic`, `export`, `overwrite`, `destination`,
`temporary`, `editor-run`, `exit code`, `Producer`, `persistence`, `cleanup`,
`retry`, `provider`, `runtime session`, `CLI`, `stdout`, and `stderr`.

The verified aggregate authority is integrated exactly once. Application code
owns no aggregate fingerprint calculation or validation. Configuration,
execution order, result/failure closure, cancellation, serializer, native
no-replace publication, overwrite, CLI, streams, protocols, object safety,
cleanup and revision ownership are singular and finite. There are no unresolved
load-bearing decisions or missing public prerequisites.

## 22. Findings by severity

Critical: none.

Major: none.

Minor: none left open.
