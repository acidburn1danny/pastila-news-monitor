import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_successor_candidate_manifest_v9.py"


def module():
    spec = importlib.util.spec_from_file_location("manifest_v9", SCRIPT)
    value = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(value)
    return value


def test_v9_receipt_and_manifest_are_sealed_and_zero_execution():
    value = module(); receipt = value.audit_receipt(); core = dict(receipt)
    assert core.pop("adapter_audit_identity") == value.sealed(core, "adapter_audit_identity")["adapter_audit_identity"]
    manifest = value.candidate_manifest(receipt); core = dict(manifest)
    assert core.pop("manifest_identity") == value.sealed(core, "manifest_identity")["manifest_identity"]
    assert manifest["qualification_attempt_consumed"] is False
    assert manifest["candidate_execution_performed"] is False
    assert manifest["promotion_effect"] is False


def test_v9_materialization_is_reproducible(tmp_path, monkeypatch):
    value = module(); monkeypatch.setattr(value, "ART", tmp_path); assert value.main() == 0
    for name in ("production-core-dual-successor-adapter-audit-receipt-v9.json", "production-core-successor-candidate-object-manifest-v9.json"):
        assert (tmp_path / name).read_bytes() == (ROOT / "docs/artifacts" / name).read_bytes()
