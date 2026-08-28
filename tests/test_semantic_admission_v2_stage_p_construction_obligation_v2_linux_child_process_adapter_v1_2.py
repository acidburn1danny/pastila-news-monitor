from __future__ import annotations

import hashlib

from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_child_process_adapter_v1_2 as adapter


class _Context:
    def Queue(self, *args, **kwargs): return object()
    def Process(self, *, target, kwargs, daemon):
        self.target, self.kwargs, self.daemon = target, kwargs, daemon
        return object()


def test_context_rebinds_only_exact_legacy_target_without_launch():
    context = _Context()
    wrapped = adapter._ContextV1_2(context)
    result = wrapped.Process(
        target=adapter.legacy._run_linux_generation_child_v1_1,
        kwargs={"sentinel": True}, daemon=False,
    )
    assert result is not None
    assert context.target is adapter._run_linux_generation_child_v1_2
    assert context.kwargs == {"sentinel": True} and context.daemon is False


def test_identity_is_deterministic_and_import_is_inert():
    assert adapter.LINUX_CHILD_PROCESS_ADAPTER_IDENTITY == hashlib.sha256(
        "\n".join(adapter.LINUX_CHILD_PROCESS_ADAPTER_IDENTITY_FIELDS).encode()
    ).hexdigest()
