"""Provider-neutral lower request construction for Editor generation."""

import unicodedata
from dataclasses import dataclass
from typing import NoReturn, Self

from pastila_scout.application_request_authority_v1 import (
    ApplicationProviderRequestV1,
    ApplicationRequestAuthorityV1,
)
from pastila_scout.provider_execution_v2 import ProviderExecutionRequestV2

from .errors import EditorGenerationAuthorityError
from .models import (
    EditorGenerationApplicationRequestV1,
    EditorGenerationRuntimeAuthorityV1,
    reconstruct_application_request,
    reconstruct_runtime_authority,
)


def _raise_invalid() -> NoReturn:
    error = EditorGenerationAuthorityError("Editor generation authority is invalid.")
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True)
class EditorGenerationRequestAuthorityV1:
    """Build one lower request without selecting or executing a provider."""

    def build(
        self,
        request: EditorGenerationApplicationRequestV1,
        runtime_authority: EditorGenerationRuntimeAuthorityV1,
    ) -> ProviderExecutionRequestV2:
        try:
            source = reconstruct_application_request(request)
            runtime = reconstruct_runtime_authority(runtime_authority)
            if (
                source.options != runtime.options
                or source.provider is not runtime.options.provider
            ):
                _raise_invalid()
            lower = ApplicationRequestAuthorityV1().build(
                ApplicationProviderRequestV1(
                    source.provider,
                    source.prompt,
                    f"editor-generation-v1:{source.request_fingerprint}",
                    source.requested_at,
                    source.options.timeout_policy,
                    source.cancellation,
                )
            )
            lower = lower.model_copy(
                update={
                    "context": lower.context.model_copy(
                        update={
                            "metadata": (
                                (
                                    "output_schema_canonical_json",
                                    source.output_schema_canonical_json,
                                ),
                                (
                                    "output_schema_fingerprint",
                                    source.output_schema_fingerprint,
                                ),
                            )
                        }
                    )
                }
            )
            rebuilt = ProviderExecutionRequestV2.model_validate(
                lower.model_dump(mode="python", warnings=False), strict=True
            )
            message = rebuilt.request_intent.request_units[0].messages[0]
            if message.role != "generation" or message.content != unicodedata.normalize(
                "NFC", source.prompt
            ):
                _raise_invalid()
            return rebuilt
        except EditorGenerationAuthorityError:
            raise
        except Exception:  # noqa: BLE001 - lower frozen authority is isolated
            _raise_invalid()

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorGenerationRequestAuthorityV1 does not support pickle")

    def __repr__(self) -> str:
        return "EditorGenerationRequestAuthorityV1()"


__all__ = ("EditorGenerationRequestAuthorityV1",)
