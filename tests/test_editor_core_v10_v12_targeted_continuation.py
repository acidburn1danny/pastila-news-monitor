import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts/audit_editor_core_v10_v12_targeted_continuation.py"
ART = ROOT / "docs/artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-v1"


def module():
    spec = importlib.util.spec_from_file_location("targeted_audit", AUDIT)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_published_round_closes_without_training():
    result = module().audit()
    assert result["verdict"] == "PASS" and result["blockers"] == 0
    assert (result["new_rows"], result["replay_rows"], result["holdout_rows"]) == (64, 64, 32)
    assert result["exact_contamination_matches"] == 0
    assert result["replay_exact_source_matches"] == 64
    assert result["training_performed"] is False


def test_holdout_contains_no_assistant_target():
    rows = module().rows("holdout-requests")
    assert len(rows) == 32
    assert all([m["role"] for m in row["messages"]] == ["system", "user"] for row in rows)


def test_audit_rejects_parent_or_manifest_drift(tmp_path, monkeypatch):
    m = module()
    manifest = json.loads((ART / f"{PREFIX}-manifest.json").read_bytes())
    manifest["parent_adapter_content_identity"] = "0" * 64
    fake_art = tmp_path / "artifacts"
    fake_art.mkdir()
    for path in ART.glob(f"{PREFIX}-*"):
        (fake_art / path.name).write_bytes(path.read_bytes())
    (fake_art / f"{PREFIX}-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(m, "ART", fake_art)
    with pytest.raises(ValueError, match="manifest identity"):
        m.audit()


def test_replay_is_exactly_sourced_from_v10_v12():
    m = module()
    replay = m.rows("replay-anchors")
    source = m.rows_from_path(ART / "pastila-editor-core-v1.2-json-successor-v10-train.jsonl")
    source_hashes = {m.sha(m.canonical(x)) for x in source}
    assert len(replay) == 64
    assert all(m.sha(m.canonical(x)) in source_hashes for x in replay)
