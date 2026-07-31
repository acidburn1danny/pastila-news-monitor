"""Provider-neutral projection and runtime boundary for Controlled Generation."""

from typing import Protocol, runtime_checkable

from pastila_scout.editor.generation.models import ControlledGenerationResult
from pastila_scout.editor.qa.integration.models import ControlledGenerationInvocation

from .models import DraftRegenerationRequest

# Controlled Generation's existing public request contract is an invocation.
type ControlledGenerationRequest = ControlledGenerationInvocation


@runtime_checkable
class ControlledGenerationGateway(Protocol):
    """One explicitly injected generation boundary; provider details stay hidden."""

    def generate(
        self, request: ControlledGenerationRequest
    ) -> ControlledGenerationResult:
        """Generate once from an already prepared invocation."""

        ...


class ControlledGenerationRequestProjector:
    """Preserve the already-approved invocation; never invoke generation."""

    def project(self, request: DraftRegenerationRequest) -> ControlledGenerationRequest:
        invocation = request.regeneration_input.generation_invocation
        # Accessing the public fingerprint forces its canonical nested validation path.
        if not invocation.invocation_fingerprint.startswith("sha256:"):
            raise ValueError("Controlled Generation request fingerprint is invalid")
        return invocation
