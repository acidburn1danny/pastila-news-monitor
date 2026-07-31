"""OpenAI V2 adapter with exact frozen V1 authority delegation."""

from pastila_scout.editor.script_composer.extracted_result_validation import (
    build_openai_extracted_execution_result,
    validate_openai_extracted_execution_result,
)
from pastila_scout.editor.script_composer.openai_result_validation import (
    build_openai_provider_execution_result,
    validate_openai_provider_execution_result,
)
from pastila_scout.editor.script_composer.provider_mapping_validation import (
    build_draft_provider_request_plan,
    validate_draft_provider_request_plan,
)
from pastila_scout.editor.script_composer.provider_result_validation import (
    build_provider_execution_result,
    validate_provider_execution_result,
)
from pastila_scout.provider_v2 import (
    ProviderCapabilityV2,
    build_provider_descriptor,
)

from .base import ProviderAdapterBase, adapter_identity


class OpenAIProviderAdapter(ProviderAdapterBase):
    """Reference adapter; transport remains outside Phase 7.1."""

    provider_id = "openai"
    adapter_identity = adapter_identity(provider_id)
    descriptor = build_provider_descriptor(
        provider_id=provider_id,
        display_name="OpenAI",
        capabilities=(
            ProviderCapabilityV2.METADATA,
            ProviderCapabilityV2.PROJECTION,
            ProviderCapabilityV2.REQUEST_CONSTRUCTION,
            ProviderCapabilityV2.RESPONSE_EXTRACTION,
            ProviderCapabilityV2.VALIDATION,
        ),
        descriptor_version="1.0.0",
        adapter_identity=adapter_identity,
    )

    v1_request_builder = staticmethod(build_draft_provider_request_plan)
    v1_request_validator = staticmethod(validate_draft_provider_request_plan)
    v1_extracted_result_builder = staticmethod(build_openai_extracted_execution_result)
    v1_extracted_result_validator = staticmethod(
        validate_openai_extracted_execution_result
    )
    v1_concrete_result_builder = staticmethod(build_openai_provider_execution_result)
    v1_concrete_result_validator = staticmethod(
        validate_openai_provider_execution_result
    )
    v1_generic_result_builder = staticmethod(build_provider_execution_result)
    v1_generic_result_validator = staticmethod(validate_provider_execution_result)


__all__ = ("OpenAIProviderAdapter",)
