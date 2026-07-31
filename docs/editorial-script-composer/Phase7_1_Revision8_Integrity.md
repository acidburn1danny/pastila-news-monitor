# Module 2.9 Phase 7.1 Revision 8 Integrity Manifest

**Baseline status: FROZEN**  
**Manifest algorithm: SHA-256**  
**Frozen production file count: 15**

## Frozen production file hashes

| Relative path | SHA-256 |
|---|---|
| `src/pastila_scout/provider_adapters_v2/__init__.py` | `72e72966daf74c7e0285992932de907a545baafb07eadd01e7220062f9eb9785` |
| `src/pastila_scout/provider_adapters_v2/base.py` | `47668eca30b0e4a224973650230e5248764a4977e23e1f5249eaaac1a5e12167` |
| `src/pastila_scout/provider_adapters_v2/claude.py` | `c730b330c3000992bd58b03692e21ba06b7f2bc7534b789ddf2d621888c655a7` |
| `src/pastila_scout/provider_adapters_v2/gemini.py` | `fb2f326e8b8e4dc3d53c3025751b77177a69876beb1a315e19ccc20df468df3b` |
| `src/pastila_scout/provider_adapters_v2/ollama.py` | `6deb7799a2c32d3748bddadd017aa3ca33db01ffb97e1a3ca87ddd2875b0e8b0` |
| `src/pastila_scout/provider_adapters_v2/openai.py` | `1f4736f29ca39eca25e9d78be3bd644240c4212f7c1a7a0a39e1569d9d957f06` |
| `src/pastila_scout/provider_composition_v2.py` | `d3ab18e2ebc9c0db6657b0bbf1ab408a98952a5668ea70a89975f06b1b180c61` |
| `src/pastila_scout/provider_v2/__init__.py` | `385f224ce9d2cea3ad1cf2affe44cb8733ad6b434c5fbf5b4cee53a2ce7edd8e` |
| `src/pastila_scout/provider_v2/authority.py` | `01585407c95a6a704ab6e912c3deeff9743f8e94282209b5c59192ebfb2f76f1` |
| `src/pastila_scout/provider_v2/canonical.py` | `8f11e4fde41f87b76037fb340e79558aca19a9ee0a38ad2b99dbe8c990605d01` |
| `src/pastila_scout/provider_v2/errors.py` | `db3ba553037f54e808b18cb958765f9cd7bff0c68929d87a8fab31bd0fd1e286` |
| `src/pastila_scout/provider_v2/identity.py` | `96675d2bbe3a9d4de70e18dbb2a46e21edacd0e40ec93376e8d521da7efb72e7` |
| `src/pastila_scout/provider_v2/interface.py` | `4e66fdcf6298f86aa8b5bd2c6bbbb52cdb70b40e02f3ab586ed00d46a4a212da` |
| `src/pastila_scout/provider_v2/models.py` | `5b9958c3f54c5008f9e22c0308eed013e72adb59d1d11eecf302f5542e9acd9e` |
| `src/pastila_scout/provider_v2/registry.py` | `e12efaf1ba60ab2ef65734e48fb4bea62c00c926bae86cf93ff6008e9c8efa68` |

## Public API snapshot

`pastila_scout.provider_v2.__all__` contains exactly these 42 symbols, in frozen
order:

1. `DuplicateProviderRegistrationError`
2. `InvalidProviderAdapterError`
3. `InvalidProviderDescriptorError`
4. `InvalidProviderIdentifierError`
5. `ProviderAdapter`
6. `ProviderCapabilityUnavailableError`
7. `ProviderCapabilityV2`
8. `ProviderDescriptorV2`
9. `ProviderFinishReasonV2`
10. `ProviderMessageInputV2`
11. `ProviderOutputInputV2`
12. `ProviderRegistry`
13. `ProviderRequestEnvelopeV2`
14. `ProviderRequestIntentV2`
15. `ProviderRequestMessageV2`
16. `ProviderRequestUnitInputV2`
17. `ProviderRequestUnitV2`
18. `ProviderResultEnvelopeV2`
19. `ProviderResultProjectionV2`
20. `ProviderResultStatusV2`
21. `ProviderResultUnitV2`
22. `ProviderV2ValidationError`
23. `ProviderV2ValidationIssue`
24. `UnknownProviderError`
25. `build_provider_descriptor`
26. `build_provider_request_envelope`
27. `build_provider_result_envelope`
28. `descriptor_fingerprint`
29. `descriptor_identity`
30. `request_envelope_fingerprint`
31. `request_envelope_identity`
32. `request_message_fingerprint`
33. `request_message_identity`
34. `request_unit_fingerprint`
35. `request_unit_identity`
36. `result_envelope_fingerprint`
37. `result_envelope_identity`
38. `result_unit_fingerprint`
39. `result_unit_identity`
40. `validate_provider_descriptor`
41. `validate_provider_request_envelope`
42. `validate_provider_result_envelope`

Adapter-package exports:

```python
()
```

Composition exports:

```python
("build_provider_registry",)
```

## Default provider snapshot

```text
claude
gemini
ollama
openai
```

## Frozen OpenAI V1 callable identity snapshot

The following eight V2 adapter bindings were verified as the exact frozen V1
callable objects:

1. `v1_request_builder` → `build_draft_provider_request_plan`
2. `v1_request_validator` → `validate_draft_provider_request_plan`
3. `v1_extracted_result_builder` → `build_openai_extracted_execution_result`
4. `v1_extracted_result_validator` → `validate_openai_extracted_execution_result`
5. `v1_concrete_result_builder` → `build_openai_provider_execution_result`
6. `v1_concrete_result_validator` → `validate_openai_provider_execution_result`
7. `v1_generic_result_builder` → `build_provider_execution_result`
8. `v1_generic_result_validator` → `validate_provider_execution_result`

Identity verification result: **8/8 preserved**.

## Quality-gate snapshot

| Gate | Result |
|---|---|
| Focused Phase 7.1 | 116 passed |
| Complete Module 2.9 | 2,544 passed; 1,777 deselected |
| Complete repository | 4,321 passed |
| Clean-process import probes | 8 passed; 108 deselected |
| Ruff | All checks passed |
| Black check | 530 files unchanged |
| compileall | Exit code 0 |
| pip check | No broken requirements |

No failures, skips, xfails, warnings, or collection anomalies were recorded in
the frozen verification baseline.
