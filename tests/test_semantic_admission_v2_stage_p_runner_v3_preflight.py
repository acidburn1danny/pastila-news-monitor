import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.gate_f_trie_projector_v1 import GateFTokenTrieProjectorOptimizedV1
from pastila_scout.semantic_admission_v2.stage_p_callback_controller_v1 import StagePCallbackControllerV1
from pastila_scout.semantic_admission_v2.stage_p_durable_executor_v3 import (
    DEPENDENCY_IDENTITIES,
    RUNNER_RELATIVE,
    RUNNER_SHA256,
    DurableConstrainedStagePCoreV12ExecutorV3,
)
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


ROOT=Path(__file__).resolve().parents[1]


def test_v3_executor_constructs_without_wsl_model_or_lifecycle_events(tmp_path) -> None:
    executor=DurableConstrainedStagePCoreV12ExecutorV3(project_root=ROOT,durable_lifecycle_root=tmp_path)
    assert executor is not None and list(tmp_path.iterdir())==[]


def test_v3_runner_and_dependency_identities_are_exact() -> None:
    assert hashlib.sha256((ROOT/RUNNER_RELATIVE).read_bytes()).hexdigest()==RUNNER_SHA256
    for relative,expected in DEPENDENCY_IDENTITIES.items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected


def test_v3_runner_connects_controller_and_preserves_durable_events() -> None:
    source=(ROOT/RUNNER_RELATIVE).read_text("utf-8")
    assert "StagePCallbackControllerV1" in source and "controller.allowed(" in source
    assert "State().feed(decoded)" not in source
    for event in ("RUNNER_STARTED","REQUEST_VALIDATED","TOKENIZER_LOAD_STARTED","TRIE_BUILD_COMPLETED",
                  "PREWARM_COMPLETED","MODEL_LOAD_STARTED","GENERATION_STARTED","GENERATION_HEARTBEAT",
                  "TERMINAL_EOS","RESPONSE_PERSISTED","RUNNER_EXCEPTION"):
        assert f'events.emit("{event}"' in source
    assert "tracking_path=receipt.tracking_path" in source
    assert "tracker_rebuilds=receipt.tracker_rebuilds" in source


def test_controller_allowed_sets_equal_baseline_through_incremental_prefixes() -> None:
    record={"entry_id":"P1","entry_type":"REAL_WORLD_COMMITMENT","candidate_span":"ab",
        "authority_support":None,"commitment":"ab","scope_basis":"ASSERTED","event_alignment":"GOVERNED_EVENT",
        "authority_modality":"POSSIBLE","candidate_modality":"CERTAIN_OR_ACTUAL","authority_timing":"FUTURE",
        "candidate_timing":"PRESENT","independence_group":"G1"}
    text=json.dumps({"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":[record],
        "coverage_receipt":{"candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
        "creative_scope_checked":True,"unresolved_scope_present":False}},separators=(",",":"))
    pieces={0:"<eos>",**{index:character for index,character in enumerate(sorted(set(text)),1)}}
    baseline=GateFTokenTrieProjectorOptimizedV1(token_pieces=pieces,eos_token_id=0)
    candidate=StagePTokenTrieProjectorV1(token_pieces=pieces,eos_token_id=0)
    controller=StagePCallbackControllerV1(projector=candidate)
    ids=[]
    for character in text:
        token_id=next(item for item,piece in pieces.items() if piece==character)
        ids.append(token_id)
        receipt=controller.allowed(ids,lambda values:"".join(pieces[item] for item in values))
        from pastila_scout.semantic_admission_v2.stage_p_constraint_v1 import StagePConstraintStateV1
        assert receipt.allowed_token_ids==baseline.allowed_token_ids(StagePConstraintStateV1().feed("".join(pieces[item] for item in ids)))
    assert controller.tracker.incremental_steps==len(ids)


def test_v3_executor_retains_timeout_surviving_host_lifecycle() -> None:
    source=(ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_durable_executor_v3.py").read_text("utf-8")
    assert "subprocess.Popen" in source and "HOST_TIMEOUT" in source and "HOST_TERMINATION_OBSERVED" in source
    assert "dependency_identities=" in source and "CREATE_NO_WINDOW" in source
