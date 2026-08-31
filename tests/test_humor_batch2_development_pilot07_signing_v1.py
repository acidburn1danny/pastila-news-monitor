import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/owner_humor_batch2_development_pilot07_signing_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pilot07_signing", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frozen_packet_is_exactly_unsigned_eight_request_packet():
    module = load_module()
    packet = module.json.loads(module.PACKET.read_text(encoding="utf-8"))
    module.verify_packet(packet)
    assert packet["packet_identity"] == module.PACKET_ID
    assert packet["status"] == "UNSIGNED"
    assert packet["signatures_present"] == 0
    assert len(packet["signature_requests"]) == 8
    assert packet["proposition_sufficiency_evaluated"] is False


def test_secret_and_response_paths_must_be_outside_repository(tmp_path):
    module = load_module()
    external = tmp_path.resolve()
    assert module.outside_repo(external) == external
    try:
        module.outside_repo(ROOT / "forbidden")
    except SystemExit as exc:
        assert "repository-local" in str(exc)
    else:
        raise AssertionError("repository-local path was accepted")
