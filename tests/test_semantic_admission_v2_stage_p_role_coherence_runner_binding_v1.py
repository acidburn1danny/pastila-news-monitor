import hashlib
import inspect
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_role_coherence_callback_controller_v1 import StagePRoleCoherenceCallbackControllerV1
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintStateV1
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_role_coherence_runner_v1.py"


def _raw() -> str:
    entry = {"entry_id":"P1","entry_type":"CONTAINED_CREATIVE","candidate_span":"hotelul","authority_support":None,
             "commitment":"Camera extinde editorial transparența.","scope_basis":"CREATIVE_CONTAINED",
             "event_alignment":"CREATIVE_VEHICLE_ONLY","authority_modality":"NOT_APPLICABLE",
             "candidate_modality":"NOT_APPLICABLE","authority_timing":"NOT_APPLICABLE",
             "candidate_timing":"NOT_APPLICABLE","independence_group":"G1"}
    value = {"stage_id":"PROPOSITION_LEDGER","entries":[entry],"coverage_receipt":{
             "candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
             "creative_scope_checked":True,"unresolved_scope_present":False},"coverage_decision":"COMPLETE"}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def test_runner_binds_only_role_coherence_types_and_durable_base() -> None:
    source = RUNNER.read_text("utf-8")
    for name in ("StagePRoleCoherenceConstraintStateV1", "StagePRoleCoherenceCallbackControllerV1", "StagePTokenTrieProjectorV1"):
        assert name in source
    assert "experimental_core_v1_2_stage_p_constrained_runner_v3.py" in source
    assert "base._types = _role_coherence_types" in source
    assert "base.run(" in source


def test_role_coherence_controller_tracks_fixture_to_terminal() -> None:
    raw = _raw()
    pieces = {0:"<eos>", **{index:char for index,char in enumerate(sorted(set(raw)),1)}}
    inverse = {char:index for index,char in pieces.items() if index}
    projector = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=0)
    controller = StagePRoleCoherenceCallbackControllerV1(projector=projector)
    ids = []
    for char in raw:
        ids.append(inverse[char])
        receipt = controller.allowed(ids, lambda values: "".join(pieces[item] for item in values))
    assert StagePRoleCoherenceConstraintStateV1().feed(raw).can_eos
    assert receipt.allowed_token_ids == (0,)
    assert receipt.tracker_rebuilds == 0


def test_bound_sources_have_no_import_time_model_or_execution() -> None:
    import pastila_scout.semantic_admission_v2.stage_p_role_coherence_callback_controller_v1 as controller
    import pastila_scout.semantic_admission_v2.stage_p_role_coherence_incremental_tracker_v1 as tracker
    combined = inspect.getsource(controller) + inspect.getsource(tracker)
    assert "transformers" not in combined and "torch" not in combined and "subprocess" not in combined
    assert hashlib.sha256(RUNNER.read_bytes()).hexdigest()
