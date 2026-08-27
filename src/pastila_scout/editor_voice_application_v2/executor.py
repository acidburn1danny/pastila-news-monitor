"""Voice execution port and the explicit no-model implementation."""

from typing import Protocol, runtime_checkable

from pastila_scout.editor_voice_application_v2.models import (
    VoiceExecutorAvailabilityV1,
    VoiceExecutorCapabilityV1,
    VoiceExecutorRequestV1,
    VoiceUnavailableExecutionResultV1,
)


@runtime_checkable
class VoiceExecutorPortV1(Protocol):
    def inspect_capability(self) -> VoiceExecutorCapabilityV1: ...

    def execute(
        self, request: VoiceExecutorRequestV1
    ) -> VoiceUnavailableExecutionResultV1: ...


class UnavailableVoiceExecutorV1:
    """No-parent binding: returns unavailable without touching any runtime."""

    _IDENTITY = "pastila-voice-executor:unbound:v1"
    _REASON = "no_viable_voice_parent_selected"

    def inspect_capability(self) -> VoiceExecutorCapabilityV1:
        return VoiceExecutorCapabilityV1(
            executor_identity=self._IDENTITY,
            availability=VoiceExecutorAvailabilityV1.UNAVAILABLE,
            safe_reason=self._REASON,
        )

    def execute(
        self, request: VoiceExecutorRequestV1
    ) -> VoiceUnavailableExecutionResultV1:
        del request
        return VoiceUnavailableExecutionResultV1(
            executor_identity=self._IDENTITY,
            safe_reason=self._REASON,
        )


__all__ = ["UnavailableVoiceExecutorV1", "VoiceExecutorPortV1"]
