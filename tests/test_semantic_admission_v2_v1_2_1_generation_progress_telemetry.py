from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pastila_scout.semantic_admission_v2 import (
    stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 as worker,
)
from pastila_scout.semantic_admission_v2 import (
    stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1
    as supervisor,
)
from pastila_scout.semantic_admission_v2 import (
    stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1
    as authority,
)
from test_semantic_admission_v2_v1_2_1_timeout_progress_remediation import _progress


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def _receipt(index: int):
    return SimpleNamespace(
        decoded_sha256=hashlib.sha256(str(index).encode()).hexdigest(),
        dfa_mode="BODY_TEXT",
        terminal=False,
        legal_token_count=17,
        eos_allowed=False,
    )


def _records(request, counts=(1, 2, 4)):
    previous = None
    records = []
    for sequence, count in enumerate(counts):
        raw = worker._generation_progress(
            provider_request_id=request.provider_request_id,
            source_context_identity=request.source_context_identity,
            sequence=sequence,
            previous_identity=previous,
            callback_count=count,
            generated_token_count=count - 1,
            callback_duration_ns=100 + count,
            elapsed_since_generation_start_ns=1000 * count,
            receipt=_receipt(count),
        )
        previous = json.loads(raw)["progress_identity"]
        records.append(("generation_progress", raw))
    return tuple(records)


def test_milestones_are_bounded_below_queue_capacity():
    observed = [value for value in range(1, 3201)
                if worker._telemetry_milestone(value)]
    assert observed == [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048]
    # lifecycle + compatibility + telemetry stays below the fixed queue size 32.
    assert len(observed) + 9 < 32


def test_timeout_reconciliation_persists_progress_and_cleanup_observation():
    request, base = _progress()
    progress = (*base, *_records(request))
    artifacts = dict(supervisor._reconcile_artifacts(
        request=request,
        child_result=None,
        failure_code="CHILD_TIMEOUT_TERMINATED",
        child_progress=progress,
    ))
    assert [json.loads(artifacts[f"generation-progress-{index:05d}.json"])
            ["callback_count"] for index in range(1, 4)] == [1, 2, 4]
    cleanup = json.loads(artifacts["termination-cleanup-observation.json"])
    assert cleanup["child_process_terminal"] is True
    assert cleanup["child_cleanup_event_observed"] is False
    assert cleanup["gpu_cleanup_observed"] is False
    assert cleanup["failure_code"] == "CHILD_TIMEOUT_TERMINATED"


def test_stall_before_first_completed_callback_is_explicitly_no_progress():
    request, base = _progress()
    artifacts = dict(supervisor._reconcile_artifacts(
        request=request,
        child_result=None,
        failure_code="CHILD_TIMEOUT_TERMINATED",
        child_progress=base,
    ))
    assert not any(label.startswith("generation-progress-") for label in artifacts)
    assert json.loads(artifacts["runner-result.json"])["execution_failure_code"] == (
        "CHILD_TIMEOUT_TERMINATED")


@pytest.mark.parametrize("counts", ((2,), (1, 4), (1, 2, 8)))
def test_recomputed_omitted_or_skipped_milestone_prefix_fails_closed(counts):
    request, base = _progress()
    with pytest.raises(ValueError, match="GENERATION_PROGRESS_BINDING_INVALID"):
        supervisor._reconcile_artifacts(
            request=request,
            child_result=None,
            failure_code="CHILD_TIMEOUT_TERMINATED",
            child_progress=(*base, *_records(request, counts)),
        )


@pytest.mark.parametrize("terminal_event,detail", (
    ("TERMINAL_EOS", {"generated_token_count": 1, "output_sha256": "2" * 64}),
    ("NO_LEGAL_TOKEN", {"receipt_identity": "3" * 64}),
    ("EXECUTION_FAILED", {"failure_code": "synthetic"}),
))
def test_recomputed_post_terminal_telemetry_fails_closed(terminal_event, detail):
    request, base = _progress()
    previous = json.loads(base[-1][1])["event_identity"]
    terminal = worker._event(
        request.provider_request_id, 3, terminal_event, detail, previous)
    with pytest.raises(ValueError, match="PROGRESS_ORDER_INVALID"):
        supervisor._validated_timeout_progress(
            (*base, ("lifecycle", terminal), *_records(request, (1,))),
            request.provider_request_id,
            request.source_context_identity,
        )


def test_recomputed_post_cleanup_telemetry_fails_closed():
    request, base = _progress()
    previous = json.loads(base[-1][1])["event_identity"]
    terminal = worker._event(
        request.provider_request_id, 3, "EXECUTION_FAILED",
        {"failure_code": "synthetic"}, previous)
    cleanup = worker._event(
        request.provider_request_id, 4, "CLEANUP_COMPLETED",
        {"failure_type": None}, json.loads(terminal)["event_identity"])
    with pytest.raises(ValueError, match="PROGRESS_ORDER_INVALID"):
        supervisor._validated_timeout_progress(
            (*base, ("lifecycle", terminal), ("lifecycle", cleanup),
             *_records(request, (1,))),
            request.provider_request_id,
            request.source_context_identity,
        )


@pytest.mark.parametrize("mutation", (
    "cross_request", "cross_source", "worker", "replayed", "reordered",
    "callback", "generated", "elapsed", "projector",
))
def test_mutated_replayed_or_reordered_progress_fails_closed(mutation):
    request, base = _progress()
    records = list(_records(request))
    if mutation == "replayed":
        records.insert(1, records[0])
    elif mutation == "reordered":
        records[0], records[1] = records[1], records[0]
    else:
        value = json.loads(records[1][1])
        if mutation == "cross_request":
            value["provider_request_id"] = "cross-request"
        elif mutation == "cross_source":
            value["source_context_identity"] = "0" * 64
        elif mutation == "worker":
            value["worker_identity"] = "0" * 64
        elif mutation == "callback":
            value["callback_count"] = 3
        elif mutation == "generated":
            value["generated_token_count"] = -1
        elif mutation == "elapsed":
            value["elapsed_since_generation_start_ns"] = 0
        else:
            value["projector_state"]["dfa_mode"] = ""
        value["progress_identity"] = hashlib.sha256(_canonical({
            key: item for key, item in value.items()
            if key != "progress_identity"
        })).hexdigest()
        records[1] = ("generation_progress", _canonical(value))
    with pytest.raises(ValueError, match="GENERATION_PROGRESS|PROGRESS_ORDER"):
        supervisor._reconcile_artifacts(
            request=request,
            child_result=None,
            failure_code="CHILD_TIMEOUT_TERMINATED",
            child_progress=(*base, *records),
        )


def test_telemetry_modules_have_no_execution_or_runtime_loading_surface():
    source = "\n".join((
        open(worker.__file__, encoding="utf-8").read(),
        open(supervisor.__file__, encoding="utf-8").read(),
    ))
    forbidden = ("wsl" + ".exe", "from_" + "pretrained",
                 ".gene" + "rate(", "nvidia" + "-smi")
    assert all(term not in source for term in forbidden)


def test_consumed_pre_telemetry_receipt_is_rejected_by_new_lineage():
    root = Path(__file__).resolve().parents[1]
    raw = (root / (
        "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-"
        "case01-successor-issuance-packet-v1-2-1-durable-label-bound/"
        "authority-receipt-issued.json")).read_bytes()
    value = json.loads(raw)
    with pytest.raises(ValueError):
        authority.parse_generation_authority_v1_2_1(
            raw_receipt=raw,
            expected_host_payload_sha256=value["host_payload_sha256"],
            expected_runner_request_sha256=value["runner_request_sha256"],
            expected_provider_request_id=value["provider_request_id"],
            expected_source_context_identity=value["source_context_identity"],
            expected_packet_plan_identity=value["packet_plan_identity"],
            expected_command_plan_identity=value["command_plan_identity"],
        )
