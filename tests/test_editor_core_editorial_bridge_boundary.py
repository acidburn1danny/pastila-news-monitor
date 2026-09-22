"""Fixture-only negative tests for the non-consuming Bridge execution gate."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_editor_core_editorial_bridge_boundary as boundary_audit  # noqa: E402
import build_editor_core_editorial_bridge_boundary as builder  # noqa: E402
import preflight_editor_core_editorial_bridge as preflight  # noqa: E402
import validate_editor_core_editorial_bridge_naturalistic as naturalistic  # noqa: E402
from project_editor_core_editorial_bridge_arms import projection  # noqa: E402


def test_boundary_and_arm_projection():
    result = boundary_audit.audit(check_publication=False)
    assert result["verdict"] == "PASS_LOCAL_BOUNDARY_ABLATIONS_BLOCKED"
    assert result["arm_count"] == 7 and result["ablation_training_authorized"] is False
    arms = projection()["arms"]
    assert arms["A1"]["sha256"] == arms["A3"]["sha256"]
    assert arms["A2"]["sha256"] == arms["A4"]["sha256"]
    assert arms["A2"]["sha256"] != arms["A5"]["sha256"]
    assert arms["A2"]["sha256"] != arms["A7"]["sha256"]


def test_rehashed_stop_rule_weakening_rejected(tmp_path):
    value = json.loads(preflight.BOUNDARY_PATH.read_bytes())
    value["stop_rules"]["immediate_program_stop"].remove("ANY_TRAIN_EVAL_OR_NATURALISTIC_TARGET_LEAKAGE")
    value["boundary_identity"] = builder.sha(builder.canonical({k: v for k, v in value.items() if k != "boundary_identity"}))
    path = tmp_path / "boundary.json"
    path.write_bytes(json.dumps(value).encode())
    with pytest.raises(ValueError, match="naturalistic/stop-rule contract"):
        boundary_audit.audit(path, check_publication=False)


def test_no_preflight_bypass_switches():
    with pytest.raises(TypeError):
        preflight.preflight(None, None, None, None, None, fresh_tokenizer=False)


def make_naturalistic_fixture(root: Path) -> Path:
    sources = root / "sources"
    sources.mkdir()
    requests, keys, source_hashes = [], [], []
    for op in builder.protocol()["operator_quota"]:
        for index in range(12):
            case_id = f"naturalistic-fixture-{op.lower()}-{index:02d}"
            span = f"Documentul {case_id} consemnează cererea independentă {index} pentru biroul {op}."
            source = (span + "\nAltă informație contextuală, fără relație cauzală.\n").encode()
            source_hash = builder.sha(source)
            (sources / f"{source_hash}.txt").write_bytes(source)
            source_hashes.append(source_hash)
            core = {"case_id": case_id, "operator": op, "source_family": f"source-{case_id}",
                    "source_document_sha256": source_hash, "source_provenance": f"fixture://{case_id}",
                    "request": "Relatează fidel faptul relevant.",
                    "authority_spans": [{"span_id": f"span-{case_id}", "text": span}]}
            request = {**core, "request_identity": "sha256:" + builder.sha(builder.canonical(core))}
            requests.append(request)
            keys.append({"case_id": case_id, "request_identity": request["request_identity"],
                         "supported_claims": ["cererea independentă"], "required_qualifications": [],
                         "disallowed_inferences": ["cauzalitate"], "editorial_operation": op,
                         "source_span_bindings": [f"span-{case_id}"]})
    requests_raw = b"".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode() + b"\n" for row in requests)
    keys_raw = b"".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode() + b"\n" for row in keys)
    (root / "requests.jsonl").write_bytes(requests_raw)
    (root / "answer-key.jsonl").write_bytes(keys_raw)
    core = {"schema": "editor-core-editorial-bridge-naturalistic-bundle", "schema_version": 1,
            "case_count": 96, "training_use": False, "collected_before_ablation": True,
            "requests_sha256": builder.sha(requests_raw), "answer_key_sha256": builder.sha(keys_raw),
            "source_document_sha256": source_hashes}
    manifest = {**core, "manifest_identity": builder.sha(builder.canonical(core))}
    (root / "manifest.json").write_bytes(json.dumps(manifest).encode())
    return root


def test_naturalistic_fixture_and_duplicate_rejection(tmp_path):
    bundle = make_naturalistic_fixture(tmp_path)
    result = naturalistic.validate(bundle)
    assert result["cases"] == 96
    assert result["verdict"] == "PASS_STRUCTURAL_ONLY_PROVENANCE_UNVERIFIED"
    assert result["eligible_for_ablation_gate"] is False
    requests_path = bundle / "requests.jsonl"
    rows = [json.loads(line) for line in requests_path.read_bytes().splitlines()]
    rows[1]["source_family"] = rows[0]["source_family"]
    raw = b"".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode() + b"\n" for row in rows)
    requests_path.write_bytes(raw)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["requests_sha256"] = builder.sha(raw)
    manifest["manifest_identity"] = builder.sha(builder.canonical({k: v for k, v in manifest.items() if k != "manifest_identity"}))
    manifest_path.write_bytes(json.dumps(manifest).encode())
    with pytest.raises(ValueError, match="naturalistic case/source overlap"):
        naturalistic.validate(bundle)
