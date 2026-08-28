from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_child_process_adapter_v1 as adapter
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_child_process_adapter_v1 import (
    LINUX_CHILD_PROCESS_ADAPTER_IDENTITY,
    build_linux_child_process_operations_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1 import (
    LinuxGenerationChildInvocationV1,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_child_process_adapter_v1.py"
)
ARTIFACT = (
    ROOT
    / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-linux-child-process-adapter-v1.json"
)
sys.path.insert(0, str(ROOT / "tests"))
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (
    _policy,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1 import (
    SYSTEM_PROMPT,
    _authority,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    _fixture,
)


class FakeQueue:
    def __init__(self, *, maxsize):
        self.maxsize = maxsize
        self.values = []
        self.closed = False

    def put(self, value, *, block, timeout):
        assert block is True and timeout == 10.0
        self.values.append(value)

    def get(self, *, block, timeout):
        assert block is True and timeout == 1.0
        if not self.values:
            raise type("Empty", (Exception,), {})()
        return self.values.pop(0)

    def close(self):
        self.closed = True

    def join_thread(self):
        assert self.closed


class FakeProcess:
    def __init__(self, *, target, kwargs, daemon):
        self.target = target
        self.kwargs = kwargs
        self.daemon = daemon
        self.started = False
        self.alive = False
        self.exitcode = 0
        self.calls = []

    def start(self):
        self.started = True

    def join(self, timeout):
        self.calls.append(("join", timeout))

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.calls.append(("terminate",))

    def kill(self):
        self.calls.append(("kill",))


class FakeContext:
    def __init__(self):
        self.processes = []
        self.queues = []

    def Queue(self, *, maxsize):
        value = FakeQueue(maxsize=maxsize)
        self.queues.append(value)
        return value

    def Process(self, **kwargs):
        value = FakeProcess(**kwargs)
        self.processes.append(value)
        return value


def _inputs():
    raw_request, request = _fixture()
    raw_authority = _authority(request)
    authority_identity = json.loads(raw_authority)["authority_receipt_identity"]
    invocation = LinuxGenerationChildInvocationV1(
        raw_request, SYSTEM_PROMPT, authority_identity
    )
    return raw_request, raw_authority, invocation


def test_constructs_one_deferred_spawn_child_without_executing_target():
    _, raw_authority, invocation = _inputs()
    context = FakeContext()
    observed_methods = []
    operations = build_linux_child_process_operations_v1(
        raw_policy_receipt=_policy(),
        raw_authority_receipt=raw_authority,
        context_factory=lambda method: observed_methods.append(method) or context,
    )
    assert context.processes == []
    handle = operations.start(invocation)
    assert observed_methods == ["spawn"]
    assert len(context.processes) == len(context.queues) == 1
    process = context.processes[0]
    assert process.started is True and process.daemon is False
    assert process.target is adapter._run_linux_generation_child_v1
    assert process.kwargs["invocation"] == invocation
    assert context.queues[0].maxsize == 1
    operations.join(handle, 7.0)
    operations.terminate(handle)
    operations.kill(handle)
    assert operations.is_alive(handle) is False
    assert operations.exit_code(handle) == 0
    assert process.calls == [("join", 7.0), ("terminate",), ("kill",)]
    with pytest.raises(RuntimeError, match="START_CEILING"):
        operations.start(invocation)


def test_start_revalidates_authority_and_collect_is_single_use():
    _, raw_authority, invocation = _inputs()
    context = FakeContext()
    operations = build_linux_child_process_operations_v1(
        raw_policy_receipt=_policy(),
        raw_authority_receipt=raw_authority,
        context_factory=lambda _: context,
    )
    with pytest.raises(ValueError):
        operations.start(
            LinuxGenerationChildInvocationV1(
                invocation.raw_runner_request, invocation.system_prompt, "0" * 64
            )
        )
    assert context.processes == []
    handle = operations.start(invocation)
    assert operations.collect_result(handle) is None
    with pytest.raises(RuntimeError):
        operations.collect_result(handle)


def test_child_target_maps_committed_layers_with_injected_fakes(monkeypatch):
    raw_request, raw_authority, invocation = _inputs()
    request = SimpleNamespace(host_payload=b"host")
    host = SimpleNamespace(rendered_prompt="rendered")
    prepared = SimpleNamespace(token_piece_bundle="pieces", operations="explicit")
    result = adapter.InjectedGenerationSupervisorResultV1(
        "EXECUTION_FAILURE", (), b"result", None, None, None, b"cleanup"
    )
    trace = []
    monkeypatch.setattr(
        adapter,
        "parse_runner_request_v1",
        lambda **kwargs: trace.append(("request", kwargs)) or request,
    )
    monkeypatch.setattr(
        adapter,
        "parse_construction_obligation_v2_host_wsl_payload_v1",
        lambda **kwargs: trace.append(("host", kwargs)) or host,
    )
    monkeypatch.setattr(
        adapter,
        "prepare_linux_runtime_operations_v1",
        lambda **kwargs: trace.append(("prepare", kwargs)) or prepared,
    )
    monkeypatch.setattr(
        adapter,
        "bind_static_projector_preflight_v1_2",
        lambda **kwargs: trace.append(("projector", kwargs)) or "projector",
    )
    monkeypatch.setattr(
        adapter,
        "bind_static_callback_preflight_v1_3",
        lambda **kwargs: trace.append(("callback", kwargs)) or "callback",
    )
    monkeypatch.setattr(
        adapter,
        "adapt_runtime_operations_v1_1",
        lambda **kwargs: trace.append(("adapt", kwargs)) or "operations",
    )
    monkeypatch.setattr(
        adapter,
        "supervise_injected_generation_v1",
        lambda **kwargs: trace.append(("supervise", kwargs)) or result,
    )
    queue = FakeQueue(maxsize=1)
    adapter._run_linux_generation_child_v1(
        invocation=invocation,
        raw_policy_receipt=_policy(),
        raw_authority_receipt=raw_authority,
        result_queue=queue,
    )
    assert [name for name, _ in trace] == [
        "request",
        "host",
        "prepare",
        "projector",
        "callback",
        "adapt",
        "supervise",
    ]
    assert trace[0][1] == {"raw_request": raw_request}
    assert queue.values == [result]


def test_policy_fails_before_context_construction():
    called = []
    with pytest.raises(ValueError):
        build_linux_child_process_operations_v1(
            raw_policy_receipt=b"{}\n",
            raw_authority_receipt=b"{}\n",
            context_factory=lambda method: called.append(method),
        )
    assert called == []


def test_artifact_identity_and_source_only_authority():
    artifact = json.loads(ARTIFACT.read_bytes())
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == LINUX_CHILD_PROCESS_ADAPTER_IDENTITY
    )
    assert artifact["canonical_identity"] == LINUX_CHILD_PROCESS_ADAPTER_IDENTITY
    assert artifact["authority"] == {
        "source_normalization": True,
        "process_or_wsl_launch_executed": False,
        "tokenizer_or_model_loading_executed": False,
        "generation_or_inference_executed": False,
        "provider_execution": False,
        "stage_c": False,
        "runtime_or_production": False,
    }
    source = SOURCE.read_text("utf-8")
    assert "if __name__" not in source
    assert "wsl.exe" not in source
    assert "subprocess" not in source
