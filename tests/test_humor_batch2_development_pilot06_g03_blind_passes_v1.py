import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_blind_passes_are_frozen_before_reconciliation():
    base = ROOT / "docs/artifacts"
    for name, namespace in (("humor-mechanics-batch2-development-pilot06-g03-open-blind-pass-v1.json", "B2_PILOT06_G03_OPEN_BLIND_PASS_V1"),
                            ("humor-mechanics-batch2-development-pilot06-g03-contrast-blind-pass-v1.json", "B2_PILOT06_G03_CONTRAST_BLIND_PASS_V1")):
        value = json.loads((base / name).read_text(encoding="utf-8"))
        core = dict(value); identity = core.pop("blind_pass_identity")
        assert identity == seal(namespace, core)
        assert value["sealed_mapping_accessed"] is False
        assert value["reconciliation_performed"] is False
        assert value["candidate_modified"] is False
