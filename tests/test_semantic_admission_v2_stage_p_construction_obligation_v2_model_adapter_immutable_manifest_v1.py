from __future__ import annotations

import hashlib
import json
from pathlib import Path


ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-model-adapter-immutable-manifest-v1.json")


def _tree_identity(tree: dict[str, object]) -> str:
    rows = tree["files"]
    material = "".join(
        f'{row["path"]}\0{row["size"]}\0{row["sha256"]}\n'
        for row in rows
    )
    return hashlib.sha256(material.encode()).hexdigest()


def test_tree_manifests_rederive_from_ordered_rows():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    for name in ("base_snapshot", "adapter"):
        tree = artifact[name]
        assert [row["path"] for row in tree["files"]] == sorted(
            row["path"] for row in tree["files"])
        assert len(tree["files"]) == tree["file_count"]
        assert sum(row["size"] for row in tree["files"]) == tree["total_file_bytes"]
        assert _tree_identity(tree) == tree["manifest_sha256"]


def test_receipt_identity_and_load_authority_are_fail_closed():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == artifact["canonical_identity"]
    unresolved = artifact["unresolved_load_policy"]
    assert unresolved["model_load_compatibility_demonstrated"] is False
    assert unresolved["model_load_started_authorized"] is False
    assert artifact["authority"]["immutable_manifest_normalization"] is True
    assert all(
        value is False for key, value in artifact["authority"].items()
        if key != "immutable_manifest_normalization"
    )


def test_audit_activity_is_zero_execution():
    activity = json.loads(ARTIFACT.read_text(encoding="utf-8"))["activity"]
    assert activity["filesystem_hash_passes"] == 2
    assert all(value == 0 for key, value in activity.items() if key != "filesystem_hash_passes")
