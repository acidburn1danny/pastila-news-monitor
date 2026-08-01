# Module 2.9 Phase 7.3 Integrity Manifest

Manifest algorithm: SHA-256 over exact file bytes.

## Git references

- Commit: `d47d69b0fb9ce6f4c6a7539808ccd4debfc819cd`
- Tag: `module-2.9-phase-7.3-r6-verified`
- Parent verified tag: `module-2.9-phase-7.3-r2-verified`
- Parent verified commit: `4c2e38bc8f2260494ca51a5e6c5405e5921ec1a7`

## Frozen production files

Paths are sorted lexicographically.

| Relative path | SHA-256 | Bytes |
|---|---|---:|
| `src/pastila_scout/provider_execution_openai_sdk_v2/__init__.py` | `2e9dfe46cc32258336741fc63ab282e52dcb429c6f6991367e373549808e2f05` | 780 |
| `src/pastila_scout/provider_execution_openai_sdk_v2/client.py` | `f42b5b30366a30755c4bba4a1bb9cd66e954cd63577d08f8053eae03ddaec889` | 12483 |
| `src/pastila_scout/provider_execution_openai_sdk_v2/errors.py` | `2b097697c5964fdab7ca30254186ad83658c241b6829ddfb46af49ae67f9dcea` | 981 |
| `src/pastila_scout/provider_execution_openai_sdk_v2/mapping.py` | `a022a7c082ff2ea9025bcc437d2ac1412782736c38e95c59674a670bd910b510` | 3872 |
| `src/pastila_scout/provider_execution_openai_sdk_v2/models.py` | `af7a43b75215b0de3b3d30f530c3b2e9874789acea0b0bf128726f10ea87d8d4` | 4439 |

Frozen production file count: **5**.

## Supporting artifacts

These files support the freeze but are not classified as frozen production files.

| Relative path | SHA-256 | Bytes |
|---|---|---:|
| `docs/editorial-script-composer/Phase7_3_OpenAISDKBoundary.md` | `17917e5a4efdddbe91a42912c5d24f5d72a9b4e34b97f41bd1d371a4f64992b9` | 7835 |
| `tests/test_provider_execution_openai_sdk_v2.py` | `0ca8bbe7fca6b79ba9fd053520a3cee29722d937441dc1dd306869d887d1b88d` | 32744 |

Supporting artifact count: **2**.

## Public API snapshots

### `pastila_scout.provider_v2` (42)

```python
(
    "DuplicateProviderRegistrationError", "InvalidProviderAdapterError",
    "InvalidProviderDescriptorError", "InvalidProviderIdentifierError",
    "ProviderAdapter", "ProviderCapabilityUnavailableError",
    "ProviderCapabilityV2", "ProviderDescriptorV2", "ProviderFinishReasonV2",
    "ProviderMessageInputV2", "ProviderOutputInputV2", "ProviderRegistry",
    "ProviderRequestEnvelopeV2", "ProviderRequestIntentV2",
    "ProviderRequestMessageV2", "ProviderRequestUnitInputV2",
    "ProviderRequestUnitV2", "ProviderResultEnvelopeV2",
    "ProviderResultProjectionV2", "ProviderResultStatusV2",
    "ProviderResultUnitV2", "ProviderV2ValidationError",
    "ProviderV2ValidationIssue", "UnknownProviderError",
    "build_provider_descriptor", "build_provider_request_envelope",
    "build_provider_result_envelope", "descriptor_fingerprint",
    "descriptor_identity", "request_envelope_fingerprint",
    "request_envelope_identity", "request_message_fingerprint",
    "request_message_identity", "request_unit_fingerprint",
    "request_unit_identity", "result_envelope_fingerprint",
    "result_envelope_identity", "result_unit_fingerprint",
    "result_unit_identity", "validate_provider_descriptor",
    "validate_provider_request_envelope", "validate_provider_result_envelope",
)
```

### `pastila_scout.provider_execution_v2` (13)

```python
(
    "CancellationTokenV2", "ExecutionCancelledError",
    "ExecutionConfigurationError", "ExecutionContextV2", "ExecutionOutcomeV2",
    "ExecutionTimeoutError", "InternalExecutionError",
    "ProviderExecutionBoundaryError", "ProviderExecutionError",
    "ProviderExecutionRequestV2", "ProviderExecutionResultV2",
    "ProviderExecutorV2", "TimeoutPolicyV2",
)
```

### `pastila_scout.provider_execution_testing_v2` (2)

```python
("ExecutionScenarioV2", "FakeProviderExecutorV2")
```

### `pastila_scout.provider_execution_openai_v2` (15)

```python
(
    "OpenAIClientContractError", "OpenAIClientErrorCategoryV2",
    "OpenAIConfigurationError", "OpenAIExecutionBoundaryError",
    "OpenAIExecutionClientV2", "OpenAIExecutionConfigV2",
    "OpenAIExecutionMessageV2", "OpenAIExecutionOutputV2",
    "OpenAIExecutionRequestV2", "OpenAIExecutionResponseV2",
    "OpenAIProviderExecutorV2", "OpenAIRequestMappingError",
    "OpenAIResponseMappingError", "build_openai_execution_request",
    "project_openai_execution_response",
)
```

### `pastila_scout.provider_execution_openai_sdk_v2` (10)

```python
(
    "OpenAISDKBoundaryError", "OpenAISDKCapabilityV2", "OpenAISDKClientV2",
    "OpenAISDKConfigurationError", "OpenAISDKDependencyError",
    "OpenAISDKRequestV2", "OpenAISDKResponseError",
    "build_openai_sdk_request", "classify_openai_sdk_exception",
    "reconstruct_openai_sdk_response",
)
```

## Frozen OpenAI delegated identities

- `OpenAIProviderAdapter.v1_request_builder` is `build_draft_provider_request_plan`: True
- `OpenAIProviderAdapter.v1_request_validator` is `validate_draft_provider_request_plan`: True
- `OpenAIProviderAdapter.v1_extracted_result_builder` is `build_openai_extracted_execution_result`: True
- `OpenAIProviderAdapter.v1_extracted_result_validator` is `validate_openai_extracted_execution_result`: True
- `OpenAIProviderAdapter.v1_concrete_result_builder` is `build_openai_provider_execution_result`: True
- `OpenAIProviderAdapter.v1_concrete_result_validator` is `validate_openai_provider_execution_result`: True
- `OpenAIProviderAdapter.v1_generic_result_builder` is `build_provider_execution_result`: True
- `OpenAIProviderAdapter.v1_generic_result_validator` is `validate_provider_execution_result`: True

Identity result: **8/8 unchanged**.

## Deterministic local validation

From the repository root, use the project virtual environment to perform these
checks. Any assertion failure exits nonzero.

```powershell
git diff --exit-code module-2.9-phase-7.3-r6-verified -- `
  src/pastila_scout/provider_execution_openai_sdk_v2 `
  docs/editorial-script-composer/Phase7_3_OpenAISDKBoundary.md `
  tests/test_provider_execution_openai_sdk_v2.py

if ((git rev-parse module-2.9-phase-7.3-r6-verified) -ne `
    "d47d69b0fb9ce6f4c6a7539808ccd4debfc819cd") { exit 1 }

@'
import hashlib
from pathlib import Path

expected = {
    "src/pastila_scout/provider_execution_openai_sdk_v2/__init__.py": ("2e9dfe46cc32258336741fc63ab282e52dcb429c6f6991367e373549808e2f05", 780),
    "src/pastila_scout/provider_execution_openai_sdk_v2/client.py": ("f42b5b30366a30755c4bba4a1bb9cd66e954cd63577d08f8053eae03ddaec889", 12483),
    "src/pastila_scout/provider_execution_openai_sdk_v2/errors.py": ("2b097697c5964fdab7ca30254186ad83658c241b6829ddfb46af49ae67f9dcea", 981),
    "src/pastila_scout/provider_execution_openai_sdk_v2/mapping.py": ("a022a7c082ff2ea9025bcc437d2ac1412782736c38e95c59674a670bd910b510", 3872),
    "src/pastila_scout/provider_execution_openai_sdk_v2/models.py": ("af7a43b75215b0de3b3d30f530c3b2e9874789acea0b0bf128726f10ea87d8d4", 4439),
    "docs/editorial-script-composer/Phase7_3_OpenAISDKBoundary.md": ("17917e5a4efdddbe91a42912c5d24f5d72a9b4e34b97f41bd1d371a4f64992b9", 7835),
    "tests/test_provider_execution_openai_sdk_v2.py": ("0ca8bbe7fca6b79ba9fd053520a3cee29722d937441dc1dd306869d887d1b88d", 32744),
}
for path, (digest, size) in expected.items():
    content = Path(path).read_bytes()
    assert len(content) == size
    assert hashlib.sha256(content).hexdigest() == digest

import pastila_scout.provider_v2 as provider_v2
import pastila_scout.provider_execution_v2 as execution_v2
import pastila_scout.provider_execution_testing_v2 as testing_v2
import pastila_scout.provider_execution_openai_v2 as openai_v2
import pastila_scout.provider_execution_openai_sdk_v2 as sdk_v2

EXPECTED_PROVIDER_V2 = (
    "DuplicateProviderRegistrationError",
    "InvalidProviderAdapterError",
    "InvalidProviderDescriptorError",
    "InvalidProviderIdentifierError",
    "ProviderAdapter",
    "ProviderCapabilityUnavailableError",
    "ProviderCapabilityV2",
    "ProviderDescriptorV2",
    "ProviderFinishReasonV2",
    "ProviderMessageInputV2",
    "ProviderOutputInputV2",
    "ProviderRegistry",
    "ProviderRequestEnvelopeV2",
    "ProviderRequestIntentV2",
    "ProviderRequestMessageV2",
    "ProviderRequestUnitInputV2",
    "ProviderRequestUnitV2",
    "ProviderResultEnvelopeV2",
    "ProviderResultProjectionV2",
    "ProviderResultStatusV2",
    "ProviderResultUnitV2",
    "ProviderV2ValidationError",
    "ProviderV2ValidationIssue",
    "UnknownProviderError",
    "build_provider_descriptor",
    "build_provider_request_envelope",
    "build_provider_result_envelope",
    "descriptor_fingerprint",
    "descriptor_identity",
    "request_envelope_fingerprint",
    "request_envelope_identity",
    "request_message_fingerprint",
    "request_message_identity",
    "request_unit_fingerprint",
    "request_unit_identity",
    "result_envelope_fingerprint",
    "result_envelope_identity",
    "result_unit_fingerprint",
    "result_unit_identity",
    "validate_provider_descriptor",
    "validate_provider_request_envelope",
    "validate_provider_result_envelope",
)
EXPECTED_PROVIDER_EXECUTION_V2 = (
    "CancellationTokenV2",
    "ExecutionCancelledError",
    "ExecutionConfigurationError",
    "ExecutionContextV2",
    "ExecutionOutcomeV2",
    "ExecutionTimeoutError",
    "InternalExecutionError",
    "ProviderExecutionBoundaryError",
    "ProviderExecutionError",
    "ProviderExecutionRequestV2",
    "ProviderExecutionResultV2",
    "ProviderExecutorV2",
    "TimeoutPolicyV2",
)
EXPECTED_PROVIDER_EXECUTION_TESTING_V2 = (
    "ExecutionScenarioV2",
    "FakeProviderExecutorV2",
)
EXPECTED_PROVIDER_EXECUTION_OPENAI_V2 = (
    "OpenAIClientContractError",
    "OpenAIClientErrorCategoryV2",
    "OpenAIConfigurationError",
    "OpenAIExecutionBoundaryError",
    "OpenAIExecutionClientV2",
    "OpenAIExecutionConfigV2",
    "OpenAIExecutionMessageV2",
    "OpenAIExecutionOutputV2",
    "OpenAIExecutionRequestV2",
    "OpenAIExecutionResponseV2",
    "OpenAIProviderExecutorV2",
    "OpenAIRequestMappingError",
    "OpenAIResponseMappingError",
    "build_openai_execution_request",
    "project_openai_execution_response",
)
EXPECTED_PROVIDER_EXECUTION_OPENAI_SDK_V2 = (
    "OpenAISDKBoundaryError",
    "OpenAISDKCapabilityV2",
    "OpenAISDKClientV2",
    "OpenAISDKConfigurationError",
    "OpenAISDKDependencyError",
    "OpenAISDKRequestV2",
    "OpenAISDKResponseError",
    "build_openai_sdk_request",
    "classify_openai_sdk_exception",
    "reconstruct_openai_sdk_response",
)

assert provider_v2.__all__ == EXPECTED_PROVIDER_V2
assert execution_v2.__all__ == EXPECTED_PROVIDER_EXECUTION_V2
assert testing_v2.__all__ == EXPECTED_PROVIDER_EXECUTION_TESTING_V2
assert openai_v2.__all__ == EXPECTED_PROVIDER_EXECUTION_OPENAI_V2
assert sdk_v2.__all__ == EXPECTED_PROVIDER_EXECUTION_OPENAI_SDK_V2

from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.editor.script_composer.extracted_result_validation import build_openai_extracted_execution_result, validate_openai_extracted_execution_result
from pastila_scout.editor.script_composer.openai_result_validation import build_openai_provider_execution_result, validate_openai_provider_execution_result
from pastila_scout.editor.script_composer.provider_mapping_validation import build_draft_provider_request_plan, validate_draft_provider_request_plan
from pastila_scout.editor.script_composer.provider_result_validation import build_provider_execution_result, validate_provider_execution_result
adapter = OpenAIProviderAdapter()
actual = (adapter.v1_request_builder, adapter.v1_request_validator, adapter.v1_extracted_result_builder, adapter.v1_extracted_result_validator, adapter.v1_concrete_result_builder, adapter.v1_concrete_result_validator, adapter.v1_generic_result_builder, adapter.v1_generic_result_validator)
expected_identities = (build_draft_provider_request_plan, validate_draft_provider_request_plan, build_openai_extracted_execution_result, validate_openai_extracted_execution_result, build_openai_provider_execution_result, validate_openai_provider_execution_result, build_provider_execution_result, validate_provider_execution_result)
assert all(actual_value is expected_value for actual_value, expected_value in zip(actual, expected_identities, strict=True))
'@ | .\.venv\Scripts\python.exe -
```
