import importlib.util
import json
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("v0", "scripts/run_editor_vnext_minimal_v0_runtime_v1.py")
V = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(V)


def load():
    contract = json.loads(Path("docs/artifacts/editor-vnext-minimal-v0-editor-runtime-contract-v1.json").read_text(encoding="utf-8"))
    packet = json.loads(Path("docs/artifacts/editor-vnext-minimal-v0-editor-runtime-fixture-v1.json").read_text(encoding="utf-8"))
    return contract, packet


def test_source_packet_identity_and_bytes():
    contract, packet = load(); V.verify_source_packet(packet, contract)


def test_structural_boundary_rejects_duplicate_keys_and_wrong_event():
    assert V.structural_output('{"case_id":"x","case_id":"x","text":"ok"}', "x")[0] is False
    assert V.structural_output('{"case_id":"y","text":"ok"}', "x")[0] is False
    assert V.structural_output('{"case_id":"x","text":"ok"}', "x")[0] is True


def test_shadow_absence_and_failure_are_non_blocking():
    assert V.optional_shadow(None, "source", "{}", "x")["status"] == "NOT_CONFIGURED_NON_BLOCKING"
    result = V.optional_shadow(Path("missing-shadow-plugin.py"), "source", "{}", "x")
    assert result["status"] == "ERROR_NON_BLOCKING" and result["authoritative"] is False


def test_source_preserving_fallback_or_abstention():
    contract, packet = load(); assert V.safety_boundary(packet, contract)["route"] == "SOURCE_PRESERVING_FALLBACK"
    packet = json.loads(json.dumps(packet)); packet["spans"].append({**packet["spans"][0], "span_id": "fourth"})
    assert V.safety_boundary(packet, contract)["route"] == "ABSTAIN"
