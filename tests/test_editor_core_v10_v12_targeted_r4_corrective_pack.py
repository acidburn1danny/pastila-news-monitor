import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts/audit_editor_core_v10_v12_targeted_r4_corrective_pack.py"
ART = ROOT / "docs/artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r4"


def module():
    spec = importlib.util.spec_from_file_location("r4_audit", AUDIT); value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None; spec.loader.exec_module(value); return value


def test_r4_pack_closes_without_training_or_contamination():
    result = module().audit()
    assert result["verdict"] == "PASS" and result["blockers"] == 0
    assert (result["new_rows"], result["replay_rows"], result["holdout_rows"]) == (12, 36, 12)
    assert result["exact_contamination_matches"] == 0
    assert result["replay_provenance"] == {"v10_v1_2": 12, "targeted_r1": 12, "targeted_r2": 12}
    assert result["frozen_holdout_training_use"] is result["frozen_holdout_targets_reused"] is False
    assert result["rejected_r3_adapter_training_use"] is False
    assert result["maximum_training_sequence_tokens"] <= 3072 and result["training_performed"] is False


def test_r4_scope_and_holdout_separation():
    manifest = json.loads((ART / f"{PREFIX}-manifest.json").read_bytes())
    assert manifest["failure_classes"] == ["EPISTEMIC_CALIBRATION"]
    assert len(manifest["source_diagnostic_case_ids"]) == 3
    rows = [json.loads(line) for line in (ART / f"{PREFIX}-holdout-requests.jsonl").read_bytes().splitlines()]
    assert len(rows) == 12 and all([m["role"] for m in row["messages"]] == ["system", "user"] for row in rows)


def test_r4_targets_preserve_three_epistemic_components():
    rows = [json.loads(line) for line in (ART / f"{PREFIX}-new-train.jsonl").read_bytes().splitlines()]
    for row in rows:
        target = json.loads(row["messages"][2]["content"])
        assert len(target["claim_bindings"]) == 3
        assert [item["claim_index"] for item in target["claim_bindings"]] == [1, 2, 3]


def test_r4_similarity_tokenization_is_unicode_aware():
    audit = module()
    assert audit.similarity("Păstrează suspiciunea explicită", "Păstrează suspiciunea explicită") == 1.0
    assert audit.shingles("Păstrează explicit incertitudinea, atribuirea și modalitatea")
