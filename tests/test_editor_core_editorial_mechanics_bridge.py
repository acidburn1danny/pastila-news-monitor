"""Meaningful closure and fail-closed tests for the data-only bridge."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_editor_core_editorial_mechanics_bridge as audit  # noqa: E402
import build_editor_core_editorial_mechanics_bridge as builder  # noqa: E402


def test_byte_exact_rebuild_and_closure(tmp_path):
    builder.build(tmp_path)
    result = audit.audit(tmp_path)
    assert result["verdict"] == "PASS" and result["blockers"] == 0
    assert (result["train"], result["development"], result["holdout"]) == (48, 24, 24)
    for path in tmp_path.iterdir():
        assert path.read_bytes() == (builder.ART / path.name).read_bytes()


def test_target_leakage_fails_closed(tmp_path):
    builder.build(tmp_path)
    name = f"{builder.PREFIX}-holdout-requests.jsonl"
    path = tmp_path / name
    rows = [json.loads(x) for x in path.read_bytes().splitlines()]
    rows[0]["messages"].append({"role": "assistant", "content": "leaked"})
    raw = builder.jsonl(rows)
    path.write_bytes(raw)
    manifest_path = tmp_path / f"{builder.PREFIX}-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"]["holdout-requests"].update(sha256=builder.sha(raw), bytes=len(raw))
    core = {k: v for k, v in manifest.items() if k != "manifest_identity"}
    manifest["manifest_identity"] = builder.sha(builder.canonical(core))
    manifest_path.write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b"\n")
    with pytest.raises(ValueError, match="answer leaked"):
        audit.audit(tmp_path)


def test_blob_tamper_fails_closed(tmp_path):
    builder.build(tmp_path)
    path = tmp_path / f"{builder.PREFIX}-train-mechanics.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="blob identity"):
        audit.audit(tmp_path)


def test_rehashed_ablation_drift_fails_closed(tmp_path):
    builder.build(tmp_path)
    plan_path = tmp_path / f"{builder.PREFIX}-plan.json"
    plan = json.loads(plan_path.read_bytes())
    plan["factorial"]["arms"][5]["replay"] = "FIXED_BASELINE"
    plan["plan_identity"] = builder.sha(builder.canonical({k: v for k, v in plan.items() if k != "plan_identity"}))
    raw = json.dumps(plan, ensure_ascii=False, indent=2).encode() + b"\n"
    plan_path.write_bytes(raw)
    manifest_path = tmp_path / f"{builder.PREFIX}-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"]["plan"].update(sha256=builder.sha(raw), bytes=len(raw))
    manifest["manifest_identity"] = builder.sha(builder.canonical({k: v for k, v in manifest.items() if k != "manifest_identity"}))
    manifest_path.write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b"\n")
    with pytest.raises(ValueError, match="controlled ablation arm projection"):
        audit.audit(tmp_path)
