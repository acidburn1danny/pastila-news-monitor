from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/owner_humor_batch2_development_pilot11_signing_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pilot11_signing", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frozen_packet_is_exactly_unsigned_eight_request_packet() -> None:
    module = load_module()
    packet = module.json.loads(module.PACKET.read_text(encoding="utf-8"))
    module.verify_packet(packet)
    assert packet["packet_identity"] == module.PACKET_IDENTITY
    assert packet["status"] == "UNSIGNED" and packet["signatures_present"] == 0
    assert len(packet["signature_requests"]) == 8
    assert packet["proposition_sufficiency_evaluated"] is False
    assert packet["constructor_semantic_plan_release_or_invocation_performed"] is False
    assert packet["realization_candidate_emission_or_semantic_edge_validation_performed"] is False
    assert packet["fragment_collision_evaluation_performed"] is False


def test_frozen_packet_inputs_are_byte_exact_at_preparation_commit() -> None:
    module = load_module()
    for path in [module.PACKET, module.PROSPECTIVE, module.INDEPENDENCE, module.REGISTRATION]:
        frozen = module.subprocess.check_output(
            ["git", "show", f"{module.FREEZE_COMMIT}:{path.relative_to(module.ROOT).as_posix()}"], cwd=module.ROOT)
        assert path.read_bytes() == frozen


def test_secret_and_response_paths_must_be_outside_repository() -> None:
    module = load_module()
    external = Path(f"{ROOT.drive}\\Pilot11-owner-controlled-external-test").resolve()
    assert module.outside_repository(external) == external
    try:
        module.outside_repository(ROOT / "forbidden")
    except SystemExit as exc:
        assert "repository-local" in str(exc)
    else:
        raise AssertionError("repository-local path accepted")
